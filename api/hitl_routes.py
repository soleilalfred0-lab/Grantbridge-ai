"""
HITL API routes — endpoints for human review checkpoints.
Imported into api/app.py.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import uuid

hitl_router = APIRouter()


class StartRequest(BaseModel):
    business_name:          str
    startup_idea:           str
    industry:               str
    location:               str = "Suriname"
    target_customers:       str
    financial_expectations: str
    founder_background:     str = ""
    plan_type:              str = "grant"
    language:               str = "English"


class ResumeRequest(BaseModel):
    thread_id:   str
    checkpoint:  int
    approved:    bool = True
    edits:       Optional[dict] = None


def _is_interrupted(result: dict) -> bool:
    """Check if the graph paused at an interrupt checkpoint."""
    # LangGraph sets __interrupt__ when interrupted
    return "__interrupt__" in result or result.get("_interrupted", False)


def _get_interrupt_data(result: dict) -> dict:
    """Extract the interrupt payload from the result."""
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        return interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
    return {}


@hitl_router.post("/generate/start")
def start_pipeline(request: StartRequest):
    """
    Start the pipeline. May return a checkpoint for human review
    instead of the final plan.
    """
    from graph.business_plan_graph import run_pipeline
    import time

    thread_id = str(uuid.uuid4())
    start = time.time()

    try:
        result = run_pipeline(request.model_dump(), thread_id=thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = round(time.time() - start, 2)

    if _is_interrupted(result):
        interrupt_data = _get_interrupt_data(result)
        return {
            "status":       "checkpoint",
            "thread_id":    thread_id,
            "checkpoint":   interrupt_data.get("checkpoint", 1),
            "message":      interrupt_data.get("message", "Please review before continuing."),
            "review_data":  interrupt_data.get("data", {}),
            "elapsed":      elapsed,
        }

    # Completed without interruption (e.g. if HITL disabled)
    return {
        "status":                   "complete",
        "thread_id":                thread_id,
        "success":                  True,
        "business_name":            result.get("business_name", ""),
        "compliance_score":         result.get("compliance_score", 0.0),
        "revision_count":           result.get("revision_count", 0),
        "final_plan":               result.get("final_plan", ""),
        "grants_matched":           result.get("best_matching_grants", []),
        "processing_time_seconds":  elapsed,
        "message":                  "Plan generated successfully.",
    }


@hitl_router.post("/generate/resume")
def resume_pipeline_endpoint(request: ResumeRequest):
    """
    Resume the pipeline after human review.
    Send approved=True to continue, or include edits dict to apply changes.
    """
    from graph.business_plan_graph import resume_pipeline
    import time

    human_input = request.edits or {}
    start = time.time()

    try:
        result = resume_pipeline(
            thread_id=request.thread_id,
            human_input=human_input,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = round(time.time() - start, 2)

    # Check if we hit another checkpoint
    if _is_interrupted(result):
        interrupt_data = _get_interrupt_data(result)
        return {
            "status":      "checkpoint",
            "thread_id":   request.thread_id,
            "checkpoint":  interrupt_data.get("checkpoint", 2),
            "message":     interrupt_data.get("message", "Please review before continuing."),
            "review_data": {k: v for k, v in interrupt_data.items() if k not in ("checkpoint", "message")},
            "elapsed":     elapsed,
        }

    # Pipeline complete
    return {
        "status":                   "complete",
        "thread_id":                request.thread_id,
        "success":                  True,
        "business_name":            result.get("business_name", ""),
        "compliance_score":         result.get("compliance_score", 0.0),
        "revision_count":           result.get("revision_count", 0),
        "final_plan":               result.get("final_plan", ""),
        "grants_matched":           result.get("best_matching_grants", []),
        "processing_time_seconds":  elapsed,
        "message":                  "Plan generated successfully.",
    }
