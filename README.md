# GrantBridge AI 🌴

**A multi-agent AI platform that helps Caribbean entrepreneurs discover funding opportunities and generate complete, grant-ready business plans — in 5 languages.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-grantbridge.soleilalfred.com-00b87c?style=flat-square)](https://grantbridge.soleilalfred.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-ff6b35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📄 Project Report

> **[Download the full project report (18 pages) →](GrantBridge_AI_Capstone_Report_v2.pdf)**

---

## 🎬 Demo Video

> **[Watch the full demo on Loom →](https://www.loom.com/share/25c7912f5f2f495b89eff079f253fedc)**

---

## 🌍 What It Does

Caribbean entrepreneurs face a persistent funding gap — grant programmes from the IDB, CDB, EU, and national governments exist, but most small business owners do not know where to look or how to write a formal application.

GrantBridge AI solves this end-to-end:

1. **Discovers** relevant grants from a curated Caribbean funding database using semantic search
2. **Researches** live market conditions for the user's sector and country via web search
3. **Pauses for human review** at two checkpoints so the entrepreneur stays in control
4. **Generates** a complete, structured business plan with financial projections
5. **Checks compliance** against grant criteria and revises if needed
6. **Exports** the final plan as a branded PDF or plain text file

All of this happens in the user's chosen language: **English, Dutch, Spanish, Portuguese, or French**.

---

## ✨ Features

| Feature | Details |
|---|---|
| Multi-agent pipeline | 6 specialised LangGraph agents running in sequence |
| Human-in-the-loop | 2 review checkpoints — user edits are incorporated verbatim |
| Semantic grant search | FAISS vector search over 40+ verified Caribbean funding programmes |
| Live web search | Tavily API for real-time market research and grant discovery |
| 5 languages | ENG, NLD, SPA, POR, FRA — full UI and plan output |
| 3 plan types | Grant Application, Bank Loan Plan, Simple Plan |
| PDF export | Branded cover page, formatted sections, downloadable |
| Grant Browser | Standalone search page with dual-currency display |
| HTTPS deployment | Custom domain, Let's Encrypt TLS, Nginx reverse proxy |
| Dark / light mode | Persisted via localStorage |

---

## 🏗️ Architecture
```
intake → grant_research → market_research
      → [HITL checkpoint 1]
      → plan_writer
      → [HITL checkpoint 2]
      → financial → compliance → END
             ↑ revision loop (max 2x) ↓
```

### Agent Roles

| Agent | Responsibility |
|---|---|
| intake_agent | Extracts structured fields from the form submission |
| grant_research_agent | FAISS semantic search + Tavily live grant discovery |
| market_research_agent | Live market size, competitors, and customer analysis |
| plan_writer_agent | Generates all 8 plan sections in the user's language |
| financial_agent | Revenue projections, cost breakdown, break-even analysis |
| compliance_agent | Scores plan 0-1, triggers revision loop if score < 0.75 |

### Registered Tools (4)

| Tool | Type | Description |
|---|---|---|
| retrieve_grants | FAISS / RAG | Semantic search over Caribbean grant dataset |
| write_proposal_file | File I/O | Saves plan as .md, returns download URL |
| convert_currency | API (fallback rates) | USD to SRD, JMD, TTD, BBD, XCD, HTG |
| convert_grant_amounts | Wrapper | Enriches grant list with local currency amounts |

---

## 🚀 Quick Start
```bash
git clone https://github.com/soleilalfred0-lab/Grantbridge-ai.git
cd Grantbridge-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Evaluation

| Metric | Result |
|---|---|
| Overall success rate | 15/15 (100%) |
| First-pass success | 13/15 (86.7%) |
| Average compliance score | 0.837 |
| Average grant matches | 3.3 per run |
| Average generation time | ~95 seconds |
| Estimated cost per run | ~$0.004 (GPT-4o-mini) |

---

## 🌐 Deployment

Live at **[grantbridge.soleilalfred.com](https://grantbridge.soleilalfred.com)**

| Layer | Technology |
|---|---|
| DNS | GoDaddy A record to EC2 |
| TLS | Let's Encrypt via Certbot |
| Reverse proxy | Nginx |
| App server | Uvicorn on AWS EC2 t2.micro |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 👩‍💻 Author

**Soleil Alfred** — Capstone project for *Building Agentic AI Systems*

🌐 [grantbridge.soleilalfred.com](https://grantbridge.soleilalfred.com) · 🎬 [Demo Video](https://www.loom.com/share/25c7912f5f2f495b89eff079f253fedc) · 📄 [Project Report](GrantBridge_AI_Capstone_Report_v2.pdf)
