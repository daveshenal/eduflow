import json
from pathlib import Path
import logging
import mimetypes
import io

from app.adapters.azure_blob import get_hop_saves_container_client
from azure.storage.blob import ContentSettings


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
) -> dict:
    """
    Upload generated huddle artifacts to Azure Blob Storage in the structure:
      provider-{provider_id}/{job_id}/{pdf|audio_mp3|voicescripts}/<files>

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
    
    
def upload_huddle_logs(
    job_id:str,
    provider_id: str,
    params: dict,
    huddle_plan: dict,
    response: dict,
    usage: dict
) -> dict:
    """
    Upload logs for generated huddle artifacts to Azure Blob Storage in the structure:
      provider-{provider_id}/{job_id}/logs/<files>
    """

    base_prefix = f"provider-{provider_id}/{job_id}/logs"

    container_client = get_hop_saves_container_client()

    def _upload_json(data: dict, blob_name: str, prefix: str):
        """Upload a JSON dict directly to blob storage without saving locally."""

        blob_path = f"{prefix}/{blob_name}"
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

        container_client.upload_blob(
            name=blob_path,
            data=io.BytesIO(json_bytes),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
        return blob_path

    try:
        blob_path = _upload_json(huddle_plan, "huddle_plan.json", f"{base_prefix}")
        logging.info(f"Uploaded huddle plan to: {blob_path}")
        
        blob_path = _upload_json(params, "input_params.json", f"{base_prefix}")
        logging.info(f"Uploaded input params to: {blob_path}")
        
        blob_path = _upload_json(response, "response.json", f"{base_prefix}")
        logging.info(f"Uploaded response to: {blob_path}")
        
        blob_path = _upload_json(usage, "usage.json", f"{base_prefix}")
        logging.info(f"Uploaded usage to: {blob_path}")
        
        logging.info(
            "Uploaded huddle logs to container '%s' with base prefix '%s'",
            container_client.container_name,
            base_prefix,
        )

    except Exception as plan_upload_error:
        logging.warning(f"Failed to upload huddle plan: {plan_upload_error}")
        raise