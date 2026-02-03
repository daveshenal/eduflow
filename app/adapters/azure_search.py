from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from config.settings import settings


def get_search_client(index_name: str) -> SearchClient:
    """Get SearchClient for a specific index (e.g. ai-index-{index_id})."""
    return SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )


def get_search_index_client():
    search_index_client = SearchIndexClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )
    
    return search_index_client

def get_search_indexer_client():
    search_indexer_client = SearchIndexerClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )
    
    return search_indexer_client