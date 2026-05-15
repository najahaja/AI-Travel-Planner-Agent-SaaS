"""
RAG Pipeline — ChromaDB + Sentence Transformers
================================================
Manages the travel knowledge base vector store.
"""
import os
import warnings

# Suppress ChromaDB telemetry BEFORE importing chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
warnings.filterwarnings("ignore", message=".*telemetry.*")

# Brute-force monkeypatch to silence the "capture() takes 1 positional argument" error
# which occurs due to version mismatch between ChromaDB 0.5.0 and newer PostHog versions.

try:
    # pyrefly: ignore [missing-import]
    import posthog
    def no_op_capture(*args, **kwargs):
        pass
    posthog.capture = no_op_capture
    
    # pyrefly: ignore [missing-import, missing-import-error]
    import chromadb.telemetry.product.posthog
    if hasattr(chromadb.telemetry.product.posthog, "Posthog"):
        chromadb.telemetry.product.posthog.Posthog._direct_capture = no_op_capture
except ImportError:
    pass
except Exception:
    pass

from typing import List, Optional
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
from app.core.config import settings

# Lazy-loaded singletons
_chroma_client = None
_collection = None
_embedding_fn = None


def _get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        # pyrefly: ignore [missing-import, missing-import-error]
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
    return _embedding_fn


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        # pyrefly: ignore [missing-import, missing-import-error]
        import chromadb
        # pyrefly: ignore [missing-import]
        from chromadb.config import Settings
        
        # Initialize client with explicit telemetry disabled to avoid library conflicts
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        _collection = _chroma_client.get_or_create_collection(
            name="travel_knowledge",
            embedding_function=_get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"[RAG] ChromaDB collection loaded: {_collection.count()} documents")
    return _collection


async def retrieve_travel_info(query: str, n_results: int = 4) -> str:
    """
    Retrieve relevant travel knowledge for the given query.
    Returns formatted context string for the LLM.
    """
    try:
        collection = _get_collection()
        count = collection.count()

        if count == 0:
            logger.debug("RAG collection is empty, skipping retrieval")
            return ""

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count),
            include=["documents", "metadatas"],
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        context_parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            source = meta.get("source", "Travel Knowledge Base")
            title = meta.get("title", "")
            context_parts.append(f"[{title} — {source}]\n{doc}")

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.warning(f"RAG retrieval error: {e}")
        return ""


async def add_documents(
    texts: List[str],
    metadatas: List[dict],
    ids: Optional[List[str]] = None,
) -> int:
    """Add documents to the vector store."""
    collection = _get_collection()

    if ids is None:
        import uuid
        ids = [str(uuid.uuid4()) for _ in texts]

    collection.upsert(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
    )
    logger.info(f"[RAG] Added {len(texts)} documents to RAG store")
    return len(texts)


async def delete_document(doc_id: str) -> bool:
    """Delete a document from the vector store."""
    try:
        collection = _get_collection()
        collection.delete(ids=[doc_id])
        return True
    except Exception as e:
        logger.error(f"RAG delete error: {e}")
        return False


def get_collection_stats() -> dict:
    """Return stats about the RAG collection."""
    try:
        collection = _get_collection()
        return {"total_documents": collection.count(), "collection_name": collection.name}
    except Exception as e:
        return {"error": str(e)}
