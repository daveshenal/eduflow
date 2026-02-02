from app.pipelines.huddle_pipeline import send_job_completion_notification


async def generate_huddles_test(params: dict):
    import asyncio
    
    await asyncio.sleep(10)
    return {
        "title": "Comprehensive Assessment Excellence: Preventing Readmissions Through Enhanced Clinical Evaluation",
        "huddle_duration": params['duration'],
        "huddles": [
            {
                "huddle_index": 1,
                "title": "Post-Hospital Assessment Excellence: Foundation for Readmission Prevention",
                "pdf_path": "provider-595959/huddles/job-12345/huddle-1.pdf",
                "audio_path": "provider-595959/huddles/job-12345/huddle-1.mp3",
                "voicescript_path": "provider-595959/huddles/job-12345/huddle-1.txt",
            },
            {
                "huddle_index": 2,
                "title": "Systematic Assessment Implementation: Building Patient Safety Through Comprehensive Evaluation",
                "pdf_path": "provider-595959/huddles/job-12345/huddle-2.pdf",
                "audio_path": "provider-595959/huddles/job-12345/huddle-2.mp3",
                "voicescript_path": "provider-595959/huddles/job-12345/huddle-2.txt",
            }
        ]   
    }

async def generate_huddles_background_task_test(params: dict):
    """Background task to generate huddles."""
    try:
        job_id = params.get("job_id")
        
        # Call the huddle generation function
        result = await generate_huddles_test(params)
        
        # Send job completion notification to callback URL
        await send_job_completion_notification(params, result)
        
    except Exception as e:
        # If the job fails, update the status to failed
        print(f"Background job {job_id} failed: {e}")