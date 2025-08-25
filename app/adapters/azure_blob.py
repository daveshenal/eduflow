from azure.storage.blob import BlobServiceClient
from config.settings import settings

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)

hop_saves_container_client = blob_service_client.get_container_client("ai-saves")

def get_blob_service_client():
    return blob_service_client

def get_hop_saves_container_client():
    return hop_saves_container_client