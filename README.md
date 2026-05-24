<div align="center">

# AegisAI

**Open-source AI Governance, Risk & Compliance (AI-GRC) Platform**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Getting Started](docs/getting-started.md) · [Architecture](docs/architecture.md) · [API Reference](docs/api-reference.md) · [Guard Module](docs/guard-module.md) · [RAG Module](docs/rag-module.md) · [Regulations](docs/regulations.md) · [Report a Bug](https://github.com/SdSarthak/AegisAI/issues)

</div>

---

## What is AegisAI?

Every company shipping AI in Europe now faces legal obligations under the **EU AI Act** (in force April 2026). Most compliance tools cost thousands per month and are closed-source.

**AegisAI is the open-source alternative** — a full-stack platform that combines three things into one:

| Module | What it does |
|---|---|
| **Compliance Engine** | Register AI systems, classify EU AI Act risk (Minimal / Limited / High / Unacceptable), generate required documentation (Technical Docs, Risk Assessment, Conformity Declaration), export as PDF |
| **LLM Guard** | Real-time prompt injection detection using regex + DeBERTa-v3 ML classifier — protect your LLM APIs with per-user rate limiting and a standalone SDK |
| **RAG Intelligence** | Ask natural language questions about EU AI Act, GDPR, ISO 42001 — grounded answers from regulatory source docs with feedback and quality tracking |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 5, Tailwind CSS, Zustand, TanStack Query, react-hot-toast |
| Backend | Python 3.11, FastAPI 0.109, SQLAlchemy 2.0, PostgreSQL 15, Alembic |
| ML (Guard) | PyTorch, HuggingFace Transformers (DeBERTa-v3-small), scikit-learn |
| RAG | LangChain 0.2, FAISS, OpenAI-compatible embeddings |
| MLOps | MLflow, Prometheus metrics |
| Infra | Docker Compose, Kubernetes (HPA configs included), GitHub Actions CI |
| Auth | JWT (python-jose), bcrypt |

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/SdSarthak/AegisAI.git
cd AegisAI

cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY and LLM_API_KEY at minimum

docker compose up -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

### Option 2 — Manual

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Option 3 — Ollama (free, no API key)

```bash
ollama pull llama3.2   # or mistral, phi3
```

Set in `backend/.env`:
```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
```

Then `docker compose up -d`. See [Getting Started](docs/getting-started.md) for all provider options.

---

## ⚙️ Environment Variables Configuration

The application requires several environment variables for application behavior, database connectivity, authentication, payment processing, and LLM providers. Copy the `backend/.env.example` file to create your `backend/.env` file and configure the following variables:

### 📱 Core Application & Database
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | The name of the application. | Optional | `AegisAI` |
| `DEBUG` | Toggles debug mode for detailed error logs. | Optional | `true` |
| `API_V1_PREFIX` | Base routing prefix for version 1 of the API endpoints. | Optional | `/api/v1` |
| `DATABASE_URL` | PostgreSQL connection string used by the backend. | **Required** | `postgresql://postgres:postgres@localhost:5432/aegisai_db` |

### 🔒 Authentication
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Secret key used to sign and verify JSON Web Tokens. | **Required** | *Generate via:* `openssl rand -hex 32` |
| `ALGORITHM` | Algorithm used for JWT encryption. | Optional | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration duration in minutes. | Optional | `30` |

### 💳 Stripe Integration (Billing)
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `STRIPE_SECRET_KEY` | Secret key for Stripe API authentication. | Optional (Leave blank to disable billing) | `sk_test_...` |
| `STRIPE_PUBLISHABLE_KEY` | Public key used on the frontend client for Stripe. | Optional | `pk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Secret key used to validate incoming Stripe webhook events. | Optional | `whsec_...` |
| `STRIPE_PRICE_STARTER` / `GROWTH` / `SCALE` | Price IDs mapped to specific subscription tiers in Stripe. | Optional | `price_...` |

### 🤖 LLM Provider (OpenAI-compatible)
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `LLM_API_KEY` | API Key for your LLM provider. Set to `ollama` for local setups. | **Required** | `sk-...` or `gsk_...` or `ollama` |
| `LLM_BASE_URL` | Base endpoint URL for the LLM provider. Leave empty for OpenAI. | Optional | `http://localhost:11434/v1` (Ollama) |
| `LLM_MODEL` | Specific model name deployed or targeted by the backend. | **Required** | `gpt-4o-mini`, `llama3.2`, or `llama-3.3-70b-versatile` |

### 🛡️ Module 2 & 3 Configurations (Guard & RAG)
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `GUARD_SANITIZATION_LEVEL`| Strictness setting for prompt sanitization. | Optional | `medium` |
| `GUARD_MAX_PROMPT_LENGTH` | Maximum allowed character length for a prompt. | Optional | `2000` |
| `S3_BUCKET_NAME` | AWS S3 Bucket Name for cloud asset storage. | Optional | `my-aegisai-bucket` |
| `FAISS_INDEX_PATH` | Local directory path where the FAISS index is saved. | Optional | `faiss_index` |
| `RAG_CHUNK_SIZE` | Maximum token/character length for text chunks. | Optional | `1000` |
| `RAG_CHUNK_OVERLAP` | Overlapping token/character footprint between chunks. | Optional | `200` |

### 📊 MLflow Tracking
| Variable Name | Description | Required / Optional | Default / Example Value |
| :--- | :--- | :--- | :--- |
| `MLFLOW_TRACKING_URI` | Destination server URI for tracking RAG query evaluations. | Optional (Defaults locally to `./mlruns`) | `http://localhost:5000` |

---
## 📓 Colab Notebooks

If you want to train the machine learning models yourself, you can run our official Google Colab notebooks on a free T4 GPU:

- [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/gist/amritanshu2611/7a533926b3df02d2ea0df5bd51641361/finetune_regulatory_model.ipynb) **Fine-tune Regulatory Q&A Model (Llama-3.2-3B QLoRA)**

---

## Project Structure

```
AegisAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (auth, ai_systems, classification,
│   │   │                    #   documents, guard, rag, analytics, badge,
│   │   │                    #   notifications, webhooks)
│   │   ├── core/            # Config, DB, JWT security
│   │   ├── models/          # SQLAlchemy ORM models (users, ai_systems,
│   │   │                    #   documents, rag_feedback, audit_log, ...)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── modules/
│   │       ├── guard/       # LLM Guard — regex + DeBERTa classifier + sanitizer
│   │       │   ├── training/ # Standard ML training pipeline
│   │       │   │   ├── configs/     # YAML training configuration
│   │       │   │   ├── data/        # Dataset loading, preprocessing, splitting
│   │       │   │   ├── evaluation/  # Metrics and evaluator
│   │       │   │   ├── pipelines/   # Train and evaluate pipeline entry points
│   │       │   │   ├── trainer/     # IntentClassifier trainer wrapper
│   │       │   │   ├── utils/       # Logging, seed, checkpoints, MLflow helpers
│   │       │   │   └── artifacts/   # Checkpoints, metrics, reports
│   │       │   └── models/classifier/ # Fine-tuned guard classifier output
│   │       ├── rag/         # RAG — FAISS vector store + LangChain chain + feedback
│   │       ├── llm/         # OpenAI-compatible LLM client
│   │       └── badge/       # SVG compliance badge generator
│   ├── data/
│   │   ├── regulatory_qa.csv        # 75-row QA dataset (EU AI Act, GDPR, ISO 42001)
│   │   └── regulatory_docs/         # Add your regulatory PDFs here
│   └── tests/               # Pytest suite — unit + integration tests
├── frontend/                # React + TypeScript dashboard
│   └── src/
│       ├── pages/           # Dashboard, AISystems, Classification, Documents,
│       │                    #   Analytics, Notifications, Onboarding, Login, Register
│       ├── components/      # Layout, ComplianceChecklist, DocumentEditor,
│       │                    #   NotificationBell, ThemeToggle
│       ├── services/api.ts  # Axios client for all endpoints
│       └── stores/          # Zustand auth store
├── guard-sdk/               # Standalone Python package (v0.1.0) — importable LLMGuard
├── mcp/                     # Model Context Protocol server scaffold
├── infra/                   # Kubernetes Deployment + HPA configs
├── notebooks/               # Jupyter — train Guard classifier on GPU (Colab-ready)
├── scripts/                 # scan_prompts.py CLI for scanning .prompts/ files
├── postman/                 # Postman collection for all API endpoints
├── docs/                    # Architecture, API reference, module guides
└── docker-compose.yml
```

---

## What's New

Recent community contributions (May 2026):

- **PDF export** — download any compliance document as PDF (`GET /documents/{id}/pdf`)
- **Bulk CSV import** — register many AI systems at once (`POST /ai-systems/import`)
- **AI Systems search + filter** by name, risk level, and compliance status
- **Per-user rate limiting** on Guard scan endpoint
- **SVG compliance badges** — embed a live compliance badge in your README
- **PATCH /users/me** — update user profile
- **RAG feedback** — thumbs up/down on answers + low-quality chunk surfacing
- **Guard SDK** — standalone package in `guard-sdk/` (PyPI coming soon)
- **Global toast notifications** in the frontend (react-hot-toast)
- **Guard scan CI Action** — automatically scans `.prompts/` files on every PR
- **75-row regulatory QA dataset** for RAG evaluation
- **Multi-regulation comparison doc** — EU AI Act vs UK AI Bill vs India DPDP

---

## Roadmap

- [x] EU AI Act risk classification engine
- [x] AI system registry + compliance dashboard
- [x] Compliance document generation (Technical Docs, Risk Assessment, Conformity Declaration)
- [x] PDF export for compliance documents
- [x] LLM Guard — regex + DeBERTa ML classifier + sanitizer + rate limiting
- [x] RAG query endpoint + feedback loop + low-quality chunk tracking
- [x] SVG compliance badge generator
- [x] Bulk CSV import for AI systems
- [x] AI Systems search and filter
- [x] User profile management (PATCH /users/me)
- [x] Guard SDK (standalone package)
- [x] Guard scan GitHub Action
- [x] 75-row regulatory QA evaluation dataset
- [ ] Pre-loaded regulatory knowledge base (EU AI Act PDF, GDPR, ISO 42001, NIST AI RMF)
- [ ] Notification model + bell UI (in progress)
- [ ] Audit log for all Guard scan decisions (in progress)
- [ ] Compliance score rollup over time (in progress)
- [ ] Reassessment reminder scheduler
- [ ] Onboarding wizard
- [ ] MCP server (Claude / Copilot integration)
- [ ] Guard SDK published to PyPI
- [ ] Multi-regulation support (UK AI Bill, India DPDP)
- [ ] OAuth2 / SSO support
- [ ] Stripe billing integration

> Open items are great contribution opportunities — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Contributing

We welcome contributions of all kinds — code, docs, tests, regulatory expertise.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide.

**Not sure where to start?** Browse issues labelled:
- [`good first issue`](https://github.com/SdSarthak/AegisAI/labels/good%20first%20issue) — beginner-friendly
- [`help wanted`](https://github.com/SdSarthak/AegisAI/labels/help%20wanted) — intermediate
- [`high priority`](https://github.com/SdSarthak/AegisAI/labels/high%20priority) — advanced / impactful

---

## License

AegisAI is licensed under **AGPL-3.0-only**.

- Free for open-source and self-hosted use.
- If you run a modified version as a SaaS, you must release your source code.
- For commercial licensing, contact the author.

Copyright (C) 2024 **Sarthak Doshi** ([@SdSarthak](https://github.com/SdSarthak))

---

<div align="center">
  <sub>Built with care. If AegisAI helps you, give it a star.</sub>
</div>
