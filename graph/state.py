"""
LangGraph State Schema for the Business Plan Generator.
This TypedDict defines the shared state passed between all agents.
"""

from typing import TypedDict, Annotated, List, Optional
import operator


class BusinessPlanState(TypedDict):
    """
    Shared state object that flows through the entire LangGraph pipeline.
    Each agent reads from and writes to this state.
    """

    # ── User intake data ──────────────────────────────────────────────────────
    business_name: str
    startup_idea: str
    industry: str
    location: str
    target_customers: str
    financial_expectations: str
    founder_background: str

    # ── Plan configuration ────────────────────────────────────────────────────
    plan_type: str                 # "simple" | "bank" | "grant"
    language: str                  # "English" | "Dutch" | "Spanish" | "Portuguese" | "French"

    # ── Grant research output ─────────────────────────────────────────────────
    available_grants: List[dict]
    best_matching_grants: List[dict]

    # ── Market research output ────────────────────────────────────────────────
    market_size: str
    competitor_overview: str
    target_customer_analysis: str
    swot_analysis: dict

    # ── Business plan sections ────────────────────────────────────────────────
    executive_summary: str
    problem_statement: str
    solution: str
    market_opportunity: str
    business_model: str
    marketing_strategy: str
    operations_plan: str
    funding_request: str

    # ── Bank-specific sections ────────────────────────────────────────────────
    collateral: str
    repayment_plan: str
    credit_history: str

    # ── Financial projections ─────────────────────────────────────────────────
    startup_costs: dict
    revenue_projections: dict
    break_even_analysis: str
    financial_summary: str

    # ── Compliance & revision (grant only) ────────────────────────────────────
    compliance_score: float
    compliance_issues: List[str]
    compliance_suggestions: List[str]
    revision_count: int

    # ── Pipeline control ──────────────────────────────────────────────────────
    messages: Annotated[List[dict], operator.add]
    current_step: str
    errors: Annotated[List[str], operator.add]
    final_plan: Optional[str]
