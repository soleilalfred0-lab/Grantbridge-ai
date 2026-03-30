"""
tools/currency_tool.py
Currency Converter Tool for Caribbean entrepreneurs.
Converts USD amounts to local currency based on country.
"""
import os, json, logging
from functools import lru_cache
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

OPEN_EXCHANGE_APP_ID = os.getenv("OPEN_EXCHANGE_APP_ID", "")

FALLBACK_RATES = {
    "SRD": 36.25, "JMD": 156.50, "TTD": 6.79, "BBD": 2.00,
    "GYD": 209.50, "BZD": 2.00, "HTG": 131.00, "XCD": 2.70,
    "EUR": 0.92, "GBP": 0.79, "USD": 1.00,
}

COUNTRY_CURRENCY = {
    "suriname": "SRD", "jamaica": "JMD", "trinidad and tobago": "TTD",
    "trinidad": "TTD", "barbados": "BBD", "guyana": "GYD", "belize": "BZD",
    "haiti": "HTG", "grenada": "XCD", "saint lucia": "XCD", "st lucia": "XCD",
    "dominica": "XCD", "antigua": "XCD", "st kitts": "XCD", "caricom": "USD",
}

CURRENCY_SYMBOLS = {
    "SRD": "SRD", "JMD": "J$", "TTD": "TT$", "BBD": "Bds$",
    "GYD": "G$", "BZD": "BZ$", "HTG": "G", "XCD": "EC$", "USD": "USD",
}

def _get_currency_code(country):
    return COUNTRY_CURRENCY.get(country.lower().strip(), "USD")

@lru_cache(maxsize=1)
def _fetch_live_rates():
    if not OPEN_EXCHANGE_APP_ID:
        return {}
    try:
        import httpx
        url = "https://openexchangerates.org/api/latest.json?app_id=" + OPEN_EXCHANGE_APP_ID + "&base=USD"
        r = httpx.get(url, timeout=5.0)
        if r.status_code == 200:
            return r.json().get("rates", {})
    except Exception as e:
        logger.warning("Live rate fetch failed: " + str(e))
    return {}

def _get_rate(currency_code):
    live = _fetch_live_rates()
    if live and currency_code in live:
        return live[currency_code]
    return FALLBACK_RATES.get(currency_code, 1.0)

def _parse_usd_amount(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        import re
        numbers = re.findall(r"[\d,]+", value.replace(".", ""))
        if numbers:
            try:
                return max(float(n.replace(",", "")) for n in numbers)
            except ValueError:
                pass
    return 0.0

def format_amount(amount_usd, country):
    code = _get_currency_code(country)
    if code == "USD":
        return "USD {:,.0f}".format(amount_usd)
    rate = _get_rate(code)
    local = amount_usd * rate
    symbol = CURRENCY_SYMBOLS.get(code, code)
    return "USD {:,.0f} (approx. {} {:,.0f})".format(amount_usd, symbol, local)

@tool
def convert_currency(amount_usd: float, country: str, format_output: bool = True) -> str:
    """
    Convert a USD amount to the local currency of a Caribbean country.
    Use this when displaying funding amounts or financial figures to entrepreneurs.
    Args:
        amount_usd: Amount in US Dollars.
        country: Entrepreneur country e.g. Suriname, Jamaica.
        format_output: Return formatted string if True, JSON if False.
    Returns: Formatted amount string with both USD and local currency.
    """
    try:
        code = _get_currency_code(country)
        rate = _get_rate(code)
        local = amount_usd * rate
        symbol = CURRENCY_SYMBOLS.get(code, code)
        if format_output:
            if code == "USD":
                return "USD {:,.0f}".format(amount_usd)
            return "USD {:,.0f} (approx. {} {:,.0f})".format(amount_usd, symbol, local)
        return json.dumps({
            "usd_amount": amount_usd, "local_amount": round(local, 2),
            "currency_code": code, "currency_symbol": symbol,
            "exchange_rate": rate, "country": country,
            "formatted": "USD {:,.0f} (approx. {} {:,.0f})".format(amount_usd, symbol, local),
        })
    except Exception as e:
        return "USD {:,.0f}".format(amount_usd)

@tool
def convert_grant_amounts(grants: list, country: str) -> str:
    """
    Enrich a list of grants with local currency equivalents for the given country.
    Use after retrieving grants to add local currency amounts before display.
    Args:
        grants: List of grant dicts with funding_amount fields.
        country: Entrepreneur country for currency conversion.
    Returns: JSON string of grants with local_amount and formatted_amount added.
    """
    try:
        code = _get_currency_code(country)
        rate = _get_rate(code)
        symbol = CURRENCY_SYMBOLS.get(code, code)
        enriched = []
        for grant in grants:
            g = dict(grant)
            usd_val = _parse_usd_amount(g.get("funding_amount", "") or g.get("max_amount_usd", 0))
            if usd_val and code != "USD":
                local_val = usd_val * rate
                g["local_amount"] = round(local_val, 0)
                g["local_currency"] = code
                g["local_symbol"] = symbol
                g["formatted_amount"] = "USD {:,.0f} (approx. {} {:,.0f})".format(usd_val, symbol, local_val)
            else:
                g["formatted_amount"] = g.get("funding_amount", "See source")
            enriched.append(g)
        return json.dumps(enriched)
    except Exception as e:
        return json.dumps(grants)
