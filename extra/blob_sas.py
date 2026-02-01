from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import os

# Set your Azure Storage connection string in environment variable first
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Specify container and blob
container_name = "hop-ai-saves"
blob_name = "provider-595959/ai-1724601234567-42-595959-15-a7b3c9d2/pdf/huddle-1.pdf"

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Generate SAS token (valid for 1 hour)
sas_token = generate_blob_sas(
    account_name=blob_service_client.account_name,
    container_name=container_name,
    blob_name=blob_name,
    account_key=blob_service_client.credential.account_key,
    permission=BlobSasPermissions(read=True),
    expiry=datetime.utcnow() + timedelta(hours=1)
)

# Build full URL
blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

print("Share this URL with your frontend dev:")
print(blob_url)
