"""
Grant Compliance Agent
───────────────────────
Responsibility: Audit the completed business plan against grant eligibility
criteria, score compliance, flag issues, and produce actionable improvement
suggestions. Drives the iterative revision loop.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

_SYSTEM_PROMPT = """You are a senior grant compliance auditor with expertise
in Caribbean Development Bank, IDB, and Suriname government grant programmes.

You will evaluate a business plan against grant requirements and return:
{
  "compliance_score": 0.85,
  "passed_criteria": ["Criterion 1 met", "Criterion 2 met"],
  "failed_criteria": ["Missing job creation targets", "No sustainability plan"],
  "issues": [
    "The financial projections do not include sensitivity analysis",
    "No mention of local hiring or gender equity targets"
  ],
  "suggestions": [
    "Add a section on projected job creation broken down by gender and age",
    "Include a risk mitigation matrix",
    "Quantify environmental sustainability commitments"
  ],
  "overall_assessment": "Brief narrative assessment for the reviewer"
}

Scoring guide (0.0 – 1.0):
  0.9+ → Ready to submit
  0.7–0.9 → Minor revisions needed
  0.5–0.7 → Moderate revisions needed
  <0.5  → Significant gaps; major revision required

Return ONLY valid JSON (no markdown fences).
"""


def compliance_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """LangGraph node for the Grant Compliance Agent."""
    logger.info("Compliance Agent: auditing business plan")

    full_plan = {
        "executive_summary":  state.get("executive_summary", ""),
        "problem_statement":  state.get("problem_statement", ""),
        "solution":           state.get("solution", ""),
        "market_opportunity": state.get("market_opportunity", ""),
        "business_model":     state.get("business_model", ""),
        "marketing_strategy": state.get("marketing_strategy", ""),
        "operations_plan":    state.get("operations_plan", ""),
        "funding_request":    state.get("funding_request", ""),
        "financial_summary":  state.get("financial_summary", ""),
        "startup_costs":      state.get("startup_costs", {}),
        "revenue_projections": state.get("revenue_projections", {}),
    }

    grants = state.get("best_matching_grants", [])
    eligibility_criteria = []
    for g in grants:
        eligibility_criteria.extend(g.get("eligibility_criteria", []))

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Business Plan:\n{json.dumps(full_plan, indent=2)}\n\n"
            f"Grant Eligibility Criteria to check against:\n"
            f"{json.dumps(list(set(eligibility_criteria)), indent=2)}\n\n"
            "Return the compliance audit JSON."
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
        audit: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Compliance Agent: JSON parse error – %s", exc)
        audit = {
            "compliance_score": 0.5,
            "issues":           ["Compliance audit failed to parse."],
            "suggestions":      ["Please rerun the compliance check."],
        }

    score = float(audit.get("compliance_score", 0.5))

    # Determine next step
    revision_count = state.get("revision_count", 0)
    if score >= 0.85 or revision_count >= 3:
        next_step = "assemble_plan"
    else:
        next_step = "revision"

        # Assemble final plan from sections
    section_keys = [
        "executive_summary", "problem_statement", "solution",
        "market_opportunity", "business_model", "marketing_strategy",
        "operations_plan", "funding_request", "financial_summary",
        "break_even_analysis", "collateral", "repayment_plan"
    ]
    parts = []
    for k in section_keys:
        v = state.get(k, "")
        if v:
            heading = "## " + k.replace("_", " ").title()
            parts.append(heading + chr(10) + chr(10) + v)
    final_plan = (chr(10) + chr(10) + "---" + chr(10) + chr(10)).join(parts)

    return {
        "final_plan":             final_plan,
        "compliance_score":       score,
        "compliance_issues":      audit.get("issues", []) + audit.get("failed_criteria", []),
        "compliance_suggestions": audit.get("suggestions", []),
        "revision_count":         revision_count + 1,
        "current_step":           next_step,
        "messages": [{
            "role":    "compliance_agent",
            "content": "Compliance check done. Score: " + str(round(score,2)),
        }],
    }
