import json
from pathlib import Path
import logging
import mimetypes
import tempfile

from app.adapters.azure_blob import get_hop_saves_container_client


def _iter_local_files(directory: Path):
    if not directory.exists():
        return []
    return [p for p in directory.iterdir() if p.is_file()]


def upload_huddle_artifacts(
    job_id:str,
    provider_id: str,
    pdfs_dir: Path,
    audio_dir: Path,
    voicescripts_dir: Path,
    huddle_plan: dict = None
) -> dict:
    """
    Upload generated huddle artifacts to Azure Blob Storage in the structure:
      provider-{provider_id}/huddle-seq-{role}-{discipline}-{datetime}/{pdf|audio_mp3|voicescripts|huddle_plan}/<files>

    Returns a dict with blob paths uploaded per category.
    """

    base_prefix = f"provider-{provider_id}/{job_id}"

    container_client = get_hop_saves_container_client()

    uploads = {"pdf": [], "audio_mp3": [], "voicescripts": []}

    def _upload_file(local_path: Path, prefix: str):
        blob_path = f"{prefix}/{local_path.name}"
        content_settings = None
        mime, _ = mimetypes.guess_type(local_path.name)
        try:
            from azure.storage.blob import ContentSettings
            if mime:
                content_settings = ContentSettings(content_type=mime)
        except Exception:
            content_settings = None

        with open(local_path, "rb") as f:
            container_client.upload_blob(
                name=blob_path,
                data=f,
                overwrite=True,
                content_settings=content_settings,
            )
        return blob_path

    try:
        # Upload huddle plan if provided
        if huddle_plan:
            try:
                # Create a temporary file for the huddle plan
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                    json.dump(huddle_plan, temp_file, indent=2, ensure_ascii=False)
                    temp_file_path = Path(temp_file.name)
                
                # Upload the huddle plan to blob storage
                blob_path = _upload_file(temp_file_path, f"{base_prefix}/huddle_plan")
                logging.info(f"Uploaded huddle plan to: {blob_path}")
                
                # Clean up temporary file
                temp_file_path.unlink()
            except Exception as plan_upload_error:
                logging.warning(f"Failed to upload huddle plan: {plan_upload_error}")
                # Continue with other uploads even if plan upload fails

        for file_path in _iter_local_files(pdfs_dir):
            blob_path = _upload_file(file_path, f"{base_prefix}/pdf")
            uploads["pdf"].append(blob_path)

        for file_path in _iter_local_files(audio_dir):
            blob_path = _upload_file(file_path, f"{base_prefix}/audio_mp3")
            uploads["audio_mp3"].append(blob_path)

        for file_path in _iter_local_files(voicescripts_dir):
            blob_path = _upload_file(file_path, f"{base_prefix}/voicescripts")
            uploads["voicescripts"].append(blob_path)

        logging.info(
            "Uploaded huddle artifacts to container '%s' with base prefix '%s'",
            container_client.container_name,
            base_prefix,
        )
        return uploads

    except Exception as e:
        logging.error(f"Failed to upload huddle artifacts: {e}")
        raise


if __name__ == "__main__":
    import json
    import sys
    
    # Define inputs here directly
    provider_id = "595959"
    job_id = "job-12345"
    pdfs_dir = Path("temp/huddles/pdfs")
    audio_dir = Path("temp/huddles/audio_mp3s")
    voicescripts_dir = Path("temp/huddles/voicescripts")

    # Validate directories
    for label, path in [
        ("pdfs-dir", pdfs_dir),
        ("audio-dir", audio_dir),
        ("voicescripts-dir", voicescripts_dir),
    ]:
        if not path.exists() or not path.is_dir():
            print(f"Error: {label} '{path}' does not exist or is not a directory.")
            sys.exit(2)

    # Call upload function
    try:
        result = upload_huddle_artifacts(
            job_id=job_id,
            provider_id=provider_id,
            pdfs_dir=pdfs_dir,
            audio_dir=audio_dir,
            voicescripts_dir=voicescripts_dir,
            huddle_plan={"test": "plan", "huddles": []}
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        sys.exit(1)
