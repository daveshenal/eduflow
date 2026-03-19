from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
from config.settings import settings

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)

ai_saves_container_client = blob_service_client.get_container_client("ai-saves")

def get_blob_service_client():
    return blob_service_client

def get_ai_saves_container_client():
    return ai_saves_container_client

def generate_sas_token(container_name, blob_name, expiry_time):    
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