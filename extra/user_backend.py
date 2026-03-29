from datetime import datetime
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

# Define the Pydantic models for the job-done notification request

class Doc(BaseModel):
    doc_index: int = Field(..., ge=1)
    title: str
    pdf_path: str
    audio_path: str
    voicescript_path: str

class GeneratedSequence(BaseModel):
    title: str
    doc_duration: int
    docs: List[Doc] = Field(..., min_length=1)

class JobDoneRequest(BaseModel):
    job_id: str
    status: str = Field(..., pattern=r"^(completed|failed)$")
    index_id: str
    generated_sequence: Optional[GeneratedSequence] = None
    error: Optional[str] = None  # include error for failed jobs

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "ai-1724601234567-42-595959-15-a7b3c9d2",
                "status": "completed",
                "index_id": "595959",
                "generated_sequence": {
                    "title": "Weekly Patient Care Review",
                    "doc_duration": 10,
                    "docs": [
                        {
                            "doc_index": 1,
                            "title": "Initial Patient Assessment",
                            "pdf_path": "provider-595959/docs/job-12345/doc-1.pdf",
                            "audio_path": "provider-595959/docs/job-12345/doc-1.mp3",
                            "voicescript_path": "provider-595959/docs/job-12345/doc-1.txt"
                        },
                        {
                            "doc_index": 2,
                            "title": "Documentation Best Practices",
                            "pdf_path": "provider-595959/docs/job-12345/doc-2.pdf",
                            "audio_path": "provider-595959/docs/job-12345/doc-2.mp3",
                            "voicescript_path": "provider-595959/docs/job-12345/doc-2.txt"
                        }
                    ]
                }
            }
        }
    }

@app.post("/job-done", description="Endpoint to receive notifications when doc generation job completed")
async def job_done(request: JobDoneRequest):

    if request.status == "completed":
        if not request.generated_sequence or len(request.generated_sequence.docs) == 0:
            raise HTTPException(
                status_code=400,
                detail="Completed jobs must include at least one doc in generated_sequence"
            )

    # Print log with current local time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*50)
    print(f"RECEIVED JOB DONE REQUEST at {current_time}")
    print("="*50)
    print(json.dumps(request.model_dump(), indent=2, ensure_ascii=False))
    print("="*50 + "\n")

    return {
        "message": "Job notification received successfully",
        "job_id": request.job_id,
        "status": request.status,
        "success": True,
    }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)