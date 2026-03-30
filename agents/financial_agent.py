"""
Financial Projection Agent
───────────────────────────
Responsibility: Generate realistic financial projections calibrated to the
Suriname/CARICOM market context, including:
  • Startup cost breakdown
  • 3-year revenue projections
  • Break-even analysis
  • Key financial assumptions
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState
from tools.financial_tools import calculate_break_even, format_currency_srd

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

_SYSTEM_PROMPT = """You are a CFO-level financial modeller with expertise in
Caribbean SME finance, Suriname Dollar (SRD) economics, and development
bank reporting standards.

Given the business profile and plan, produce a structured JSON object:
{
  "startup_costs": {
    "equipment":       0,
    "working_capital": 0,
    "marketing":       0,
    "licenses_legal":  0,
    "technology":      0,
    "other":           0,
    "total_usd":       0,
    "total_srd":       0,
    "notes":           "Key assumptions"
  },
  "revenue_projections": {
    "year_1": {"revenue": 0, "expenses": 0, "net_profit": 0, "growth_rate": "0%"},
    "year_2": {"revenue": 0, "expenses": 0, "net_profit": 0, "growth_rate": "0%"},
    "year_3": {"revenue": 0, "expenses": 0, "net_profit": 0, "growth_rate": "0%"}
  },
  "break_even": {
    "monthly_fixed_costs": 0,
    "variable_cost_ratio": 0.0,
    "break_even_revenue_monthly": 0,
    "break_even_month": "Month X of Year Y"
  },
  "key_assumptions": ["Assumption 1", "Assumption 2"],
  "financial_summary": "2-paragraph narrative for grant application"
}

Use realistic SRD/USD exchange rate of approximately 36 SRD = 1 USD.
All monetary values should be in USD unless noted.
Return ONLY valid JSON (no markdown fences).
"""


def financial_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """LangGraph node for the Financial Projection Agent."""
    logger.info("Financial Agent: generating projections")

    context = {
        "business_name":          state.get("business_name", ""),
        "industry":               state.get("industry", ""),
        "startup_idea":           state.get("startup_idea", ""),
        "financial_expectations": state.get("financial_expectations", ""),
        "business_model":         state.get("business_model", ""),
        "market_size":            state.get("market_size", ""),
        "funding_request":        state.get("funding_request", ""),
        "best_grants":            [
            {"name": g.get("name"), "max_amount": g.get("max_amount_usd")}
            for g in state.get("best_matching_grants", [])
        ],
    }

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Business context:\n{json.dumps(context, indent=2)}\n\n"
            "Generate the financial projections JSON."
        )),
    ]

    response = _llm.invoke(messages)
    raw_text = response.content.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    try:
        financials: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Financial Agent: JSON parse error – %s", exc)
        financials = {
            "startup_costs":         {"total_usd": 0, "total_srd": 0, "notes": "Parse error"},
            "revenue_projections":   {},
            "break_even":            {},
            "key_assumptions":       [],
            "financial_summary":     "Financial projection failed. Please retry.",
        }

    # Use the financial tool to validate/recalculate break-even
    be_data = financials.get("break_even", {})
    if be_data.get("monthly_fixed_costs") and be_data.get("variable_cost_ratio") is not None:
        calc_be = calculate_break_even(
            fixed_costs=be_data.get("monthly_fixed_costs", 0),
            variable_cost_ratio=be_data.get("variable_cost_ratio", 0.3),
        )
        financials["break_even"]["break_even_revenue_monthly"] = calc_be

    return {
        "startup_costs":       financials.get("startup_costs", {}),
        "revenue_projections": financials.get("revenue_projections", {}),
        "break_even_analysis": (lambda b: (
            "Monthly Fixed Costs: " + str(b.get("monthly_fixed_costs", "N/A")) +
            chr(10) + "Break-Even Revenue (monthly): " + str(b.get("break_even_revenue_monthly", "N/A")) +
            chr(10) + "Projected Break-Even: " + str(b.get("break_even_month", "N/A"))
        ))(financials.get("break_even", {})),
        "financial_summary":   financials.get("financial_summary", ""),
        "current_step":        "compliance_check",
        "messages": [{
            "role":    "financial_agent",
            "content": "Financial projections generated.",
            "data":    financials,
        }],
    }
