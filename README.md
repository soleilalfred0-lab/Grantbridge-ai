# 🇸🇷 Suriname Business Plan Generator
### AI-powered, Grant-Ready Business Plans for Caribbean Entrepreneurs

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-teal)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 Overview

An **AI-powered multi-agent system** built with LangGraph that guides entrepreneurs
in Suriname and CARICOM countries through generating a complete, grant-ready business
plan — from raw idea to submission-ready document in minutes.

### Why This Exists

Caribbean entrepreneurs face two key barriers to accessing grants:
1. **Knowledge gap** — unclear which grants they qualify for
2. **Quality gap** — business plans that don't meet funder standards

This system solves both by combining LLM intelligence with structured grant
databases and an iterative compliance loop.

---

## 🏗️ Architecture

### LangGraph Workflow

```
User Input (API)
      │
      ▼
┌─────────────┐
│ Intake Agent│  ← Enriches & validates user inputs
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│Grant Research    │  ← Matches grants from CDB, IDB, Suriname Gov, UNDP
│Agent             │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│Market Research   │  ← Market size, SWOT, competitors (Caribbean context)
│Agent             │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│Plan Writer Agent │  ← Generates all 8 business plan sections
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│Financial Agent   │  ← Startup costs, 3-year projections, break-even
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│Compliance Agent  │  ← Audits plan vs grant criteria, scores 0–1
└──────┬───────────┘
       │
       ▼
   Score ≥ 0.85                Score < 0.85
   or max revisions?      ←────────────────── Revision Loop (max 3×)
       │                       (re-runs Plan Writer with suggestions)
       ▼
┌──────────────────┐
│Assemble Plan     │  ← Combines all sections into Markdown
└──────┬───────────┘
       │
       ▼
 Final Plan + Store
 in Vector DB (RAG)
```

### Memory Architecture

| Type | Technology | Purpose |
|------|-----------|---------|
| **Short-term** | LangGraph State (TypedDict) | In-pipeline conversation & data flow |
| **Long-term** | ChromaDB / FAISS | Store past plans, enable RAG retrieval |

### Multi-Agent Design

| Agent | Responsibility | LLM Temp |
|-------|--------------|---------|
| `IntakeAgent` | Validate & enrich user inputs | 0.3 |
| `GrantResearchAgent` | Find matching grants (CDB, IDB, Gov) | 0.2 |
| `MarketResearchAgent` | Market size, SWOT, competitors | 0.4 |
| `PlanWriterAgent` | Write all 8 plan sections | 0.5 |
| `FinancialAgent` | Startup costs, 3-yr projections, break-even | 0.2 |
| `ComplianceAgent` | Audit vs grant criteria, score, suggest fixes | 0.2 |

---

## 📁 Project Structure

```
business-plan-generator/
│
├── agents/
│   ├── intake_agent.py           # User Intake Agent
│   ├── grant_research_agent.py   # Grant Research Agent
│   ├── market_research_agent.py  # Market Research Agent
│   ├── plan_writer_agent.py      # Business Plan Writer Agent
│   ├── financial_agent.py        # Financial Projection Agent
│   └── compliance_agent.py       # Grant Compliance Agent
│
├── tools/
│   ├── web_search.py             # Tavily / SerpAPI web search tool
│   ├── grant_lookup.py           # Structured grant database lookup
│   └── financial_tools.py        # Break-even, projections, currency
│
├── memory/
│   └── vector_store.py           # ChromaDB / FAISS long-term memory
│
├── graph/
│   ├── state.py                  # BusinessPlanState TypedDict
│   └── business_plan_graph.py    # LangGraph graph + routing logic
│
├── api/
│   └── app.py                    # FastAPI application
│
├── docker/
│   └── docker-compose.yml
│
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- OpenAI API key
- (Optional) Tavily API key for web search

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/suriname-business-plan-generator.git
cd suriname-business-plan-generator

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

```bash
cp .env.example .env
# Edit .env and add your API keys:
#   OPENAI_API_KEY=sk-...
#   TAVILY_API_KEY=tvly-...   (optional)
```

### 4. Run the API

```bash
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000/docs** for the interactive API explorer.

### 5. Generate Your First Business Plan

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "AgroTech Suriname",
    "startup_idea": "Mobile app connecting Surinamese farmers to urban buyers, reducing food waste by 40%",
    "industry": "agritech",
    "location": "Paramaribo, Suriname",
    "target_customers": "500 small-scale farmers and 50,000 urban consumers",
    "financial_expectations": "Seeking USD 50,000 grant for app development and farmer onboarding",
    "founder_background": "Agricultural engineer with 5 years field experience and mobile development skills"
  }'
```

---

## 🔌 API Reference

### `POST /generate`
Run the full pipeline. Returns a complete Markdown business plan.

**Request body:** `IntakeRequest`
**Response:** `PlanResponse` with `final_plan` (Markdown), `compliance_score`, `grants_matched`

### `GET /grants`
Search available grants by industry and location.

**Query params:** `industry`, `location`, `funding`

### `GET /similar-plans`
Retrieve semantically similar past plans from the vector store (RAG).

**Query params:** `query`, `top_k`

### `GET /health`
Returns service health status.

---

## 💡 Example Interaction

**Input:**
```json
{
  "business_name": "EcoTours Suriname",
  "startup_idea": "Eco-tourism platform connecting international tourists with indigenous community guides in the Suriname interior",
  "industry": "tourism",
  "location": "Brokopondo, Suriname",
  "target_customers": "International eco-tourists aged 25-55 from Netherlands, USA, Brazil",
  "financial_expectations": "USD 75,000 to fund guide training, website, and first-year marketing",
  "founder_background": "Former Ministry of Tourism employee, fluent in Dutch, English, Sranan Tongo"
}
```

**Output (excerpt):**
```markdown
# EcoTours Suriname
## Complete Business Plan – Grant Application Edition

## 1. Executive Summary
EcoTours Suriname addresses the gap between Suriname's extraordinary
biodiversity and the international eco-tourism market...

## 10. Recommended Grant Programmes
### 1. UNDP Small Grants Programme
- Provider: United Nations Development Programme
- Max Amount: USD 50,000
- Match Score: 90%
```

---

## 🌍 Supported Grant Programmes

| Programme | Provider | Max Amount | Focus |
|-----------|---------|-----------|-------|
| CDB Basic Needs Trust Fund | Caribbean Development Bank | USD 500,000 | Social impact, community |
| IDB SME Competitiveness | Inter-American Development Bank | USD 250,000 | Tech, innovation, SME |
| Suriname S-FONDS | Suriname Government | USD 50,000 | Local businesses |
| CARICOM Innovation Grant | CARICOM Secretariat | USD 100,000 | Regional innovation |
| UNDP Small Grants | United Nations | USD 50,000 | Environment, climate |
| GEF Climate Innovation | World Bank / GEF | USD 200,000 | Climate, renewables |

---

## 🐳 Docker Deployment

### Option 1 – Docker Compose (Recommended)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Build and run
docker compose -f docker/docker-compose.yml up --build

# API available at http://localhost:8000
```

### Option 2 – AWS EC2 + Docker

```bash
# 1. Launch an EC2 instance (t3.medium recommended)
#    AMI: Ubuntu 22.04 LTS
#    Security group: allow port 8000 (or 80/443 with Nginx)

# 2. SSH in and install Docker
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu

# 3. Clone and deploy
git clone https://github.com/yourusername/suriname-business-plan-generator.git
cd suriname-business-plan-generator
cp .env.example .env
# nano .env  →  add your API keys

docker compose -f docker/docker-compose.yml up -d --build

# 4. (Optional) Set up Nginx reverse proxy + SSL with Certbot
sudo apt install nginx certbot python3-certbot-nginx
# Configure /etc/nginx/sites-available/business-plan and run certbot
```

### Option 3 – AWS ECS (Production)

```bash
# 1. Build and push to ECR
aws ecr create-repository --repository-name business-plan-generator
aws ecr get-login-password | docker login --username AWS \
  --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

docker build -t business-plan-generator .
docker tag business-plan-generator:latest \
  <account>.dkr.ecr.<region>.amazonaws.com/business-plan-generator:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/business-plan-generator:latest

# 2. Create ECS task definition using the pushed image
# 3. Set env vars via AWS Secrets Manager (OPENAI_API_KEY etc.)
# 4. Create ECS service with Application Load Balancer
```

### Option 4 – AWS Lambda (Serverless)

> ⚠️ Lambda has a 15-minute timeout. Suitable only if your pipeline
> completes within that window. For longer plans, use ECS.

```bash
# Install Mangum adapter for ASGI → Lambda
pip install mangum

# Wrap the FastAPI app in lambda_handler.py:
# from mangum import Mangum
# from api.app import app
# handler = Mangum(app)

# Package and deploy via AWS SAM or Serverless Framework
sam build && sam deploy --guided
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model to use |
| `VECTOR_BACKEND` | `chroma` | `chroma` or `faiss` |
| `CHROMA_PERSIST_PATH` | `./data/chroma_db` | ChromaDB storage path |
| `TAVILY_API_KEY` | optional | For live web search |
| `PORT` | `8000` | API server port |
| `WORKERS` | `1` | Uvicorn worker count |
| `ENV` | `production` | `development` enables hot reload |

---

## 🗺️ Roadmap

- [ ] Async pipeline with WebSocket streaming
- [ ] PDF export of completed business plans
- [ ] Multi-language support (Dutch, Sranan Tongo, Papiamento)
- [ ] Integration with Suriname Chamber of Commerce (KKF) API
- [ ] User authentication and plan history
- [ ] Dashboard UI (React/Next.js)
- [ ] WhatsApp bot interface for low-bandwidth access

---

## 📜 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built to support Caribbean entrepreneurship using:
- [LangGraph](https://langchain-ai.github.io/langgraph/) by LangChain
- [FastAPI](https://fastapi.tiangolo.com)
- [ChromaDB](https://www.trychroma.com)
- Data from CDB, IDB, UNDP, and Suriname government resources

---

*Made with ❤️ for Suriname and the Caribbean*
