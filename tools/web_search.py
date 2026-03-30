"""
Web Search Tool
────────────────
Provides a web search capability for agents that need live data.

In production, swap the backend to Tavily, SerpAPI, or Brave Search.
This module provides a clean interface so the backend can be swapped
without changing agent code.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Search the web and return structured results.

    Parameters
    ----------
    query : str
        Search query string.
    max_results : int
        Maximum number of results to return.

    Returns
    -------
    list[dict]
        List of ``{"title": ..., "url": ..., "snippet": ...}`` dicts.
    """
    # ── Tavily (recommended for production) ───────────────────────────────────
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        return _tavily_search(query, max_results, tavily_key)

    # ── SerpAPI fallback ──────────────────────────────────────────────────────
    serp_key = os.getenv("SERPAPI_API_KEY")
    if serp_key:
        return _serpapi_search(query, max_results, serp_key)

    # ── Offline stub for development / testing ────────────────────────────────
    logger.warning(
        "No search API key found (TAVILY_API_KEY / SERPAPI_API_KEY). "
        "Returning stub results."
    )
    return _stub_results(query)


# ── Backend implementations ───────────────────────────────────────────────────

def _tavily_search(query: str, max_results: int, api_key: str) -> list[dict]:
    try:
        from tavily import TavilyClient  # pip install tavily-python
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
    except Exception as exc:
        logger.error("Tavily search error: %s", exc)
        return _stub_results(query)


def _serpapi_search(query: str, max_results: int, api_key: str) -> list[dict]:
    try:
        import requests
        params = {
            "q":       query,
            "api_key": api_key,
            "num":     max_results,
            "engine":  "google",
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in data.get("organic_results", [])[:max_results]
        ]
    except Exception as exc:
        logger.error("SerpAPI search error: %s", exc)
        return _stub_results(query)


def _stub_results(query: str) -> list[dict]:
    """Return placeholder results when no search API is configured."""
    return [
        {
            "title":   f"[Stub] Search result for: {query}",
            "url":     "https://example.com",
            "snippet": (
                "This is a stub result. Configure TAVILY_API_KEY or "
                "SERPAPI_API_KEY in your .env file for live search results."
            ),
        }
    ]
