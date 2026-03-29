from app.pipelines.gen_pipeline import send_job_completion_notification


async def generate_content_test(params: dict):
    import asyncio

    await asyncio.sleep(10)
    return {
        "title": "Comprehensive Assessment Excellence: Preventing Readmissions Through Enhanced Clinical Evaluation",
        "doc_duration": params['duration'],
        "docs": [
            {
                "doc_index": 1,
                "title": "Post-Hospital Assessment Excellence: Foundation for Readmission Prevention",
                "pdf_path": "index-595959/docs/job-12345/doc-1.pdf",
                "audio_path": "index-595959/docs/job-12345/doc-1.mp3",
                "voicescript_path": "index-595959/docs/job-12345/doc-1.txt",
            },
            {
                "doc_index": 2,
                "title": "Systematic Assessment Implementation: Building Patient Safety Through Comprehensive Evaluation",
                "pdf_path": "index-595959/docs/job-12345/doc-2.pdf",
                "audio_path": "index-595959/docs/job-12345/doc-2.mp3",
                "voicescript_path": "index-595959/docs/job-12345/doc-2.txt",
            }
        ]
    }

async def generate_content_background_task_test(params: dict):
    """Background task to generate docs."""
    try:
        job_id = params.get("job_id")

        # Call the doc generation function
        result = await generate_content_test(params)

        # Send job completion notification to callback URL
        await send_job_completion_notification(params, result)

    except Exception as e:
        # If the job fails, update the status to failed
        print(f"Background job {job_id} failed: {e}")
