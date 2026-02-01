from azure.storage.blob import BlobServiceClient
import os

# Azure Blob Storage connection string
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# Blob path (container name and blob name)
container_name = "hop-ai-saves"
blob_name = "provider-595959/ai-1724601234567-42-595959-15-a7b3c9d2/pdf/huddle-1.pdf" # path retruned by job done request

# Local file path to save the downloaded file
download_file_path = "local_file.pdf"

def download_blob():
    try:
        # Initialize BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Get a blob client to interact with the blob
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # Download the blob to a file
        with open(download_file_path, "wb") as file:
            blob_data = blob_client.download_blob()
            file.write(blob_data.readall())
        
        print(f"Blob downloaded successfully to {download_file_path}")
    
    except Exception as e:
        print(f"Error downloading blob: {e}")

# Run the function to download the blob
download_blob()