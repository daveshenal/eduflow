from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict
import json
import shutil
import httpx

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.core.huddle_upload import upload_huddle_artifacts, upload_huddle_logs
from app.core.huddle_plan_service import get_word_targets, fetch_plan_prompts, format_plan_prompt, generate_plan
from app.core.huddle_content_service import fetch_huddle_prompts, process_single_huddle
from app.core.pdf_generator import create_huddle_pdf
from app.core.voicescript_service import generate_voiceover_script
from app.core.audio_generator import generate_mp3_from_file


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
        "providerId", "jobId", "callbackUrl", "ccn", "branchId", "userId", 
        "sequenceId", "learningFocus", "topic", "clinicalContext", "role", 
        "roleValue", "discipline", "disciplineValue", "learningLevel",
        "duration", "numHuddles", "voice", "branchState", "certificationList",
        "agencyName", "branchName"
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
        "ccn": payload.get("ccn"),
        "branch_id": payload.get("branchId"),
        "user_id": payload.get("userId"),
        "sequence_id": payload.get("sequenceId"),
        "learning_focus": payload.get("learningFocus"),
        "topic": payload.get("topic"),
        "clinical_context": payload.get("clinicalContext"),
        "role_label": payload.get("role"),
        "role_value": payload.get("roleValue"),
        "discipline_label": payload.get("discipline"),
        "discipline_value": payload.get("disciplineValue"),
        "learning_level": payload.get("learningLevel"),
        "duration": int(payload.get("duration")),
        "num_huddles": int(payload.get("numHuddles")),
        "voice": payload.get("voice"),
        "branch_state": payload.get("branchState"),
        "certifications": payload.get("certificationList"),
        "agency_name": payload.get("agencyName"),
        "branch_name": payload.get("branchName"),  
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
        # Persist initial job row and mark processing
        from app.adapters.azure_sql import create_huddle_job, update_huddle_job
        await create_huddle_job(
            job_id=job_id,
            sequence_id=params.get("sequence_id"),
            provider_id=params.get("provider_id"),
            ccn=params.get("ccn"),
            branch_id=params.get("branch_id"),
            user_id=params.get("user_id"),
            callback_url=params.get("callback_url"),
            status="queued",
            message="Job queued for processing",
        )
        await update_huddle_job(job_id=job_id, status="processing", message="Generating Huddles...")
        
        # Call the huddle generation function
        huddle_outputs = await generate_huddles(params, claude_client)
        
        if huddle_outputs.get("success") is False:
            # Update job to completed state
            await update_huddle_job(
                job_id=job_id,
                status="Failed",
                message="Huddle generation failed",
                result_text=json.dumps(huddle_outputs.get("error")) if huddle_outputs else None,
            )
            
            clean_local_directories(job_id)
            # Send notification with error
            notification_payload = await send_job_completion_notification(params, result=None, error=huddle_outputs.get("error"))
            logging.error(f"Sent job failed notification for job {job_id}")
        else:
            await update_huddle_job(
                job_id=job_id,
                status="completed",
                message="Huddle generation completed successfully",
                result_text=json.dumps(huddle_outputs.get("returns")) if huddle_outputs else None,
            )
            
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
        # If the job fails, update the status to failed
        from app.adapters.azure_sql import update_huddle_job
        try:
            await update_huddle_job(
                job_id=params.get("job_id"),
                status="failed",
                message=f"Huddle generation failed: {str(e)}",
                error_text=str(e),
            )
        except Exception:
            pass
        print(f"Background job {params.get('job_id')} failed: {e}")


async def generate_huddles(params: dict, claude_client):
    """Generate huddle plan and create PDF files for each huddle."""
    
    # Initialize tracking variables
    total_input_tokens = 0
    total_output_tokens = 0
    total_speech_characters = 0
    
    try: 
        min_words, max_words = get_word_targets(params['duration'])
        action_plan = retrieve_action_plan(params['ccn'])

        # === HUDDLE PLAN GENERATION ===
        
        prompts = await fetch_plan_prompts(params['role_value'], params['discipline_value'])
        user_prompt = format_plan_prompt(prompts, params, action_plan, min_words, max_words)
        plan_response = await generate_plan(claude_client, prompts['system_prompt'], user_prompt)
        
        # Extract plan result and accumulate tokens
        plan_result = plan_response["plan"]
        total_input_tokens += plan_response["tokens"]["input"]
        total_output_tokens += plan_response["tokens"]["output"]

        # === HUDDLE GENERATION ===
        
        huddles = (plan_result or {}).get("huddles") or []
        if not huddles:
            raise ValueError("Huddle plan contains no huddles to generate")
        
        dirs = setup_output_directories(params['job_id'])

        # Prepare retriever
        retriever = PrioritizedRetriever(
            provider_id=params['provider_id'],
            provider_k=settings.PROVIDER_INDEX_TOP_K,
            global_k=settings.GLOBAL_INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )

        huddle_prompts = await fetch_huddle_prompts()

        # Build dynamic global filter from branchState and certificationList (comma-separated)
        global_filter = retriever.build_global_filter(
            branch_state=params['branch_state'],
            certifications=params['certifications'],
        )

        # Generate each huddle and create artifacts
        for huddle in huddles:
            huddle_id = huddle.get("id")
            
            # Generate huddle content
            result = await process_single_huddle(
                claude_client, huddle, huddle_id, plan_result, huddles, retriever,
                huddle_prompts, min_words, max_words, params['duration'], global_filter,
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

            # Generate voiceover
            try:
                voiceover_payload = {
                    "huddleHtml": content_html,
                    "tone": "professional, warm, clear",
                    "paceWpm": 140,
                    "duration": params['duration']
                }
                voiceover_response = await generate_voiceover_script(payload=voiceover_payload, claude_client=claude_client)
                
                # Accumulate tokens from voiceover generation
                total_input_tokens += voiceover_response["tokens"]["input"]
                total_output_tokens += voiceover_response["tokens"]["output"]
                
                voiceover_script = voiceover_response["script"]
                
                # Count characters for Azure Speech
                total_speech_characters += len(voiceover_script)
                
                voiceover_filename = f"huddle-{huddle_id}.txt"
                voiceover_path = dirs['voiceovers'] / voiceover_filename
                with open(voiceover_path, 'w', encoding='utf-8') as f:
                    f.write(voiceover_script)

                # Generate MP3
                try:
                    mp3_filename = f"huddle-{huddle_id}.mp3"
                    mp3_path = dirs['audio'] / mp3_filename
                    generate_mp3_from_file(
                        text_file_path=str(voiceover_path),
                        output_file_path=mp3_path,
                        voice = params.get("voice"),
                        speed="medium",
                        pitch="medium"
                    )

                except Exception as mp3_error:
                    logging.error(f"Failed to generate MP3 for huddle {huddle_id}: {mp3_error}")
                    raise mp3_error
            except Exception as voiceover_error:
                logging.error(f"Failed to generate voiceover for huddle {huddle_id}: {voiceover_error}")
                raise voiceover_error
        
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
    """Send job completion notification to the callback URL.
    
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