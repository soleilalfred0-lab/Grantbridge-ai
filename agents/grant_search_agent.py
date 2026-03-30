import os
import json
from tools.currency_tool import convert_grant_amounts as _cga
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def search_grants(country: str = "Suriname", sector: str = "", query: str = "", language: str = "en") -> list:
    search_q = f"grants funding {country} Caribbean CARICOM entrepreneurs 2025 {sector} {query}".strip()

    try:
        results = tavily.search(
            query=search_q,
            search_depth="advanced",
            max_results=8,
            include_answer=True
        )
        raw = json.dumps(results.get("results", []))
    except Exception as e:
        print(f"[grant_search_agent] Tavily error: {e}")
        return []

    lang_map = {"en": "English", "nl": "Dutch", "es": "Spanish", "pt": "Portuguese", "fr": "French"}
    lang_name = lang_map.get(language, "English")

    prompt = f"""You are a grant research assistant specializing in Caribbean and CARICOM funding opportunities.

From the search results below, extract all grants or funding programs relevant to {country} and/or CARICOM entrepreneurs.

Search results:
{raw}

Return a JSON array. Each grant object must include:
- title: full grant/program name (string)
- org: funding organization name (string)
- amount: funding range as a readable string, e.g. "$5,000 – $50,000" (use "Not specified" if unknown)
- countries: array of eligible country names e.g. ["Suriname", "CARICOM"]
- sectors: array of sectors from: agriculture, tech, youth, women, climate, sme, health, education, tourism
- deadline: deadline as YYYY-MM-DD, or "Rolling", or "Not specified"
- desc: 1-2 sentence description in {lang_name}
- url: source URL string (use "" if not available)

Return ONLY a valid JSON array, no markdown, no explanation."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        grants = json.loads(content.strip())
        try:
            import json as _j
            raw = _cga.invoke({"grants": grants, "country": country})
            grants = _j.loads(raw) if isinstance(raw, str) else grants
        except Exception:
            pass
        return grants
    except Exception as e:
        print(f"[grant_search_agent] OpenAI/parse error: {e}")
        return []
