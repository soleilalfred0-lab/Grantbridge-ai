"""
Business Plan Writer Agent
───────────────────────────
Supports three plan types:
  • simple  — lightweight, plain language, personal/early-stage use
  • bank    — loan-focused: collateral, repayment, cash flow for local banks
  • grant   — grant-compliance focused (original behaviour)

All plans are written in the language specified in state["language"].
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from graph.state import BusinessPlanState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

# ── Language instruction ──────────────────────────────────────────────────────
_LANGUAGE_PROMPTS = {
    "English":    "Write the entire business plan in English.",
    "Dutch":      "Schrijf het volledige businessplan in het Nederlands (Dutch). Alle secties, koppen en inhoud moeten in het Nederlands zijn.",
    "Spanish":    "Escribe el plan de negocios completo en español. Todas las secciones, títulos y contenido deben estar en español.",
    "Portuguese": "Escreva o plano de negócios completo em português. Todas as seções, títulos e conteúdo devem estar em português.",
    "French":     "Rédigez l'intégralité du plan d'affaires en français. Toutes les sections, titres et contenus doivent être en français.",
}

# ── System prompts per plan type ──────────────────────────────────────────────
_SIMPLE_SYSTEM = """You are a friendly business advisor helping an entrepreneur
write a clear, straightforward business plan. This is NOT for a grant or bank —
it is a simple plan the owner can use to organise their thoughts, guide their
team, or share with family and advisors.

Use plain, everyday language. Avoid heavy financial jargon. Keep sections
concise and practical.

Return a JSON object with these keys:
{
  "executive_summary":  "Short, clear overview of the business",
  "problem_statement":  "What problem or need does this business address?",
  "solution":           "What product or service is offered?",
  "market_opportunity": "Who are the customers and how big is the opportunity?",
  "business_model":     "How will the business make money?",
  "marketing_strategy": "How will customers find out about the business?",
  "operations_plan":    "Day-to-day: team, location, suppliers, key steps",
  "funding_request":    "How much money is needed and what will it be used for?"
}

Return ONLY valid JSON (no markdown fences).
"""

_BANK_SYSTEM = """You are a senior financial advisor with expertise in preparing
business loan applications for Caribbean and Suriname commercial banks
(Hakrinbank, DSB Bank, RBC Royal Bank, Republic Bank).

Bank loan officers need to see: repayment ability, collateral, cash flow
stability, and management credibility. Write with that audience in mind.

Return a JSON object with these keys:
{
  "executive_summary":  "Professional overview emphasising financial stability and repayment capacity",
  "problem_statement":  "Market gap the business fills",
  "solution":           "Product/service with clear value proposition",
  "market_opportunity": "Quantified market with customer segments",
  "business_model":     "Revenue streams and pricing — focus on cash flow predictability",
  "marketing_strategy": "Customer acquisition and retention strategy",
  "operations_plan":    "Team, location, supply chain, operational controls",
  "funding_request":    "Exact loan amount, purpose breakdown, repayment source",
  "collateral":         "Assets offered as security: property, equipment, inventory, guarantors",
  "repayment_plan":     "Proposed repayment schedule, monthly instalment estimate, loan term",
  "credit_history":     "Owner's banking relationship, existing loans, credit standing"
}

Return ONLY valid JSON (no markdown fences).
"""

_GRANT_SYSTEM = """You are an expert business plan writer with 15+ years
experience writing grant-winning proposals for Caribbean and Suriname
entrepreneurs. You understand CDB, IDB, and local government funder
requirements deeply.

You will produce a structured JSON object with these exact keys:
{
  "executive_summary":   "2-3 paragraph overview compelling to grant committees",
  "problem_statement":   "Clear articulation of the problem being solved",
  "solution":            "Product/service description and unique value proposition",
  "market_opportunity":  "Quantified market opportunity referencing research data",
  "business_model":      "Revenue streams, pricing, customer acquisition",
  "marketing_strategy":  "Go-to-market: channels, partnerships, brand positioning",
  "operations_plan":     "Team, facilities, supply chain, milestones",
  "funding_request":     "Amount requested, use of funds breakdown, ROI to grantor"
}

Emphasise job creation, community economic impact, and sustainability.
Align language with grant eligibility criteria provided.
Return ONLY valid JSON (no markdown fences).
"""

_SYSTEM_BY_TYPE = {
    "simple": _SIMPLE_SYSTEM,
    "bank":   _BANK_SYSTEM,
    "grant":  _GRANT_SYSTEM,
}


def plan_writer_agent_node(state: BusinessPlanState) -> dict[str, Any]:
    """LangGraph node for the Business Plan Writer Agent."""
    plan_type = state.get("plan_type", "grant")
    language  = state.get("language", "English")

    logger.info("Plan Writer Agent: type=%s language=%s", plan_type, language)

    lang_instruction = _LANGUAGE_PROMPTS.get(language, _LANGUAGE_PROMPTS["English"])
    system_prompt    = _SYSTEM_BY_TYPE.get(plan_type, _GRANT_SYSTEM)
    full_system      = f"{system_prompt}\n\nLANGUAGE INSTRUCTION: {lang_instruction}"

    context = {
        "business_name":          state.get("business_name", ""),
        "startup_idea":           state.get("startup_idea", ""),
        "industry":               state.get("industry", ""),
        "location":               state.get("location", ""),
        "target_customers":       state.get("target_customers", ""),
        "financial_expectations": state.get("financial_expectations", ""),
        "founder_background":     state.get("founder_background", ""),
        "plan_type":              plan_type,
        "market_research": {
            "market_size":              state.get("market_size", ""),
            "competitor_overview":      state.get("competitor_overview", ""),
            "target_customer_analysis": state.get("target_customer_analysis", ""),
            "swot_analysis":            state.get("swot_analysis", {}),
        },
        "best_matching_grants":    state.get("best_matching_grants", []),
        "compliance_suggestions":  state.get("compliance_suggestions", []),
    }

    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=(
            f"Full context:\n{json.dumps(context, indent=2)}\n\n"
            "Write the complete business plan sections as a JSON object. "
            f"Remember to write everything in {language}."
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
        plan: dict = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.warning("Plan Writer Agent: JSON parse error – %s", exc)
        plan = {
            "executive_summary":  "Plan generation failed. Please retry.",
            "problem_statement":  "",
            "solution":           "",
            "market_opportunity": "",
            "business_model":     "",
            "marketing_strategy": "",
            "operations_plan":    "",
            "funding_request":    "",
            "collateral":         "",
            "repayment_plan":     "",
            "credit_history":     "",
        }

    return {
        "executive_summary":  plan.get("executive_summary", ""),
        "problem_statement":  plan.get("problem_statement", ""),
        "solution":           plan.get("solution", ""),
        "market_opportunity": plan.get("market_opportunity", ""),
        "business_model":     plan.get("business_model", ""),
        "marketing_strategy": plan.get("marketing_strategy", ""),
        "operations_plan":    plan.get("operations_plan", ""),
        "funding_request":    plan.get("funding_request", ""),
        "collateral":         plan.get("collateral", ""),
        "repayment_plan":     plan.get("repayment_plan", ""),
        "credit_history":     plan.get("credit_history", ""),
        "current_step":       "financial_projections",
        "messages": [{
            "role":    "plan_writer_agent",
            "content": f"Business plan written — type={plan_type}, language={language}.",
        }],
    }
