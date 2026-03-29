"""Azure Search retriever with caching and prioritization."""

import functools
import logging
from langchain_community.vectorstores import AzureSearch
from typing import List, Optional, Tuple
from langchain.schema import Document
from azure.search.documents.models import VectorizedQuery

from config.settings import settings
from langchain_openai import AzureOpenAIEmbeddings

class CachedAzureSearch(AzureSearch):
    """Cached wrapper for Azure Search vector store."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store index_name from kwargs or get it from parent class
        self.index_name = kwargs.get(
            'index_name') or getattr(self, 'index_name', None)

    @functools.cached_property
    def _index_metadata(self):
        """Cached index metadata property."""
        return self.client.get_index(self.index_name)

    def similarity_search_by_vector(
        self,
        embedding: List[float],
        k: int = 4,
        score_threshold: Optional[float] = None,
        filters: Optional[str] = None
    ) -> List[Tuple[Document, float]]:
        """
        Search by precomputed embedding vector directly,
        avoiding re-embedding the query.
        """
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=k,
            fields="content_vector"
        )

        results = self.client.search(
            search_text="*",
            vector_queries=[vector_query],
            top=k,
            filter=filters,
            include_total_count=True
        )
        docs = []
        for result in results:
            score = result.get('@search.score', 0)
            if score_threshold is not None and score < score_threshold:
                continue
            metadata = {
                "category": result.get("category"),
                "source_name": result.get("source_name"),
                "source_path": result.get("source_path"),
                "created_at": result.get("created_at"),
                "title": result.get("title"),
            }
            doc = Document(page_content=result.get(
                'content', ''), metadata=metadata)
            docs.append((doc, score))
        return docs

class PrioritizedSearchManager:
    """Singleton manager for Azure Search instances."""
    _instances = {}

    def __init__(self, index_name: str):
        self.index_name = index_name
        self.embeddings = AzureOpenAIEmbeddings(
            deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            openai_api_version=settings.AZURE_OPENAI_API_VERSION
        )
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.search_key = settings.AZURE_SEARCH_KEY

    def get_vectorstore(self):
        """Get cached vector store instance."""
        # Singleton cache to avoid re-instantiation and metadata calls
        if self.index_name not in self._instances:
            self._instances[self.index_name] = CachedAzureSearch(
                azure_search_endpoint=self.search_endpoint,
                azure_search_key=self.search_key,
                index_name=self.index_name,
                embedding_function=self.embeddings.embed_query,
                vector_field_name="content_vector"
            )
        return self._instances[self.index_name]

class PrioritizedRetriever:
    """Retriever over the single AI index"""

    def __init__(
        self,
        index_id: str,
        k: int,
        min_score: float,
    ):
        self.k = k
        self.min_score = min_score
        manager = PrioritizedSearchManager(f"ai-index-{index_id}")
        self.store = manager.get_vectorstore()

    def get_relevant_documents(
        self,
        query: str,
        filter_expr: Optional[str] = None,
    ) -> List[Document]:
        try:
            query_embedding = self.store.embedding_function(query)
            docs = self._search_from_store(
                self.store, query_embedding, self.k, filter_expr
            )
            logging.info("Retrieved %s docs from AI index", len(docs))
            return docs
        except Exception as e:
            logging.warning("RAG search failed: %s", e)
            return []

    def _search_from_store(
        self,
        store,
        embedding: List[float],
        k: int,
        filters: Optional[str] = None
    ) -> List[Document]:
        try:
            scored_docs = store.similarity_search_by_vector(
                embedding=embedding,
                k=k * 4,
                score_threshold=self.min_score,
                filters=filters
            )
            return [doc for doc, _ in scored_docs][:k]
        except Exception as e:
            logging.warning(
                f"Search error in store with filter {filters}: {e}")
            return []

    def format_context_with_sources(self, docs: List[Document]) -> str:
        """Format context with clear source attribution using real file names"""
        if not docs:
            return "No relevant documents found in knowledge bases."

        context_parts = []
        context_parts.append("=== FROM KNOWLEDGE SOURCES ===")

        for i, doc in enumerate(docs, 1):
            source_name = doc.metadata.get("source_name", f"document_{i}")
            # print(f"\nSource {i} - {source_name}:\n{doc.page_content}\n")
            # context_parts.append(f"\nSource {i} - {source_name}:\n{doc.page_content}\n")
            context_parts.append(
                f"\nSource - {source_name}:\n{doc.page_content}\n")

        return "\n".join(context_parts)

    @staticmethod
    def build_ai_filter(branch_state: str = "", certifications: str = None) -> str:
        """Construct Azure Search filter from branchState and certification list.

        - State: allow null/empty and the provided branch_state (lowercased) if present
        - Certifications: exclude categories not present in provided certs among {tjc, chap, achc}
        """
        # Parse certifications (comma-separated string). Empty or None means none.
        provided_raw = []
        if certifications is not None:
            parts = [p.strip().strip('"\'') for p in certifications.split(
                ',')] if certifications.strip() else []
            provided_raw = [p for p in parts if p]

        branch_state = (branch_state or "").strip().lower()

        known_accreditations = {"tjc", "chap", "achc"}
        provided = {str(a).lower() for a in provided_raw if str(
            a).lower() in known_accreditations}
        categories_to_exclude = sorted(list(known_accreditations - provided))

        state_clauses = ["state eq null", "state eq ''", "state eq 'null'"]
        if branch_state:
            state_clauses.append(f"state eq '{branch_state}'")
        state_filter = f"({ ' or '.join(state_clauses) })"

        if categories_to_exclude:
            category_filter = " and ".join(
                [f"category ne '{c}'" for c in categories_to_exclude])
            return f"{state_filter} and {category_filter}"
        return state_filter
