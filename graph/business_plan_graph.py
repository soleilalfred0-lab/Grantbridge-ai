"""
Business Plan Generator - LangGraph Pipeline with Human-in-the-Loop
Two interrupt checkpoints:
  - Checkpoint 1: after market research (review market data + grants)
  - Checkpoint 2: after plan writing (review draft sections)
"""
from __future__ import annotations
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from graph.state import BusinessPlanState

logger = logging.getLogger(__name__)

from agents.intake_agent import intake_agent_node
from agents.grant_research_agent import grant_research_agent_node
from agents.market_research_agent import market_research_agent_node
from agents.plan_writer_agent import plan_writer_agent_node
from agents.financial_agent import financial_agent_node
from agents.compliance_agent import compliance_agent_node


def review_market_node(state: BusinessPlanState) -> dict:
    """
    CHECKPOINT 1 — pauses after market research.
    Returns market data + matched grants for user review.
    User can edit before plan writing begins.
    """
    logger.info("HITL Checkpoint 1: waiting for market review approval")
    human_input = interrupt({
        "checkpoint": 1,
        "message": "Please review the market research and matched grants before we write your plan.",
        "data": {
            "market_size":              state.get("market_size", ""),
            "competitor_overview":      state.get("competitor_overview", ""),
            "target_customer_analysis": state.get("target_customer_analysis", ""),
            "best_matching_grants":     state.get("best_matching_grants", []),
        }
    })
    # Apply any edits the user made
    updates = {}
    if isinstance(human_input, dict):
        for field in ["market_size", "competitor_overview", "target_customer_analysis"]:
            if human_input.get(field):
                updates[field] = human_input[field]
        if human_input.get("best_matching_grants"):
            updates["best_matching_grants"] = human_input["best_matching_grants"]
    updates["messages"] = [{"role": "human_review", "content": "Checkpoint 1 approved."}]
    return updates


def review_plan_node(state: BusinessPlanState) -> dict:
    """
    CHECKPOINT 2 — pauses after plan writing.
    Returns draft sections for user review.
    User can edit any section before financial projections run.
    """
    logger.info("HITL Checkpoint 2: waiting for plan draft review approval")
    human_input = interrupt({
        "checkpoint": 2,
        "message": "Your plan draft is ready. Review and edit any section before we finalize.",
        "data": {
            "executive_summary":  state.get("executive_summary", ""),
            "problem_statement":  state.get("problem_statement", ""),
            "solution":           state.get("solution", ""),
            "market_opportunity": state.get("market_opportunity", ""),
            "business_model":     state.get("business_model", ""),
            "marketing_strategy": state.get("marketing_strategy", ""),
            "operations_plan":    state.get("operations_plan", ""),
            "funding_request":    state.get("funding_request", ""),
        }
    })
    # Apply any edits the user made
    updates = {}
    if isinstance(human_input, dict):
        for field in ["executive_summary", "problem_statement", "solution",
                      "market_opportunity", "business_model", "marketing_strategy",
                      "operations_plan", "funding_request"]:
            if human_input.get(field):
                updates[field] = human_input[field]
    updates["messages"] = [{"role": "human_review", "content": "Checkpoint 2 approved."}]
    return updates


def route_by_plan_type(state: BusinessPlanState) -> str:
    plan_type = state.get("plan_type", "grant")
    if plan_type in ("simple", "bank"):
        return "market_research"
    return "grant_research"


def route_compliance(state: BusinessPlanState) -> str:
    plan_type = state.get("plan_type", "grant")
    if plan_type != "grant":
        return "__end__"
    score = state.get("compliance_score", 0.0)
    revision_count = state.get("revision_count", 0)
    if score < 0.75 and revision_count < 2:
        return "plan_writer"
    return "__end__"


# ── Shared checkpointer (in-memory, survives between API calls in same process)
checkpointer = MemorySaver()


def build_graph():
    graph = StateGraph(BusinessPlanState)

    graph.add_node("intake",          intake_agent_node)
    graph.add_node("grant_research",  grant_research_agent_node)
    graph.add_node("market_research", market_research_agent_node)
    graph.add_node("review_market",   review_market_node)
    graph.add_node("plan_writer",     plan_writer_agent_node)
    graph.add_node("review_plan",     review_plan_node)
    graph.add_node("financial",       financial_agent_node)
    graph.add_node("compliance",      compliance_agent_node)

    graph.set_entry_point("intake")

    graph.add_conditional_edges(
        "intake",
        route_by_plan_type,
        {"grant_research": "grant_research", "market_research": "market_research"},
    )

    graph.add_edge("grant_research",  "market_research")
    graph.add_edge("market_research", "review_market")   # → CHECKPOINT 1
    graph.add_edge("review_market",   "plan_writer")
    graph.add_edge("plan_writer",     "review_plan")     # → CHECKPOINT 2
    graph.add_edge("review_plan",     "financial")
    graph.add_edge("financial",       "compliance")

    graph.add_conditional_edges(
        "compliance",
        route_compliance,
        {"plan_writer": "plan_writer", "__end__": END},
    )

    return graph.compile(checkpointer=checkpointer)


# Compiled graph singleton
compiled_graph = build_graph()


def run_pipeline(intake_data: dict, thread_id: str = None) -> dict:
    """Start a new pipeline run. Returns state — may be interrupted at checkpoint."""
    import uuid
    if not thread_id:
        thread_id = str(uuid.uuid4())

    initial_state = {
        "business_name":            intake_data.get("business_name", ""),
        "startup_idea":             intake_data.get("startup_idea", ""),
        "industry":                 intake_data.get("industry", ""),
        "location":                 intake_data.get("location", "Suriname"),
        "target_customers":         intake_data.get("target_customers", ""),
        "financial_expectations":   intake_data.get("financial_expectations", ""),
        "founder_background":       intake_data.get("founder_background", ""),
        "plan_type":                intake_data.get("plan_type", "grant"),
        "language":                 intake_data.get("language", "English"),
        "available_grants":         [],
        "best_matching_grants":     [],
        "market_size":              "",
        "competitor_overview":      "",
        "target_customer_analysis": "",
        "swot_analysis":            {},
        "executive_summary":        "",
        "problem_statement":        "",
        "solution":                 "",
        "market_opportunity":       "",
        "business_model":           "",
        "marketing_strategy":       "",
        "operations_plan":          "",
        "funding_request":          "",
        "collateral":               "",
        "repayment_plan":           "",
        "credit_history":           "",
        "startup_costs":            {},
        "revenue_projections":      {},
        "break_even_analysis":      "",
        "financial_summary":        "",
        "compliance_score":         0.0,
        "compliance_issues":        [],
        "compliance_suggestions":   [],
        "revision_count":           0,
        "messages":                 [],
        "current_step":             "intake",
        "errors":                   [],
        "final_plan":               None,
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = compiled_graph.invoke(initial_state, config=config)
    result["_thread_id"] = thread_id
    return result


def resume_pipeline(thread_id: str, human_input: dict) -> dict:
    """Resume a paused pipeline after human review."""
    from langgraph.types import Command
    config = {"configurable": {"thread_id": thread_id}}
    result = compiled_graph.invoke(
        Command(resume=human_input),
        config=config,
    )
    result["_thread_id"] = thread_id
    return result
