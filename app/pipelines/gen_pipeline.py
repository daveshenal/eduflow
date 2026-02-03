from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict
import json
import shutil
import httpx

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.core.content_upload import upload_huddle_artifacts, upload_huddle_logs
from app.core.curriculem_plan_service import get_word_targets, fetch_plan_prompts, format_plan_prompt, generate_plan
from app.core.content_service import fetch_huddle_prompts, process_single_huddle
from app.core.pdf_generator import create_huddle_pdf


class HuddleJob:
    def __init__(self, job_id: str, sequence_id: int, provider_id: str, ccn: str,
                 branch_id: int, user_id: int, callback_url: str):
        self.job_id = job_id
        self.sequence_id = sequence_id
        self.provider_id = provider_id
        self.ccn = ccn
        self.branch_id = branch_id
        self.user_id = user_id
        self.callback_url = callback_url
        self.status = "queued"
        self.message = "Job queued for processing"
        self.result = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def update(self, status: str, message: str, result: Dict = None, error: str = None):
        self.status = status
        self.message = message
        self.result = result
        self.error = error
        self.updated_at = datetime.now(timezone.utc).isoformat()


def validate_payload(payload: dict) -> dict:
    """Validate and extract required fields from payload."""
    
    # Required fields
    required_fields = [
        "indexId", "jobId", "callbackUrl", "learningFocus", "topic", 
        "targetAudiance", "duration", "numHuddles", "voice"
    ]
    
    # List to store missing fields
    missing_fields = []

    # Check for missing required fields
    for field in required_fields:
        if field not in payload:
            missing_fields.append(field)
    
    # If any fields are missing, raise an error with a list of missing fields
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Extract and return fields from payload
    return {
        "job_id": payload.get("jobId"),
        "callback_url": payload.get("callbackUrl"),
        "provider_id": payload.get("providerId"),
        "learning_focus": payload.get("learningFocus"),
        "topic": payload.get("topic"),
        "target_audiance": payload.get("targetAudiance"),
        "duration": int(payload.get("duration")),
        "num_huddles": int(payload.get("numHuddles")),
        "voice": payload.get("voice"),
    }


def setup_output_directories(job_id: str) -> dict:
    """Create and return output directory paths for a specific job."""
    base_dir = Path("temp/huddles") / job_id
    base_dir.mkdir(parents=True, exist_ok=True)
    
    dirs = {
        'pdfs': base_dir / "pdfs",
        'voiceovers': base_dir / "voicescripts",
        'audio': base_dir / "audio_mp3s"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


def clean_local_directories(job_id: str):
    """Delete the entire job directory."""
    job_dir = Path("temp/huddles") / job_id
    try:
        if job_dir.exists() and job_dir.is_dir():
            shutil.rmtree(job_dir, ignore_errors=True)
    except Exception as cleanup_error:
        logging.warning(f"Failed to clean up job directory {job_id}: {cleanup_error}")


async def generate_huddles_background_task(params: dict, claude_client):
    """Background task to generate huddles."""
    try:
        job_id = params.get("job_id")
        
        # Call the huddle generation function
        huddle_outputs = await generate_huddles(params, claude_client)
        
        if huddle_outputs.get("success") is False:
            clean_local_directories(job_id)
            # Send notification with error
            notification_payload = await send_job_completion_notification(params, result=None, error=huddle_outputs.get("error"))
            logging.error(f"Sent job failed notification for job {job_id}")
        else:
            
            # Successful job
            results = huddle_outputs.get("returns")
            logs = huddle_outputs.get("logs")
            
            notification_payload = await send_job_completion_notification(params, result=results, error=None)
            logging.info(f"Sent job completed notification for job {job_id}")
            upload_huddle_logs(
                job_id=job_id,
                provider_id=params.get("provider_id"),
                params=params,
                huddle_plan=logs.get("huddle_plan"),
                response=notification_payload,
                usage=logs.get("token_usage")
            )
        
    except Exception as e:
        print(f"Background job {params.get('job_id')} failed: {e}")


async def generate_huddles(params: dict, claude_client):
    """Generate huddle plan and create PDF files for each huddle."""
    
    # Initialize tracking variables
    total_input_tokens = 0
    total_output_tokens = 0
    total_speech_characters = 0
    
    try: 
        min_words, max_words = get_word_targets(params['duration'])

        # === HUDDLE PLAN GENERATION ===
        plan_prompts = fetch_plan_prompts()
        user_prompt = format_plan_prompt(plan_prompts, params, min_words, max_words)
        plan_response = await generate_plan(claude_client, plan_prompts['system_prompt'], user_prompt)
        
        # Extract plan result and accumulate tokens
        plan_result = plan_response["plan"]
        total_input_tokens += plan_response["tokens"]["input"]
        total_output_tokens += plan_response["tokens"]["output"]

        # === HUDDLE GENERATION ===
        
        huddles = (plan_result or {}).get("huddles") or []
        if not huddles:
            raise ValueError("Huddle plan contains no huddles to generate")
        
        dirs = setup_output_directories(params['job_id'])

        # Prepare retriever (single AI index)
        retriever = PrioritizedRetriever(
            provider_id=params['provider_id'],
            k=settings.INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )

        # Load huddle/document generation prompts
        huddle_prompts = fetch_huddle_prompts()

        # Build dynamic filter from branchState and certificationList (comma-separated)
        ai_filter = retriever.build_ai_filter(
            branch_state=params['branch_state'],
            certifications=params['certifications'],
        )

        # Generate each huddle and create artifacts
        for huddle in huddles:
            huddle_id = huddle.get("id")
            
            # Generate huddle content
            result = await process_single_huddle(
                claude_client, huddle, huddle_id, plan_result, huddles, retriever,
                huddle_prompts, min_words, max_words, params['duration'], ai_filter,
                params['agency_name'], params['branch_name']
            )

            # Accumulate tokens from huddle generation
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]

            content_html = result.get("content_html")

            # Create PDF
            try:
                pdf_path = await create_huddle_pdf(huddle_id, content_html, dirs['pdfs'])
            except Exception as pdf_error:
                logging.error(f"Failed to create PDF for huddle {huddle_id}: {pdf_error}")
                raise pdf_error
        
        token_usage = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_speech_characters": total_speech_characters
        }

        #=== UPLOAD ALL ARTIFACTS TO AZURE BLOB ===
        try:
            upload_result = upload_huddle_artifacts(
                job_id=params["job_id"],
                provider_id=params['provider_id'],
                pdfs_dir=dirs['pdfs'],
                audio_dir=dirs['audio'],
                voicescripts_dir=dirs['voiceovers'],
            )
        except Exception as upload_error:
            logging.error(f"Failed to upload huddle artifacts to Azure Blob: {upload_error}")
            raise upload_error

        clean_local_directories(params["job_id"])
        
        # Initialize an empty list for the generated huddles
        generated_huddles = []
        for i, huddle in enumerate(huddles):
            huddle_id = huddle.get("id")
            
            # Find the corresponding uploaded file paths by matching filenames
            pdf_filename = f"huddle-{huddle_id}.pdf"
            mp3_filename = f"huddle-{huddle_id}.mp3"
            txt_filename = f"huddle-{huddle_id}.txt"
            
            # Find the uploaded paths that match this huddle's files
            pdf_path = next((path for path in upload_result["pdf"] if pdf_filename in path), None)
            audio_path = next((path for path in upload_result["audio_mp3"] if mp3_filename in path), None)
            voicescript_path = next((path for path in upload_result["voicescripts"] if txt_filename in path), None)
            
            if not pdf_path or not audio_path or not voicescript_path:
                logging.error(f"Missing uploaded artifact for huddle {huddle_id}")
                raise ValueError(f"Uploaded artifacts missing for huddle {huddle_id}")
            
            huddle_data = {
                "huddle_index": i + 1,
                "title": huddle.get("title"),
                "pdf_path": pdf_path,
                "audio_path": audio_path,
                "voicescript_path": voicescript_path
            }
            
            generated_huddles.append(huddle_data)

        return {
            "success": True,
            "returns": {
                "title": plan_result.get("curriculum_metadata").get("title"),
                "huddle_duration": params['duration'],
                "huddles": generated_huddles,
            },
            "logs": {
                "token_usage": token_usage,
                "huddle_plan": plan_result
            }
        }
        
    except Exception as e:
        logging.error(f"Error in generate_huddle_pdfs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def send_job_completion_notification(params: dict, result: dict = None, error: str = None):
    """
    Send job completion notification to the callback URL.
    
    if completed: error = none
    if faild; result = none
    """
    
    callback_url = params.get("callback_url")
    job_id = params.get("job_id")
    
    # Prepare the notification payload with dummy data for now
    notification_payload = {
        "jobId": job_id,
        "status": "completed" if error is None else "failed",
        "error": error,
        "providerId": str(params.get("provider_id")),
        "ccn": str(params.get("ccn")),
        "branchId": int(params.get("branch_id")),
        "userId": int(params.get("user_id")),
        "sequenceId": int(params.get("sequence_id")),
        "generated_sequence": result     
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=notification_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HuddleGenerator/1.0"
                }
            )

            if response.status_code != 200:
                logging.error(
                    f"Failed to send notification for job {job_id}. Status: {response.status_code}"
                )
                return {
                    "jobId": job_id,
                    "status": "notification_failed",
                    "error": f"HTTP {response.status_code}",
                }

            return notification_payload

    except httpx.RequestError as e:
        logging.error(f"Request error while sending notification for job {job_id}: {e}")
        return {
            "jobId": job_id,
            "status": "notification_failed",
            "error": str(e),
        }
    except Exception as e:
        logging.error(f"Unexpected error while sending notification for job {job_id}: {e}")
        return {
            "jobId": job_id,
            "status": "notification_failed",
            "error": str(e),
        }