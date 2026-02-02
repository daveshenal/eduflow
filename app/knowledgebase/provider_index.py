import json
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataSourceType,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    FieldMapping,
    SearchIndexerSkillset,
    SplitSkill,
    AzureOpenAIEmbeddingSkill,
    IndexingParameters,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector
)

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from app.adapters.azure_search import get_search_index_client, get_search_indexer_client
from config.settings import settings
import time

class ProviderIndex:
    def __init__(self, provider_id: str,):
        
        self.search_index_client = get_search_index_client()
        self.search_indexer_client = get_search_indexer_client()
        self.blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
        self.index = f"provider-index-{provider_id}"
        self.azure_oai_endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.azure_oai_key = settings.AZURE_OPENAI_KEY
        self.emb_deployment_name = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self.emb_model_name = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self.storage_connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.blob_container_name = f"provider-{provider_id}"
        self.chunk_size = settings.MAX_CHUNK_SIZE     
        self.chunk_overlap = settings.CHUNK_OVERLAP     
        self.emb_dimentions = settings.EMBEDDING_DIMENSIONS
        
    def create_blob_container(self):
        """Create Azure Blob Storage container if it doesn't exist"""
        
        try:
            container_client = self.blob_service_client.create_container(
                name=self.blob_container_name,
                public_access=None  # Private container
            )
            print(f"Container '{self.blob_container_name}' created successfully")
            return container_client
            
        except ResourceExistsError:
            print(f"Container '{self.blob_container_name}' already exists")
            return self.blob_service_client.get_container_client(self.blob_container_name)
            
        except Exception as e:
            print(f"Error creating container '{self.blob_container_name}': {e}")
            raise

    def create_search_index(self):
        """Create Azure AI Search index with vector search capabilities and vectorizer"""
        
        print(f"Creating or updating index: {self.index}")
        
        # Define the search fields
        fields = [
            SearchableField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                key=True,
                searchable=True,
                analyzer_name="keyword"
            ),
            SimpleField(name="parent_id", type=SearchFieldDataType.String, filterable=True),  # Required for indexProjections
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="source_path", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=settings.EMBEDDING_DIMENSIONS,
                vector_search_profile_name="default-vector-profile",
                hidden=False  # ensures retrievable
            )
        ]
        
        # Configure vectorizer
        vectorizer = AzureOpenAIVectorizer(
            vectorizer_name="content-vectorizer",
            kind="azureOpenAI",
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=self.azure_oai_endpoint,
                deployment_name=self.emb_deployment_name,
                api_key=self.azure_oai_key,
                model_name=self.emb_model_name
            )
        )
        
        # Configure vector search with vectorizer
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-algorithm-config",
                    vectorizer_name="content-vectorizer"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default-algorithm-config",
                    kind=VectorSearchAlgorithmKind.HNSW
                )
            ],
            vectorizers=[vectorizer]
        )
        
        # Create the search index
        index = SearchIndex(
            name=self.index,
            fields=fields,
            vector_search=vector_search
        )
        
        try:
            result = self.search_index_client.create_or_update_index(index)
            print(f"Index {self.index} created successfully with vectorizer")
            return result
        except Exception as e:
            print(f"Error creating index: {e}")
            raise

    def create_blob_data_source(self):
        """Create a blob data source for the indexer"""
        
        data_source = SearchIndexerDataSourceConnection(
            name=f"{self.index}-blob-datasource",
            type=SearchIndexerDataSourceType.AZURE_BLOB,
            connection_string=self.storage_connection_string,
            container=SearchIndexerDataContainer(
                name=self.blob_container_name
            )
        )
        
        try:
            result = self.search_indexer_client.create_or_update_data_source_connection(data_source)
            print(f"Data source created successfully: {data_source.name}")
            return result
        except Exception as e:
            print(f"Error creating data source: {e}")
            raise

    def create_skillset(self):
        """Create a skillset for document processing and chunking with indexProjections"""
        
        # Text splitting skill for chunking
        split_skill = SplitSkill(
            name="split-skill",
            description="Split content into manageable pages",
            context="/document",
            odata_type="#Microsoft.Skills.Text.SplitSkill",
            text_split_mode="pages",
            maximum_page_length=self.chunk_size,
            page_overlap_length=self.chunk_overlap,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/content")
            ],
            outputs=[
                OutputFieldMappingEntry(name="textItems", target_name="pages")
            ]
        )
        
        # Azure OpenAI Embedding skill
        embedding_skill = AzureOpenAIEmbeddingSkill(
            name="embedding-skill",
            description="Generate embeddings using Azure OpenAI",
            context="/document/pages/*",
            resource_url=self.azure_oai_endpoint,
            deployment_name=self.emb_deployment_name,
            api_key=self.azure_oai_key,
            odata_type="#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
            model_name=self.emb_model_name,
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/pages/*")
            ],
            outputs=[
                OutputFieldMappingEntry(name="embedding", target_name="content_vector")
            ],
            dimensions=self.emb_dimentions
        )
        
        # Define index projections
        index_projection = SearchIndexerIndexProjection(
            selectors=[
                SearchIndexerIndexProjectionSelector(
                    target_index_name=self.index,
                    parent_key_field_name="parent_id",
                    source_context="/document/pages/*",
                    mappings=[
                        InputFieldMappingEntry(name="category", source="/document/category"),
                        InputFieldMappingEntry(name="source_name", source="/document/metadata_storage_name"),
                        InputFieldMappingEntry(name="source_path", source="/document/metadata_storage_path"),
                        InputFieldMappingEntry(name="created_at", source="/document/created_at"),
                        InputFieldMappingEntry(name="content", source="/document/pages/*"),
                        InputFieldMappingEntry(name="content_vector", source="/document/pages/*/content_vector"),
                    ]
                )
            ],
            parameters={
                "projectionMode": "skipIndexingParentDocuments"
            }
        )

        # Create the skillset
        skillset = SearchIndexerSkillset(
            name=f"{self.index}-skillset",
            description="Skillset for document processing and embedding generation",
            skills=[split_skill, embedding_skill],
            index_projection=index_projection
        )
        
        try:
            result = self.search_indexer_client.create_or_update_skillset(skillset)
            print(f"Skillset created successfully: {skillset.name}")
            return result
        except Exception as e:
            print(f"Error creating skillset: {e}")
            raise

    def create_indexer(self):
        """Create an indexer to process documents from blob storage"""
        
        # Configure indexing parameters
        indexing_parameters = IndexingParameters(
            batch_size=5,  # Reduced batch size for better error handling
            max_failed_items=5,  # Allow some failures
            max_failed_items_per_batch=2,
            configuration={
                "parsingMode": "default",
                "dataToExtract": "contentAndMetadata",
                "imageAction": "none",
                "failOnUnsupportedContentType": False,
                "failOnUnprocessableDocument": False,
            }
        )
        
        # Field mappings from blob metadata to index fields (for parent document)
        field_mappings = [
            FieldMapping(
                source_field_name="id",
                target_field_name="parent_id"
            ),
            FieldMapping(
                source_field_name="category",
                target_field_name="category"
            ),
            FieldMapping(
                source_field_name="metadata_storage_name",
                target_field_name="source_name"
            ),
            FieldMapping(
                source_field_name="metadata_storage_path",
                target_field_name="source_path"
            ),
            FieldMapping(
                source_field_name="created_at",
                target_field_name="created_at"
            ),
            FieldMapping(
                source_field_name="content",
                target_field_name="content"
            ),
        ]
        
        indexer = SearchIndexer(
            name=f"{self.index}-indexer",
            description="Indexer for processing blob documents",
            data_source_name=f"{self.index}-blob-datasource",
            target_index_name=self.index,
            skillset_name=f"{self.index}-skillset",
            parameters=indexing_parameters,
            field_mappings=field_mappings,
            # output_field_mappings parameter removed - using indexProjections in skillset
            schedule=None
        )
        
        try:
            result = self.search_indexer_client.create_or_update_indexer(indexer)
            print(f"Indexer created successfully: {indexer.name}")
            return result
        except Exception as e:
            print(f"Error creating indexer: {e}")
            raise

    def run_indexer(self):
        """Run the indexer to process documents"""
        
        indexer_name = f"{self.index}-indexer"
        
        try:
            # Reset the indexer first to clear any previous state
            self.search_indexer_client.reset_indexer(indexer_name)
            print(f"Indexer {indexer_name} reset successfully")
            
            # Run the indexer
            result = self.search_indexer_client.run_indexer(indexer_name)
            print(f"Indexer {indexer_name} started successfully")
            
            # Monitor indexer status
            self.monitor_indexer_status(indexer_name)
            
            return result
        except Exception as e:
            print(f"Error running indexer: {e}")
            raise

    def monitor_indexer_status(self, indexer_name):
        print(f"Monitoring indexer {indexer_name}...")
        while True:
            status = self.search_indexer_client.get_indexer_status(indexer_name)
            print(json.dumps(status.as_dict(), indent=2))  # Dump full status object

            execution_status = status.last_result.status if status.last_result else "Unknown"
            print(f"Indexer status: {execution_status}")

            if execution_status in ["success", "partialSuccess"]:
                if status.last_result:
                    print(f"Items processed: {status.last_result.item_count}")
                    print(f"Items failed: {status.last_result.failed_item_count}")
                break

            elif execution_status in ["transientFailure", "persistentFailure"]:
                if status.last_result and status.last_result.errors:
                    print("Detailed errors:")
                    for error in status.last_result.errors:
                        print(json.dumps(error.as_dict(), indent=2))
                break

            else:
                print("Indexer is still running...")
                time.sleep(10)

    def get_indexer_status(self, indexer_name=None):
        """Get the current status of an indexer"""
        
        if not indexer_name:
            indexer_name = f"{self.index}-indexer"
        
        try:
            status = self.search_indexer_client.get_indexer_status(indexer_name)
            return {
                "name": indexer_name,
                "status": status.status,
                "last_result": {
                    "status": status.last_result.status if status.last_result else None,
                    "item_count": status.last_result.item_count if status.last_result else None,
                    "failed_item_count": status.last_result.failed_item_count if status.last_result else None,
                    "start_time": status.last_result.start_time if status.last_result else None,
                    "end_time": status.last_result.end_time if status.last_result else None,
                    "errors": [str(error) for error in status.last_result.errors] if status.last_result and status.last_result.errors else []
                }
            }
        except Exception as e:
            print(f"Error getting indexer status: {e}")
            return None

    def setup_complete_indexing_pipeline(self):
        """Set up the complete indexing pipeline"""
        
        print("Setting up complete indexing pipeline...")
        
        # Create the blob container first
        print("1. Creating blob container...")
        self.create_blob_container()
        
        # Create the search index
        print("2. Creating search index...")
        self.create_search_index()
        
        # Create blob data source
        print("3. Creating blob data source...")
        self.create_blob_data_source()
        
        # Create skillset
        print("4. Creating skillset...")
        self.create_skillset()
        
        # # Create indexer
        # print("5. Creating indexer...")
        # self.create_indexer()
        
        print("Indexing pipeline setup complete!")