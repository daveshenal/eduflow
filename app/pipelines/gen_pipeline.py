from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict
import json
import shutil
import httpx

from config.settings import settings
from app.retrievers.index_data_retriver import PrioritizedRetriever
from app.adapters.azure_sql import get_db_connection
from app.core.content_upload import upload_artifacts, upload_generation_logs
from app.core.curriculem_plan_service import get_word_targets, fetch_plan_prompts, format_plan_prompt, generate_plan
from app.core.content_service import fetch_pdf_prompts, process_single_doc
from app.core.pdf_generator import create_pdf

class BackgroundJob:
    def __init__(self, job_id: str, index_id: str, callback_url: str):
        self.job_id = job_id
        self.index_id = index_id
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
        "job_id", "callback_url", "index_id", "learning_focus", "topic", 
        "target_audience", "duration", "num_docs", "voice"
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
        "job_id": payload.get("job_id"),
        "callback_url": payload.get("callback_url"),
        "index_id": payload.get("index_id"),
        "learning_focus": payload.get("learning_focus"),
        "topic": payload.get("topic"),
        "target_audience": payload.get("target_audience"),
        "duration": int(payload.get("duration")),
        "num_docs": int(payload.get("num_docs")),
        "voice": payload.get("voice"),
    }


def setup_output_directories(job_id: str) -> dict:
    """Create and return output directory paths for a specific job."""
    base_dir = Path("temp/generated_content") / job_id
    base_dir.mkdir(parents=True, exist_ok=True)
    
    dirs = {
        'plan': base_dir / "plan",
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


async def generate_content_background_task(params: dict, claude_client):
    """Background task to generate huddles."""
    try:
        job_id = params.get("job_id")
        
        from app.adapters.azure_sql import create_bg_job, update_huddle_job
        await create_bg_job(
            job_id=job_id,
            index_id=params.get("index_id"),
            callback_url=params.get("callback_url"),
            status="queued",
            message="Generating Huddles...",
        )
        # Call the huddle generation function
        huddle_outputs = await generate_content(params, claude_client)
        
        if huddle_outputs.get("success") is False:
            print(huddle_outputs.get("error"))
            await update_huddle_job(
                job_id=job_id,
                status="Failed",
                message="Huddle generation failed",
                result_text=json.dumps(huddle_outputs.get("error")) if huddle_outputs else None,
            )
            
            # clean_local_directories(job_id)
            # Send notification with error
            notification_payload = await send_job_completion_notification(params, result=None, error=huddle_outputs.get("error"))
        else:
            await update_huddle_job(
                job_id=job_id,
                status="completed",
                message="Huddle generation completed successfully",
                result_text=json.dumps(huddle_outputs.get("returns")) if huddle_outputs else None,
            )
            
            results = huddle_outputs.get("returns")
            logs = huddle_outputs.get("logs")
            
            notification_payload = await send_job_completion_notification(params, result=results, error=None)
            logging.info(f"Sent job completed notification for job {job_id}")
            upload_generation_logs(
                job_id=job_id,
                index_id=params.get("index_id"),
                params=params,
                plan=logs.get("plan"),
                response=notification_payload,
                usage=logs.get("token_usage")
            )
        
    except Exception as e:
        await send_job_completion_notification(params, result=None, error=str(e))
        logging.error(f"Background job {params.get('job_id')} failed: {e}")


async def generate_content(params: dict, claude_client):
    """Generate a curriculum plan and create PDF files."""
    
    total_input_tokens = 0
    total_output_tokens = 0
    try:
        dirs = setup_output_directories(params["job_id"])
        
        min_words, max_words = get_word_targets(params['duration'])

        # === PLAN GENERATION (prompts from prompt manager) ===
        async with get_db_connection() as db_conn:
            plan_prompts = await fetch_plan_prompts(db_conn)
        user_prompt = format_plan_prompt(plan_prompts, params, min_words, max_words)
        plan_response = await generate_plan(claude_client, plan_prompts['system_prompt'], user_prompt)

        # Extract plan result and accumulate tokens
        plan_result = plan_response["plan"]
        total_input_tokens += plan_response["tokens"]["input"]
        total_output_tokens += plan_response["tokens"]["output"]

        # # Save plan locally
        # plan_file_path = dirs["plan"] / "plan.json"
        # plan_file_path.write_text(json.dumps(plan_result, indent=2, default=str), encoding="utf-8")
        # logging.info("Saved plan to %s", plan_file_path.resolve())
        
        
        # plan_file_path = dirs["plan"] / "plan.json"
        # if plan_file_path.exists():
        #     # Load existing plan
        #     plan_result = json.loads(plan_file_path.read_text(encoding="utf-8"))
        #     logging.info("Loaded existing plan from %s", plan_file_path.resolve())
        # else:
        #     raise FileNotFoundError(f"Plan file not found: {plan_file_path}")

        # === CONTENT + PDF GENERATION (save docs locally) ===
        docs = (plan_result or {}).get("docs") or []
        if not docs:
            raise ValueError("Plan contains no docs to generate")

        retriever = PrioritizedRetriever(
            index_id=params["index_id"],
            k=settings.INDEX_TOP_K,
            min_score=settings.MIN_SCORE,
        )

        async with get_db_connection() as db_conn:
            pdf_prompts = await fetch_pdf_prompts(db_conn)

        for doc in docs:
            doc_id = doc.get("id")

            # Generate pdf content
            result = await process_single_doc(
                claude_client, doc, doc_id, plan_result, docs, retriever,
                pdf_prompts, min_words, max_words, params["duration"],
            )
            
            # # Accumulate tokens from pdf generation
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]
            content_html = result.get("content_html")

            try:
                pdf_path = await create_pdf(doc_id, content_html, dirs["pdfs"])
            except Exception as pdf_error:
                logging.error("Failed to create PDF for doc %s: %s", doc_id, pdf_error)
                raise

        token_usage = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        }
        
        #=== UPLOAD ALL ARTIFACTS TO AZURE BLOB ===
        try:
            upload_result = upload_artifacts(
                job_id=params["job_id"],
                index_id=params['index_id'],
                pdfs_dir=dirs['pdfs'],
                audio_dir=dirs['audio'],
                voicescripts_dir=dirs['voiceovers'],
            )
        except Exception as upload_error:
            logging.error(f"Failed to upload doc artifacts to Azure Blob: {upload_error}")
            raise upload_error
        
        # clean_local_directories(params["job_id"])
        
        # Initialize an empty list for the generated documents
        generated_docs = []
        for i, doc in enumerate(docs):
            doc_id = doc.get("id")
            
            # Find the corresponding uploaded file paths by matching filenames
            pdf_filename = f"doc-{doc_id}.pdf"
            mp3_filename = f"voiceover-{doc_id}.mp3"
            txt_filename = f"voicescript-{doc_id}.txt"
            
            print(upload_result)
            
            # Find the uploaded paths that match this huddle's files
            pdf_path = next((path for path in upload_result["pdf"] if pdf_filename in path), None)
            # audio_path = next((path for path in upload_result["audio_mp3"] if mp3_filename in path), None)
            # voicescript_path = next((path for path in upload_result["voicescripts"] if txt_filename in path), None)
            
            print(f'pdf_path:{pdf_path}')
            
            # if not pdf_path or not audio_path or not voicescript_path:
            if not pdf_path:
                logging.error(f"Missing uploaded artifact for doc {doc_id}")
                raise ValueError(f"Uploaded artifacts missing for doc {doc_id}")
            
            doc_data = {
                "doc_index": i + 1,
                "title": doc.get("title"),
                "pdf_path": pdf_path,
                "audio_path": mp3_filename,
                "voicescript_path": txt_filename
            }
            
            generated_docs.append(doc_data)

        return {
            "success": True,
            "returns": {
                "title": plan_result.get("curriculum_metadata").get("title"),
                "doc_duration": params['duration'],
                "docs": generated_docs,
            },
            "logs": {
                "token_usage": token_usage,
                "plan": plan_result
            }
        }
        
    except Exception as e:
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
        "job_id": job_id,
        "status": "completed" if error is None else "failed",
        "error": error,
        "index_id": str(params.get("index_id")),
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
                    "job_id": job_id,
                    "status": "notification_failed",
                    "error": f"HTTP {response.status_code}",
                }

            return notification_payload

    except httpx.RequestError as e:
        logging.error(f"Request error while sending notification for job {job_id}: {e}")
        return {
            "job_id": job_id,
            "status": "notification_failed",
            "error": str(e),
        }
    except Exception as e:
        logging.error(f"Unexpected error while sending notification for job {job_id}: {e}")
        return {
            "job_id": job_id,
            "status": "notification_failed",
            "error": str(e),
        }