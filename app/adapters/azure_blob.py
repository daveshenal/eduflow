"""Azure Blob Storage client helpers for SAS tokens and connection checks."""

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from config.settings import settings

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(
    settings.AZURE_STORAGE_CONNECTION_STRING
)

ai_saves_container_client = blob_service_client.get_container_client(
    "ai-saves")


def get_blob_service_client():
    """Return the shared BlobServiceClient instance."""
    return blob_service_client


def get_ai_saves_container_client():
    """Return the client for the ai-saves container."""
    return ai_saves_container_client


def generate_sas_token(container_name, blob_name, expiry_time):
    """Generate a read-only SAS token for a blob."""
    # Generate the SAS token with read permissions for the specific blob
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),  # Only read permission
        expiry=expiry_time
    )
    return sas_token


def test_blob_connection(container):
    """Verify that a container exists; return status dict for API responses."""
    container_client = blob_service_client.get_container_client(container)

    if not container_client.exists():
        return {
            "status": "failed",
            "message": f"Container '{container}' not found."
        }

    return {
        "status": "success",
        "message": f"Successfully verified connection to container: {container}"
    }
