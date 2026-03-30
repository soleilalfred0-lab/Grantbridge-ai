"""
Vector Store – Long-Term Memory
─────────────────────────────────
Provides persistent memory for the Business Plan Generator using
ChromaDB (default) or FAISS as a drop-in alternative.

Responsibilities:
  • Store completed business plans as embedded documents
  • Retrieve similar past plans to inform new plan generation (RAG)
  • Provide a consistent interface regardless of the backend chosen
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ── Backend selection ─────────────────────────────────────────────────────────
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "chroma").lower()   # "chroma" | "faiss"
CHROMA_PATH    = os.getenv("CHROMA_PERSIST_PATH", "./data/chroma_db")
FAISS_PATH     = os.getenv("FAISS_INDEX_PATH",    "./data/faiss_index")
COLLECTION_NAME = "business_plans"


# ── Lazy singletons ───────────────────────────────────────────────────────────
_chroma_collection = None
_faiss_store       = None


def _get_embeddings():
    """Return an OpenAI embedding model."""
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model="text-embedding-3-small")


def _get_chroma_collection():
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        _chroma_collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


def _get_faiss_store():
    global _faiss_store
    if _faiss_store is None:
        from langchain_community.vectorstores import FAISS

        embeddings = _get_embeddings()

        if os.path.exists(FAISS_PATH):
            _faiss_store = FAISS.load_local(
                FAISS_PATH, embeddings, allow_dangerous_deserialization=True
            )
        else:
            # Bootstrap with a dummy document so FAISS is initialised
            _faiss_store = FAISS.from_texts(
                ["Business Plan Generator initialised."],
                embedding=embeddings,
            )
    return _faiss_store


# ── Public API ────────────────────────────────────────────────────────────────

def store_business_plan(plan_state: dict[str, Any]) -> str:
    """
    Persist a completed business plan to the vector store.

    Parameters
    ----------
    plan_state : dict
        The full LangGraph state after pipeline completion.

    Returns
    -------
    str
        The unique document ID assigned to this plan.
    """
    doc_id = str(uuid.uuid4())
    plan_text = _state_to_text(plan_state)
    metadata = {
        "id":            doc_id,
        "business_name": plan_state.get("business_name", "Unknown"),
        "industry":      plan_state.get("industry", ""),
        "location":      plan_state.get("location", ""),
        "compliance":    str(plan_state.get("compliance_score", 0.0)),
    }

    try:
        if VECTOR_BACKEND == "faiss":
            _store_faiss(doc_id, plan_text, metadata)
        else:
            _store_chroma(doc_id, plan_text, metadata)
        logger.info("Stored business plan %s in %s", doc_id, VECTOR_BACKEND)
    except Exception as exc:
        logger.error("Vector store write error: %s", exc)

    return doc_id


def retrieve_similar_plans(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve the most semantically similar past business plans.

    Parameters
    ----------
    query : str
        The search query (e.g. startup idea description).
    top_k : int
        Number of results to return.

    Returns
    -------
    list[dict]
        List of ``{"text": ..., "metadata": ...}`` dicts.
    """
    try:
        if VECTOR_BACKEND == "faiss":
            return _retrieve_faiss(query, top_k)
        else:
            return _retrieve_chroma(query, top_k)
    except Exception as exc:
        logger.error("Vector store retrieval error: %s", exc)
        return []


# ── Backend helpers ───────────────────────────────────────────────────────────

def _store_chroma(doc_id: str, text: str, metadata: dict) -> None:
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = _get_embeddings()
    embedding_vector = embeddings_model.embed_query(text)

    col = _get_chroma_collection()
    col.upsert(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding_vector],
        metadatas=[metadata],
    )


def _retrieve_chroma(query: str, top_k: int) -> list[dict]:
    embeddings_model = _get_embeddings()
    query_vector = embeddings_model.embed_query(query)

    col = _get_chroma_collection()
    results = col.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas"],
    )

    output = []
    for doc, meta in zip(
        results.get("documents", [[]])[0],
        results.get("metadatas", [[]])[0],
    ):
        output.append({"text": doc, "metadata": meta})
    return output


def _store_faiss(doc_id: str, text: str, metadata: dict) -> None:
    store = _get_faiss_store()
    store.add_texts([text], metadatas=[{**metadata, "id": doc_id}])
    store.save_local(FAISS_PATH)


def _retrieve_faiss(query: str, top_k: int) -> list[dict]:
    store = _get_faiss_store()
    docs = store.similarity_search(query, k=top_k)
    return [{"text": d.page_content, "metadata": d.metadata} for d in docs]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _state_to_text(state: dict) -> str:
    """Flatten relevant state fields into a single text blob for embedding."""
    sections = [
        f"Business: {state.get('business_name', '')}",
        f"Industry: {state.get('industry', '')}",
        f"Location: {state.get('location', '')}",
        f"Idea: {state.get('startup_idea', '')}",
        f"Executive Summary: {state.get('executive_summary', '')}",
        f"Problem: {state.get('problem_statement', '')}",
        f"Solution: {state.get('solution', '')}",
        f"Market Opportunity: {state.get('market_opportunity', '')}",
        f"Business Model: {state.get('business_model', '')}",
        f"Financial Summary: {state.get('financial_summary', '')}",
    ]
    return "\n\n".join(s for s in sections if s.split(": ", 1)[-1].strip())
