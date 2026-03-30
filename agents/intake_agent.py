"""
User Intake Agent
─────────────────
Responsibility: Collect all structured information about the entrepreneur's
business idea before any research or writing begins.

In a real deployment this agent runs as a conversational loop; here it is
wired as a LangGraph node that processes whatever intake data has already
been placed on the state (e.g. from an API request body) and enriches it
with follow-up completions via the LLM.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState

logger = logging.getLogger(__name__)

# ── LLM ───────────────────────────────────────────────────────────────────────
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert business consultant specialising in
Suriname and CARICOM startup ecosystems. Your job is to analyse the
entrepreneur's raw inputs and produce a structured, enriched intake summary.

Given the raw intake data, you will:
1. Identify any missing critical fields and make reasonable inferences.
2. Classify the industry using standard ISIC codes.
3. Summarise the startup idea in one crisp paragraph.
4. Output a JSON object with these keys:
   business_name, startup_idea_summary, industry, industry_code,
   location, target_customers, financial_expectations, founder_background,
   key_value_proposition
"""


def intake_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """
    LangGraph node for the User Intake Agent.

    Reads raw user-supplied fields from *state*, calls the LLM to enrich
    and validate them, then returns updated state fields.
    """
    logger.info("Intake Agent: processing user inputs")

    raw_data = {
        "business_name":         state.get("business_name", ""),
        "startup_idea":          state.get("startup_idea", ""),
        "industry":              state.get("industry", ""),
        "location":              state.get("location", ""),
        "target_customers":      state.get("target_customers", ""),
        "financial_expectations": state.get("financial_expectations", ""),
        "founder_background":    state.get("founder_background", ""),
    }

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=(
            "Here is the raw intake data from the entrepreneur:\n\n"
            f"{json.dumps(raw_data, indent=2)}\n\n"
            "Return ONLY a valid JSON object (no markdown fences)."
        )),
    ]

    response = _llm.invoke(messages)
    raw_text = response.content.strip()

    # Strip optional markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    try:
        enriched: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Intake Agent: JSON parse error – %s", exc)
        enriched = raw_data  # fall back to raw inputs

    return {
        "business_name":         enriched.get("business_name", raw_data["business_name"]),
        "startup_idea":          enriched.get("startup_idea_summary", raw_data["startup_idea"]),
        "industry":              enriched.get("industry", raw_data["industry"]),
        "location":              enriched.get("location", raw_data["location"]),
        "target_customers":      enriched.get("target_customers", raw_data["target_customers"]),
        "financial_expectations": enriched.get("financial_expectations", raw_data["financial_expectations"]),
        "founder_background":    enriched.get("founder_background", raw_data["founder_background"]),
        "current_step":          "grant_research",
        "messages": [{
            "role":    "system",
            "content": "Intake complete",
            "data":    enriched,
        }],
    }
