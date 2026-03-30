"""
tools/retrieval_tool.py

LangGraph-compatible Vector Retrieval Tool.
Registered as a callable tool that any agent in the graph can invoke.
Uses FAISS semantic search over the Caribbean grant dataset.
"""

import os
import json
import logging
from typing import Optional
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./data/vector_index")
GRANTS_DATA_PATH  = os.getenv("GRANTS_DATA_PATH",  "./data/caribbean_grants.json")


@tool
def retrieve_grants(
    query: str,
    country: Optional[str] = None,
    sector: Optional[str] = None,
    top_k: int = 10,
) -> str:
    """
    Search the Caribbean grant database using semantic similarity.

    Use this tool when you need to find grants that match an entrepreneur's
    profile, industry, country, or funding needs. Returns a JSON string of
    the most relevant grants.

    Args:
        query:   Natural language description of what to search for.
                 e.g. "solar energy grants for small farmers in Suriname"
        country: Optional country filter (e.g. "Suriname", "Jamaica")
        sector:  Optional sector filter (e.g. "agritech", "climate", "SME")
        top_k:   Number of results to return (default 10, max 20)

    Returns:
        JSON string containing a list of matching grants with all fields.
    """
    try:
        store = _get_store()
        results = store.search(query=query, top_k=min(top_k, 20))

        # Apply optional filters
        if country:
            country_lower = country.lower()
            results = [
                g for g in results
                if not g.get("country_eligibility")
                or any(
                    country_lower in c.lower() or c.lower() in ("all", "caricom")
                    for c in g.get("country_eligibility", [])
                )
            ]

        if sector:
            sector_lower = sector.lower()
            results = [
                g for g in results
                if any(sector_lower in s.lower() for s in g.get("sector", []))
                or sector_lower in g.get("description", "").lower()
            ]

        logger.info(f"retrieve_grants: query='{query}' → {len(results)} results")
        return json.dumps(results, indent=2)

    except Exception as e:
        logger.error(f"retrieve_grants error: {e}")
        return json.dumps({"error": str(e), "grants": []})


# ── Store singleton ────────────────────────────────────────────────────────────

_store_instance = None

def _get_store():
    global _store_instance
    if _store_instance is None:
        _store_instance = _GrantVectorStore()
    return _store_instance


class _GrantVectorStore:
    """
    Internal FAISS store. Loads from disk if index exists,
    otherwise builds it from the JSON dataset.
    """

    def __init__(self):
        self.grants: list[dict] = []
        self.index = None
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self._load()

    def _load(self):
        try:
            import faiss
            import numpy as np

            index_path = os.path.join(VECTOR_STORE_PATH, "grants.index")
            meta_path  = os.path.join(VECTOR_STORE_PATH, "grants_meta.json")

            if os.path.exists(index_path) and os.path.exists(meta_path):
                self.index = faiss.read_index(index_path)
                with open(meta_path) as f:
                    self.grants = json.load(f)
                logger.info(f"Loaded FAISS index: {len(self.grants)} grants")
            else:
                self._build()

        except ImportError:
            logger.warning("FAISS not installed — using keyword fallback")
            self._load_json()

    def _load_json(self):
        if os.path.exists(GRANTS_DATA_PATH):
            with open(GRANTS_DATA_PATH) as f:
                self.grants = json.load(f)

    def _build(self):
        import faiss
        import numpy as np

        self._load_json()
        if not self.grants:
            logger.error("No grants found — cannot build index")
            return

        os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
        logger.info(f"Building FAISS index for {len(self.grants)} grants...")

        texts = [self._to_text(g) for g in self.grants]
        vecs  = self.embeddings.embed_documents(texts)

        dim        = len(vecs[0])
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(vecs, dtype=np.float32))

        faiss.write_index(self.index, os.path.join(VECTOR_STORE_PATH, "grants.index"))
        with open(os.path.join(VECTOR_STORE_PATH, "grants_meta.json"), "w") as f:
            json.dump(self.grants, f)

        logger.info("FAISS index built and saved.")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if self.index is None:
            return self._keyword_search(query, top_k)

        import numpy as np
        vec       = self.embeddings.embed_query(query)
        distances, indices = self.index.search(
            np.array([vec], dtype=np.float32), top_k
        )
        return [self.grants[i] for i in indices[0] if 0 <= i < len(self.grants)]

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        words  = query.lower().split()
        scored = []
        for g in self.grants:
            text  = self._to_text(g).lower()
            score = sum(1 for w in words if w in text)
            if score:
                scored.append((score, g))
        scored.sort(reverse=True)
        return [g for _, g in scored[:top_k]]

    def _to_text(self, g: dict) -> str:
        return " ".join(filter(None, [
            g.get("grant_name", ""),
            g.get("organization", ""),
            g.get("description", ""),
            " ".join(g.get("sector", [])),
            " ".join(g.get("country_eligibility", [])),
            " ".join(g.get("eligibility_requirements", [])),
        ]))
