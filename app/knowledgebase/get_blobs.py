from datetime import datetime, timedelta
from typing import Optional

from app.adapters.azure_blob import get_blob_service_client, generate_sas_token


def get_blobs(container: str, directory: Optional[str] = None, expiry_hours: int = 1):
    """
    Return blobs in a container with optional directory/prefix, including 1-time SAS URLs.

    Response shape:
    {
      "container": str,
      "prefix": Optional[str],
      "count": int,
      "items": [
        {"name": str, "size": int|None, "content_type": str|None, "last_modified": iso|None, "etag": str|None, "url": str|None}
      ]
    }
    """
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(container)
    if not container_client.exists():
        raise FileNotFoundError(f"Container '{container}' not found")

    prefix = (directory or "").strip("/")
    if prefix:
        prefix = f"{prefix}/" if not prefix.endswith("/") else prefix

    blobs_iter = container_client.list_blobs(name_starts_with=prefix or None)

    expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)
    items = []
    for blob in blobs_iter:
        try:
            sas = generate_sas_token(container, blob.name, expiry_time)
            url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container}/{blob.name}?{sas}"
        except Exception:
            url = None

        content_type = None
        cs = getattr(blob, "content_settings", None)
        if cs is not None:
            content_type = getattr(cs, "content_type", None)

        items.append({
            "name": blob.name,
            "size": getattr(blob, "size", None),
            "content_type": content_type,
            "last_modified": blob.last_modified.isoformat() if getattr(blob, "last_modified", None) else None,
            "etag": getattr(blob, "etag", None),
            "url": url,
        })

    return {"container": container, "prefix": prefix or None, "count": len(items), "items": items}