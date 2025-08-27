from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
from io import BytesIO
import logging
from dataclasses import dataclass
from enum import Enum

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from config.settings import settings
from langchain.schema import Document

# Azure services
from app.adapters.azure_search import get_global_search_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    UNKNOWN = "unknown"

@dataclass
class ProcessingResult:
    """Result of document processing"""
    success: bool
    message: str
    chunks_created: int = 0
    chunks_failed: int = 0
    total_chunks: int = 0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class DocumentProcessor:
    """Main document processing class using LangChain"""
    
    def __init__(self, 
                 embedding_deployment: str = None,
                 chunk_size: int = 500,
                 chunk_overlap: int = 100):
        
        # Initialize Azure clients
        self.main_search_client = get_global_search_client()
        
        # Create embedding model
        deployment_name = embedding_deployment or settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
        self.embeddings = AzureOpenAIEmbeddings(
            deployment=deployment_name,
            model=deployment_name,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            openai_api_version=settings.AZURE_OPENAI_API_VERSION,
            chunk_size=200, # batch size
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _get_file_type(self, filename: str) -> FileType:
        """Determine file type from filename"""
        extension = filename.lower().split('.')[-1]
        try:
            return FileType(extension)
        except ValueError:
            return FileType.UNKNOWN
    
    def _load_document_from_bytes(self, filename: str, data: bytes) -> List[Document]:
        """Load document from bytes using appropriate loader"""
        file_type = self._get_file_type(filename)
        
        try:
            if file_type == FileType.PDF:
                return self._load_pdf_from_bytes(data, filename)
            elif file_type in [FileType.DOCX, FileType.DOC]:
                return self._load_docx_from_bytes(data, filename)
            elif file_type == FileType.TXT:
                return self._load_txt_from_bytes(data, filename)
            else:
                # Try to decode as text
                return self._load_txt_from_bytes(data, filename)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return []
    
    def _load_pdf_from_bytes(self, data: bytes, filename: str) -> List[Document]:
        """Load PDF from bytes"""
        try:
            import PyPDF2
            pdf_file = BytesIO(data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            documents = []
            for _, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    doc = Document(
                        page_content=page_text,
                        metadata={
                            "doc_id": str(uuid.uuid4()),
                            "filename": filename,
                            "file_type": FileType.PDF.value,
                        }
                    )
                    documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return []
    
    def _load_docx_from_bytes(self, data: bytes, filename: str) -> List[Document]:
        """Load DOCX from bytes"""
        try:
            import docx
            doc_file = BytesIO(data)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            return [Document(
                page_content=text,
                metadata={
                    "doc_id": str(uuid.uuid4()),
                    "filename": filename,
                    "file_type": FileType.DOCX.value,
                }
            )]
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return []
    
    def _load_txt_from_bytes(self, data: bytes, filename: str) -> List[Document]:
        """Load text from bytes"""
        try:
            text = data.decode('utf-8')
            return [Document(
                page_content=text,
                metadata={
                    "doc_id": str(uuid.uuid4()),
                    "filename": filename,
                    "file_type": FileType.TXT.value,
                }
            )]
        except Exception as e:
            logger.error(f"Error decoding text: {e}")
            return []
    
    def _prepare_documents_for_search(self, documents: List[Document], provider_id: str) -> List[Dict[str, Any]]:
        """Prepare documents for Azure Search index"""
        search_docs = []
        
        # Extract text content for batch embedding
        texts = [doc.page_content for doc in documents]
        
        try:
            # Generate embeddings in batch for efficiency
            embeddings = self.embeddings.embed_documents(texts)
            
            for _, (doc, embedding) in enumerate(zip(documents, embeddings)):
                search_doc = {
                    "id": str(uuid.uuid4()),
                    "parent_id": doc.metadata.get("doc_id"),
                    "is_general": False,
                    "provider_id": provider_id,
                    "filename": doc.metadata.get("filename"),
                    "storage_url": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "title": None,
                    "content": doc.page_content,
                    "content_vector": embedding,
                }
                search_docs.append(search_doc)
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
        
        return search_docs
    
    def process_document(self, provider_id: str, filename: str, data: bytes) -> ProcessingResult:
        """Process a document through the complete pipeline"""
        logger.info(f"Processing document: {filename} for user: {provider_id}")
        
        try:
            # Step 1: Load document
            documents = self._load_document_from_bytes(filename, data)
            if not documents:
                return ProcessingResult(
                    success=False,
                    message="No content could be extracted from the file",
                    error="Failed to load document"
                )
            
            logger.info(f"Loaded {len(documents)} document(s)")
            
            # Step 2: Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Created {len(chunks)} chunks")
            
            if not chunks:
                return ProcessingResult(
                    success=False,
                    message="No chunks could be created from the document",
                    error="Failed to create chunks"
                )
            
            # Step 3: Prepare for search index
            search_docs = self._prepare_documents_for_search(chunks, provider_id)
            
            if not search_docs:
                return ProcessingResult(
                    success=False,
                    message="Failed to generate embeddings for chunks",
                    error="Embedding generation failed",
                    total_chunks=len(chunks)
                )
            
            # Step 4: Upload to search index
            try:
                self.main_search_client.upload_documents(search_docs)
                logger.info("Successfully uploaded to search index")
                
                return ProcessingResult(
                    success=True,
                    message=f"Successfully processed {filename}",
                    chunks_created=len(search_docs),
                    chunks_failed=len(chunks) - len(search_docs),
                    total_chunks=len(chunks),
                    metadata=documents[0].metadata if documents else {}
                )
                
            except Exception as e:
                logger.error(f"Failed to upload to search index: {e}")
                return ProcessingResult(
                    success=False,
                    message="Failed to upload to search index",
                    error=str(e),
                    total_chunks=len(chunks)
                )
                
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return ProcessingResult(
                success=False,
                message="Failed to process document",
                error=str(e)
            )

class DocumentManager:
    """High-level document management class"""
    
    def __init__(self, processor: DocumentProcessor):
        self.processor = processor
    
    def upload_and_process(self, provider_id: str, filename: str, data: bytes) -> Dict[str, Any]:
        """Upload file to blob storage and process it"""
        blob_name = f"{provider_id}/{filename}"
        
        try:
            
            # Process the document
            processing_result = self.processor.process_document(provider_id, filename, data)
            
            return {
                "blob_name": blob_name,
                "processing_result": processing_result.__dict__,
                "success": processing_result.success
            }
            
        except Exception as e:
            logger.error(f"Error uploading and processing: {e}")
            return {
                "blob_name": blob_name,
                "processing_result": {"error": str(e)},
                "success": False
            }
    
    def batch_process(self, provider_id: str, files: List[tuple]) -> Dict[str, Any]:
        """Process multiple files in batch"""
        results = []
        total_success = 0
        total_failed = 0
        
        for filename, data in files:
            try:
                result = self.upload_and_process(provider_id, filename, data)
                results.append({"filename": filename, "result": result})
                
                if result["success"]:
                    total_success += 1
                else:
                    total_failed += 1
                    
            except Exception as e:
                results.append({
                    "filename": filename, 
                    "result": {"error": str(e), "success": False}
                })
                total_failed += 1
        
        return {
            "total_processed": len(files),
            "successful": total_success,
            "failed": total_failed,
            "results": results
        }
    
    def delete_provider_documents(self, provider_id: str) -> Dict[str, Any]:
        """Delete all documents for a user"""
        try:
            results = self.processor.main_search_client.search(
                search_text="*",
                filter=f"provider_id eq '{provider_id}'",
                select=["id"]
            )
            
            doc_ids = [{"id": result["id"]} for result in results]
            if doc_ids:
                self.processor.main_search_client.delete_documents(doc_ids)
                logger.info(f"Deleted {len(doc_ids)} documents for user {provider_id}")
                return {"deleted_count": len(doc_ids), "success": True}
            else:
                return {"deleted_count": 0, "success": True, "message": "No documents found"}
                
        except Exception as e:
            logger.error(f"Error deleting user documents: {e}")
            return {"error": str(e), "success": False}