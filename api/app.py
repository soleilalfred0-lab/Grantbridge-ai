"""
Business Plan Generator – FastAPI Interface
─────────────────────────────────────────────
Endpoints:
  POST /generate          Run full pipeline synchronously
  POST /generate/stream   Stream pipeline events (SSE)
  GET  /health            Health check
  GET  /grants            List available grants by industry/location
  GET  /similar-plans     Retrieve similar plans from vector store
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from graph.business_plan_graph import run_pipeline, build_graph
from tools.grant_lookup import lookup_grants
from memory.vector_store import retrieve_similar_plans
from agents.grant_search_agent import search_grants
from api.hitl_routes import hitl_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Suriname Business Plan Generator",
    description=(
        "AI-powered grant-ready business plan generator for entrepreneurs "
        "in Suriname and CARICOM countries. Built with LangGraph."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(hitl_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class IntakeRequest(BaseModel):
    business_name:          str = Field(...,  example="AgroTech Suriname")
    startup_idea:           str = Field(...,  example="Mobile platform connecting Surinamese farmers to buyers")
    industry:               str = Field(...,  example="agritech")
    location:               str = Field("Paramaribo, Suriname", example="Paramaribo, Suriname")
    target_customers:       str = Field(...,  example="Small-scale farmers and urban consumers")
    financial_expectations: str = Field(...,  example="Seeking USD 50,000 in grant funding")
    founder_background:     str = Field("",   example="5 years in agriculture and 3 in software development")
    plan_type:              str = Field("grant",   example="grant")   # "simple" | "bank" | "grant"
    language:               str = Field("English", example="English") # "English" | "Dutch" | "Spanish" | "Portuguese" | "French"

    class Config:
        json_schema_extra = {
            "example": {
                "business_name":          "AgroTech Suriname",
                "startup_idea":           "A mobile app connecting small Surinamese farmers to urban buyers, reducing food waste and increasing farmer income by 30%.",
                "industry":               "agritech",
                "location":               "Paramaribo, Suriname",
                "target_customers":       "500+ small-scale farmers in the interior and 50,000 urban consumers in Paramaribo",
                "financial_expectations": "Seeking USD 50,000 grant to fund app development and farmer onboarding",
                "founder_background":     "Agricultural engineer with 5 years field experience and mobile app development background",
            }
        }


class PlanResponse(BaseModel):
    success:          bool
    business_name:    str
    compliance_score: float
    revision_count:   int
    final_plan:       Optional[str]
    grants_matched:   list
    processing_time_seconds: float
    message:          str


class HealthResponse(BaseModel):
    status:  str
    version: str
    model:   str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Returns service health status."""
    return {
        "status":  "healthy",
        "version": "1.0.0",
        "model":   os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


@app.post("/generate", response_model=PlanResponse, tags=["Business Plan"])
def generate_business_plan(request: IntakeRequest):
    """
    Generate a complete, grant-ready business plan.

    This runs the full LangGraph pipeline synchronously and returns the
    assembled Markdown plan along with compliance metadata.

    ⚠️  This endpoint may take 60–120 seconds for a full pipeline run.
    For production use, prefer `/generate/async` with a job ID.
    """
    logger.info("Generating plan for: %s", request.business_name)
    start = time.time()

    try:
        final_state = run_pipeline(request.model_dump())
    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    elapsed = round(time.time() - start, 2)

    return PlanResponse(
        success=True,
        business_name=final_state.get("business_name", ""),
        compliance_score=final_state.get("compliance_score", 0.0),
        revision_count=final_state.get("revision_count", 0),
        final_plan=final_state.get("final_plan", ""),
        grants_matched=final_state.get("best_matching_grants", []),
        processing_time_seconds=elapsed,
        message="Business plan generated successfully.",
    )


@app.get("/grants", tags=["Grants"])
def list_grants(
    industry: str = Query(...,   example="agritech"),
    location: str = Query("Suriname", example="Suriname"),
    funding:  str = Query("",    example="50000"),
):
    """
    Look up available grants filtered by industry and location.
    Returns ranked list of matching programmes.
    """
    grants = lookup_grants(
        industry=industry,
        location=location,
        funding_needed=funding,
    )
    return {
        "count":  len(grants),
        "grants": grants,
    }


@app.get("/similar-plans", tags=["Memory"])
def get_similar_plans(
    query: str = Query(..., example="agritech mobile app Suriname farmers"),
    top_k: int = Query(3,   ge=1, le=10),
):
    """
    Retrieve semantically similar past business plans from the vector store.
    Useful for benchmarking or improving a new plan via RAG.
    """
    try:
        results = retrieve_similar_plans(query=query, top_k=top_k)
    except Exception as exc:
        logger.error("Vector store retrieval error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "query":   query,
        "results": results,
    }


@app.get("/", tags=["System"])
def root():
    """API root – returns service info."""
    return {
        "service":     "Suriname Business Plan Generator",
        "version":     "1.0.0",
        "description": "AI-powered grant-ready business plan generator for Caribbean entrepreneurs.",
        "docs":        "/docs",
        "health":      "/health",
    }


# ── Serve the frontend UI ─────────────────────────────────────────────────────


@app.get("/api/convert")
def convert_currency_endpoint(
    amount: float = 0,
    country: str = "Suriname",
):
    """Convert a USD amount to local Caribbean currency."""
    from tools.currency_tool import convert_currency, _get_currency_code, _get_rate, CURRENCY_SYMBOLS, format_amount
    code = _get_currency_code(country)
    rate = _get_rate(code)
    local = amount * rate
    symbol = CURRENCY_SYMBOLS.get(code, code)
    return {
        "usd_amount": amount,
        "local_amount": round(local, 2),
        "currency_code": code,
        "currency_symbol": symbol,
        "exchange_rate": rate,
        "country": country,
        "formatted": format_amount(amount, country),
    }

import pathlib
_frontend_path = pathlib.Path(__file__).parent.parent / "frontend"
if _frontend_path.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/ui", StaticFiles(directory=str(_frontend_path), html=True), name="frontend")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development",
        workers=int(os.getenv("WORKERS", 1)),
    )


@app.get("/api/grants")
async def browse_grants(
    country:  str = "Suriname",
    sector:   str = "",
    query:    str = "",
    language: str = "en"
):
    results = await search_grants(
        country=country,
        sector=sector,
        query=query,
        language=language
    )
    return {"grants": results}

@app.get("/api/proposals/download/{filename}")
async def download_proposal(filename: str):
    """Download a saved proposal .md file."""
    import pathlib
    from fastapi.responses import FileResponse
    proposals_dir = pathlib.Path(__file__).parent.parent / "data" / "proposals"
    safe_name = pathlib.Path(filename).name
    filepath = proposals_dir / safe_name
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Proposal file not found")
    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type="text/markdown",
    )


@app.post("/api/proposal")
async def generate_proposal_endpoint(request: IntakeRequest):
    """Generate and save a grant proposal draft using the file writer tool."""
    from tools.file_writer_tool import write_proposal_file
    from agents.proposal_agent import ProposalAgent
    import json

    try:
        agent = ProposalAgent()
        proposal_text = agent.run(
            grant_name="Best Matching Grant",
            grant_description="Caribbean development funding program",
            profile=request.model_dump(),
            language=request.language,
        )

        raw = write_proposal_file.invoke({
            "proposal_text": proposal_text,
            "business_name": request.business_name,
            "grant_name":    "Best Matching Grant",
            "language":      request.language,
        })

        file_info = json.loads(raw) if isinstance(raw, str) else raw
        return {"status": "success", "proposal": proposal_text, "proposal_file": file_info}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
