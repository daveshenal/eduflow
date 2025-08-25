from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from config.settings import settings

main_search_client = SearchClient(
    endpoint=settings.AZURE_SEARCH_ENDPOINT,
    index_name=settings.AZURE_GLOBAL_INDEX_NAME,
    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
)

search_index_client = SearchIndexClient(
    endpoint=settings.AZURE_SEARCH_ENDPOINT,
    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
)

# Initialize the SearchIndexerClient for managing indexers
search_indexer_client = SearchIndexerClient(
    endpoint=settings.AZURE_SEARCH_ENDPOINT,
    credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
)

def get_global_search_client():
    return main_search_client

def get_search_index_client():
    return search_index_client

def get_search_indexer_client():
    return search_indexer_client