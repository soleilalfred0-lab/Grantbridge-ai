"""
Financial Calculation Tools
─────────────────────────────
Utility functions used by the Financial Projection Agent.
"""

from __future__ import annotations

SRD_PER_USD = 36.0  # Approximate exchange rate as of 2024


def calculate_break_even(
    fixed_costs: float,
    variable_cost_ratio: float,
) -> float:
    """
    Calculate monthly break-even revenue.

    Parameters
    ----------
    fixed_costs : float
        Total monthly fixed costs in USD.
    variable_cost_ratio : float
        Variable costs as a fraction of revenue (0.0 – 1.0).
        E.g. 0.4 means 40 cents of every dollar is variable cost.

    Returns
    -------
    float
        Monthly revenue required to break even, in USD.
    """
    if variable_cost_ratio >= 1.0:
        raise ValueError("variable_cost_ratio must be less than 1.0")

    contribution_margin = 1.0 - variable_cost_ratio
    if contribution_margin == 0:
        return float("inf")

    return round(fixed_costs / contribution_margin, 2)


def format_currency_srd(amount_usd: float) -> str:
    """Convert USD amount to SRD string."""
    srd = amount_usd * SRD_PER_USD
    return f"SRD {srd:,.0f}  (≈ USD {amount_usd:,.0f})"


def build_3year_projection(
    year1_revenue: float,
    growth_rate_y2: float = 0.30,
    growth_rate_y3: float = 0.25,
    expense_ratio: float = 0.65,
) -> dict:
    """
    Build a simple 3-year revenue model.

    Parameters
    ----------
    year1_revenue : float
        Projected Year 1 total revenue in USD.
    growth_rate_y2 : float
        Revenue growth rate for Year 2 (default 30%).
    growth_rate_y3 : float
        Revenue growth rate for Year 3 (default 25%).
    expense_ratio : float
        Expenses as fraction of revenue (default 65%).

    Returns
    -------
    dict
        Three-year projection dict.
    """
    def _year(revenue: float) -> dict:
        expenses = round(revenue * expense_ratio, 2)
        net = round(revenue - expenses, 2)
        return {
            "revenue":    round(revenue, 2),
            "expenses":   expenses,
            "net_profit": net,
        }

    y1 = _year(year1_revenue)
    y2 = _year(year1_revenue * (1 + growth_rate_y2))
    y3 = _year(y2["revenue"] * (1 + growth_rate_y3))

    return {
        "year_1": {**y1, "growth_rate": "Base year"},
        "year_2": {**y2, "growth_rate": f"{growth_rate_y2:.0%}"},
        "year_3": {**y3, "growth_rate": f"{growth_rate_y3:.0%}"},
    }


def estimate_startup_costs(
    industry: str,
    location: str = "Suriname",
) -> dict:
    """
    Return rough startup cost benchmarks by industry.
    These are indicative ranges used when the LLM needs a starting point.
    """
    templates = {
        "agritech": {
            "equipment":       15_000,
            "working_capital": 10_000,
            "marketing":        3_000,
            "licenses_legal":   2_000,
            "technology":       5_000,
            "other":            2_000,
        },
        "fintech": {
            "equipment":        5_000,
            "working_capital":  20_000,
            "marketing":        8_000,
            "licenses_legal":   10_000,
            "technology":       30_000,
            "other":             5_000,
        },
        "tourism": {
            "equipment":       10_000,
            "working_capital":  15_000,
            "marketing":        5_000,
            "licenses_legal":    3_000,
            "technology":        3_000,
            "other":             4_000,
        },
        "retail": {
            "equipment":        8_000,
            "working_capital":  20_000,
            "marketing":         4_000,
            "licenses_legal":    2_000,
            "technology":        3_000,
            "other":             3_000,
        },
    }

    industry_key = industry.lower().split()[0]
    costs = templates.get(industry_key, {
        "equipment":       10_000,
        "working_capital": 15_000,
        "marketing":        4_000,
        "licenses_legal":   3_000,
        "technology":       5_000,
        "other":            3_000,
    })

    total_usd = sum(costs.values())
    costs["total_usd"] = total_usd
    costs["total_srd"] = round(total_usd * SRD_PER_USD)
    costs["notes"] = f"Indicative estimates for {industry} in {location}."
    return costs
