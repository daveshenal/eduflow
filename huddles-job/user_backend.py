from datetime import datetime
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

# Define the Pydantic models for the job-done notification request

class Huddle(BaseModel):
    huddle_index: int = Field(..., ge=1)
    title: str
    pdf_path: str
    audio_path: str
    voicescript_path: str

class GeneratedSequence(BaseModel):
    title: str
    huddle_duration: int
    huddles: List[Huddle] = Field(..., min_length=1)

class JobDoneRequest(BaseModel):
    jobId: str
    status: str = Field(..., pattern=r"^(completed|failed)$")
    providerId: str
    ccn: str
    branchId: int
    userId: int
    sequenceId: int
    generated_sequence: Optional[GeneratedSequence] = None
    error: Optional[str] = None  # include error for failed jobs

    model_config = {
        "json_schema_extra": {
            "example": {
                "jobId": "ai-1724601234567-42-595959-15-a7b3c9d2",
                "status": "completed",
                "providerId": "595959",
                "ccn": "123456789",
                "branchId": 15,
                "userId": 42,
                "sequenceId": 123,
                "generated_sequence": {
                    "title": "Weekly Patient Care Review",
                    "huddle_duration": 10,
                    "huddles": [
                        {
                            "huddle_index": 1,
                            "title": "Initial Patient Assessment",
                            "pdf_path": "provider-595959/huddles/job-12345/huddle-1.pdf",
                            "audio_path": "provider-595959/huddles/job-12345/huddle-1.mp3",
                            "voicescript_path": "provider-595959/huddles/job-12345/huddle-1.txt"
                        },
                        {
                            "huddle_index": 2,
                            "title": "Documentation Best Practices",
                            "pdf_path": "provider-595959/huddles/job-12345/huddle-2.pdf",
                            "audio_path": "provider-595959/huddles/job-12345/huddle-2.mp3",
                            "voicescript_path": "provider-595959/huddles/job-12345/huddle-2.txt"
                        }
                    ]
                }
            }
        }
    }

@app.post("/job-done", description="Endpoint to receive notifications when huddle generation job completed")
async def job_done(request: JobDoneRequest):

    if request.status == "completed":
        if not request.generated_sequence or len(request.generated_sequence.huddles) == 0:
            raise HTTPException(
                status_code=400,
                detail="Completed jobs must include at least one huddle in generated_sequence"
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
        "jobId": request.jobId,
        "status": request.status,
        "success": True,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)