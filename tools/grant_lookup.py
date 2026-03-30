"""
Grant Lookup Tool
──────────────────
Simulates a structured database of Caribbean/Suriname grants.

In production this would connect to:
  • A live CDB / IDB API
  • A PostgreSQL grants database
  • A web scraper for government portals
"""

from __future__ import annotations

import re
from typing import Any

# ── Simulated grant database ──────────────────────────────────────────────────
_GRANT_DATABASE: list[dict] = [
    {
        "id": "CDB-BNTF-001",
        "name": "CDB Basic Needs Trust Fund (BNTF)",
        "provider": "Caribbean Development Bank",
        "max_amount_usd": 500_000,
        "eligibility_criteria": [
            "Must operate in a CDB borrowing member country",
            "Project must target low-income communities",
            "Must demonstrate measurable social impact",
            "Job creation component required",
            "Community ownership or participation preferred",
        ],
        "required_documents": [
            "Business registration certificate",
            "2 years of financial statements (or projections for startups)",
            "Project proposal with logical framework",
            "Community impact assessment",
        ],
        "focus_areas": ["agriculture", "education", "health", "infrastructure", "social services"],
        "application_url": "https://www.caribank.org/programmes/bntf",
        "deadline_notes": "Annual cycle – applications open Q1",
        "regions": ["suriname", "caricom"],
    },
    {
        "id": "IDB-SME-002",
        "name": "IDB SME Competitiveness Programme",
        "provider": "Inter-American Development Bank",
        "max_amount_usd": 250_000,
        "eligibility_criteria": [
            "SME with fewer than 100 employees",
            "Operating in Latin America or Caribbean",
            "Demonstrated growth potential",
            "Technology adoption or innovation component",
            "Financial sustainability plan required",
        ],
        "required_documents": [
            "Company registration",
            "3-year financial projections",
            "Technology adoption plan",
            "Market analysis",
        ],
        "focus_areas": ["technology", "agritech", "fintech", "tourism", "manufacturing"],
        "application_url": "https://www.iadb.org/en/projects",
        "deadline_notes": "Rolling applications",
        "regions": ["suriname", "caricom", "latin_america"],
    },
    {
        "id": "SR-GOV-SME-003",
        "name": "Suriname S-FONDS SME Support Programme",
        "provider": "Suriname Government / Ministry of Finance",
        "max_amount_usd": 50_000,
        "eligibility_criteria": [
            "Must be registered in Suriname",
            "Owner must be Surinamese national",
            "Must employ at least 2 Surinamese workers",
            "Business must serve local market",
            "Priority to agribusiness, ICT, and manufacturing",
        ],
        "required_documents": [
            "KKF (Chamber of Commerce) registration",
            "National ID",
            "Business plan",
            "Bank statements (3 months)",
        ],
        "focus_areas": ["agriculture", "ict", "manufacturing", "retail", "services"],
        "application_url": "https://gov.sr/smefund",
        "deadline_notes": "Quarterly – contact Ministry of Finance",
        "regions": ["suriname"],
    },
    {
        "id": "CARICOM-INNOV-004",
        "name": "CARICOM Regional Innovation Grant",
        "provider": "CARICOM Secretariat",
        "max_amount_usd": 100_000,
        "eligibility_criteria": [
            "Must operate across 2+ CARICOM member states",
            "Innovation or technology must be central to business model",
            "Must address a regional challenge",
            "Youth (under 35) or women-led businesses prioritised",
        ],
        "required_documents": [
            "CARICOM business registration",
            "Innovation description",
            "Regional market analysis",
            "Partnership letters from 2+ member states",
        ],
        "focus_areas": ["technology", "innovation", "climate", "food_security", "digital"],
        "application_url": "https://caricom.org/grants",
        "deadline_notes": "Annual – typically March deadline",
        "regions": ["caricom"],
    },
    {
        "id": "UNDP-SGP-005",
        "name": "UNDP Small Grants Programme",
        "provider": "United Nations Development Programme",
        "max_amount_usd": 50_000,
        "eligibility_criteria": [
            "NGO, community group, or social enterprise",
            "Focus on environmental sustainability",
            "Climate change adaptation component",
            "Must benefit marginalised communities",
            "Local partner required",
        ],
        "required_documents": [
            "Organisation profile",
            "Project proposal",
            "Environmental impact assessment",
            "Community endorsement letters",
        ],
        "focus_areas": ["environment", "climate", "agriculture", "coastal", "forestry"],
        "application_url": "https://sgp.undp.org",
        "deadline_notes": "Rolling applications reviewed bi-annually",
        "regions": ["suriname", "caricom", "global"],
    },
    {
        "id": "GEF-CLIM-006",
        "name": "Global Environment Facility (GEF) Climate Innovation Fund",
        "provider": "GEF / World Bank",
        "max_amount_usd": 200_000,
        "eligibility_criteria": [
            "Must demonstrate environmental benefit",
            "Climate adaptation or mitigation focus",
            "Co-funding of at least 20% required",
            "Government endorsement preferred",
        ],
        "required_documents": [
            "Environmental impact assessment",
            "Climate change mitigation plan",
            "Co-funding commitment letters",
            "Full project proposal",
        ],
        "focus_areas": ["renewable_energy", "climate", "environment", "agriculture", "water"],
        "application_url": "https://www.thegef.org/grants",
        "deadline_notes": "Annual cycle",
        "regions": ["suriname", "caricom", "global"],
    },
]


def lookup_grants(
    industry: str,
    location: str = "Suriname",
    funding_needed: str = "",
) -> list[dict[str, Any]]:
    """
    Return relevant grants filtered by industry and location.

    Parameters
    ----------
    industry : str
        The applicant's industry (e.g. "agritech", "fintech").
    location : str
        Country or region of operation.
    funding_needed : str
        Free-text description of funding expectations (used for soft matching).

    Returns
    -------
    list[dict]
        List of matching grant objects with an added ``match_score`` field.
    """
    industry_lower = industry.lower()
    location_lower = location.lower()

    results: list[dict] = []

    for grant in _GRANT_DATABASE:
        score = 0.0

        # Region match
        for region in grant.get("regions", []):
            if region in location_lower or location_lower in region:
                score += 0.4
                break
        else:
            # Suriname-based businesses qualify for CARICOM grants
            if "suriname" in location_lower and "caricom" in grant.get("regions", []):
                score += 0.2

        # Industry / focus area match
        for focus in grant.get("focus_areas", []):
            if focus in industry_lower or any(
                kw in industry_lower for kw in focus.split("_")
            ):
                score += 0.5
                break

        # Funding amount soft match
        if funding_needed:
            numbers = re.findall(r"\d[\d,]*", funding_needed.replace(",", ""))
            if numbers:
                ask = int(numbers[0])
                max_grant = grant.get("max_amount_usd", 0)
                if ask <= max_grant:
                    score += 0.1

        if score > 0.2:
            enriched = dict(grant)
            enriched["match_score"] = round(min(score, 1.0), 2)
            results.append(enriched)

    results.sort(key=lambda g: g["match_score"], reverse=True)
    return results
