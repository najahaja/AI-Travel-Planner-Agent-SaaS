# 🌍 AI Travel Planner Agent

> A production-grade, AI-powered travel planning system built with **FastAPI**, **LangChain**, **LangGraph**, and **RAG** technology. Features enterprise-level **Role-Based Access Control (RBAC)**, **Audit Logging**, and **PDF Itinerary Generation**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [API Documentation](#api-documentation)
- [Role-Based Access Control](#role-based-access-control)
- [AI Agent & Tools](#ai-agent--tools)
- [Audit Logs & Reports](#audit-logs--reports)
- [PDF Export](#pdf-export)
- [Testing & CI/CD](#testing--cicd)
- [Project Structure](#project-structure)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Agent** | LangGraph-powered multi-step agent with intent routing |
| 📚 **RAG** | ChromaDB vector store with pre-loaded travel knowledge |
| 🔐 **RBAC** | Three-tier role system (Super Admin → Admin → User) |
| 📝 **Audit Logs** | Complete trail of logins, AI chats, and exports |
| 📄 **PDF Export** | Professional day-by-day itineraries with budget tables |
| 📊 **Reports** | Usage statistics and analytics for administrators |
| 🌤️ **Weather** | Real-time weather data via OpenWeatherMap |
| 💰 **Budget** | Intelligent cost estimation by region and tier |
| 💱 **Currency** | Live exchange rates for 35+ currencies |
| 📱 **Multi-turn** | Session-based conversation memory |
| 🚀 **CI/CD** | GitHub Actions for automated testing and linting |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Application                     │
│  /auth  /superadmin  /admin  /agent  /reports  /export  │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   LangGraph Agent       │
         │  classify → rag →       │
         │  weather → budget →     │
         │  itinerary → synthesize │
         └────────────┬────────────┘
                      │
         ┌────────────▼──────────────┐
         │  ChromaDB  │  SQLite/Postgres│
         │  (RAG)     │  (Data/Logs)    │
         └───────────────────────────┘
```

---

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **Git**
- **Groq API Key** (Primary LLM)
- (Optional) OpenWeatherMap & ExchangeRate API Keys

---

## 🚀 Installation

### Step 1 — Clone & Virtual Env
```bash
git clone https://github.com/YOUR_USERNAME/travel-planner-agent.git
cd travel-planner-agent

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 2 — Install Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Step 3 — Set Up Environment Variables
```bash
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux
```

Edit `.env` with your credentials:
```env
# REQUIRED
GOOGLE_API_KEY=your-api-key
SECRET_KEY=your-32-char-random-string

# OPTIONAL
OPENWEATHER_API_KEY=your-key
EXCHANGE_RATE_API_KEY=your-key

# Super Admin Default
SUPER_ADMIN_EMAIL=superadmin@travelplanner.com
SUPER_ADMIN_PASSWORD=SuperAdmin@2025!
```

---

### Step 4 — Start Backend
```bash
uvicorn app.main:app --reload
```
*Auto-creates tables and seeds super admin on first run.*

### Step 4b — Start Frontend
```bash
cd frontend
npm install
npm run dev
```
*Default frontend: http://localhost:5173*

### Step 5 — Seed Knowledge Base
```bash
python scripts/seed_rag.py
```

### Step 6 — Access Docs
- **Swagger**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 🔐 Role-Based Access Control

- **Super Admin**: System-wide control, manage all admins, view all logs.
- **Admin**: Manage own users, view own users' trips and logs.
- **User**: Chat with AI, save travel plans, export PDFs.

*Isolation is enforced at the database level to prevent data leakage.*

---

## 📝 Audit Logs & Reports

Every significant action is recorded for security and analytics:
- **Audit Logs**: `GET /reports/audit-logs` (Filter by action, user, or status).
- **Usage Stats**: `GET /reports/usage-stats?days=7` (Total chats, trips, exports, active users).

---

## 📄 PDF Export

Users can download their travel plans as professional, branded PDF documents:
- **Endpoint**: `GET /export/trips/{trip_id}/pdf`
- **Includes**: Destination header, Budget Summary Table, Day-by-Day Activities, Meals, Packing Tips.

---

## 🤖 AI Agent & Tools

The agent uses a **LangGraph** state machine to orchestrate:
1. **RAG**: Searches the vector store for travel guides.
2. **Weather**: Fetches current/seasonal weather.
3. **Budget**: Calculates daily costs based on traveler count and tier.
4. **Itinerary**: Generates a structured JSON plan.
5. **Currency**: Converts costs to the user's preferred currency.

---

## 🧪 Testing & CI/CD

```bash
# Run tests
pytest -v

# Run linter
ruff check app/
```

**GitHub Actions**: The `.github/workflows/ci.yml` file ensures that every push to `main` or `develop` is automatically tested and linted.

---

## 🛠️ Challenges Faced & Solutions

During development, several technical hurdles were overcome to ensure a production-grade experience:

1. **Database Schema Evolution**: Mid-development, we transitioned to a session-based model which required adding `session_id` to the existing SQLite `travel_plans` table. We implemented a custom migration script to ensure no data loss during this transition.
2. **PDF Generation Constraints**: Generating professional PDFs in a serverless-ready environment required careful handling of the `reportlab` library and ensuring it was robust against `null` values returned from AI estimations.
3. **Multi-Tenant Isolation**: Ensuring that Admins can only see *their* users while Super Admins see *all* data required complex SQLAlchemy join queries and role-aware API routing.
4. **LLM Rate Limiting**: To prevent API abuse and cost overruns with Groq, we integrated `slowapi` to enforce a 20 requests/minute limit on the chat endpoint.
5. **Real-time State Management**: Managing the synchronization between the React frontend and the LangGraph backend state (especially for itinerary updates) required a robust polling and session management strategy.

---

## 📁 Project Structure

```
travel-planner-agent/
├── app/
│   ├── api/routes/      # Auth, Admin, Agent, Reports, Export
│   ├── agent/           # LangGraph + Tools (Weather, Budget, etc)
│   ├── core/            # Config, Security, DB, Logging
│   ├── models/          # User, Chat, Travel, AuditLog
│   ├── services/        # Audit service, PDF export service
│   └── rag/             # ChromaDB retrieval pipeline
├── scripts/             # Data seeding
├── tests/               # Pytest suite + conftest
└── .github/workflows/   # CI/CD
```

---

*Built for Enterprise Travel Planning — 2026*
