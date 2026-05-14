# 🌍 AI Travel Planner Agent — Complete Project Overview

## 1. Executive Overview

A production-grade, AI-powered Travel Planner platform built with **FastAPI**, **LangChain**, and **LangGraph**. The system features a conversational AI agent powered exclusively by **Groq (`llama-3.1-8b-instant`)**, enhanced with **Retrieval-Augmented Generation (RAG)** for accurate travel recommendations, and backed by a secure **Role-Based Access Control (RBAC)** system.

---

## 2. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| **API Framework** | FastAPI | High performance, async, auto Swagger docs |
| **AI Orchestration** | LangGraph | Stateful multi-step agent workflows |
| **LLM Integration** | LangChain | Tool chaining, memory, prompt management |
| **RAG / Vector Store** | ChromaDB + HuggingFace Embeddings | Local, fast, no cloud dependency |
| **LLM Provider** | Groq (Llama 3.1 8B) | Ultra-fast inference, high reasoning quality |
| **Database** | SQLite (Async via `aiosqlite`) | Lightweight, async compatible |
| **Auth** | JWT (OAuth2 Bearer) + bcrypt | Secure, stateless |
| **External APIs** | OpenWeatherMap, Google Places API (New) | Live data |

---

## 3. LangGraph Agent Workflow

The agent uses a stateful 7-node graph (`app/agent/graph.py`):
```text
User Message → Classify Intent
    ├── Intent: Greeting → Synthesize Response
    └── Intent: Other → RAG Retrieval
          ├── Intent: Weather → Weather Node → Synthesize
          ├── Intent: Destination Research → Places Node → Synthesize
          └── Intent: Planning → Weather Node → Places Node → Budget Node → Itinerary Node → Synthesize
```

---

## 4. Role-Based Access Control (RBAC)

- **SUPER ADMIN:** Global visibility. Can manage all Admins and view overall analytics.
- **ADMIN:** Tenant isolation. Can view and manage only their own Users and view those Users' trips.
- **USER:** End-user. Can chat with the Agent, plan trips, view their own trips, and export PDFs.

---

## 5. System Architecture & File Structure

```text
travel-planner-agent/
├── app/
│   ├── main.py                   ← FastAPI entry point
│   ├── api/routes/               ← Auth, Admin, Agent, Reports, Export APIs
│   ├── agent/                    
│   │   ├── graph.py              ← LangGraph workflow
│   │   ├── llm.py                ← Groq API integration
│   │   └── tools/                ← Weather, Budget, Itinerary, Places, Currency
│   ├── core/                     ← Config, DB, Security, Logging
│   ├── models/                   ← SQLAlchemy ORM Models (User, Chat, Travel, AuditLog)
│   ├── rag/retriever.py          ← ChromaDB Retrieval
│   └── services/                 ← Audit, PDF Export
├── scripts/seed_rag.py           ← Populates vector store
├── docker/                       ← Dockerfile & docker-compose
├── .env                          ← Environment variables
└── requirements.txt              ← Python dependencies
```

---

## 6. Setup & Run Guide

### STEP 1 — Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### STEP 2 — Configure Environment
Ensure your `.env` contains:
```env
SECRET_KEY=your-32-char-secret
GROQ_API_KEY=your-groq-key
GOOGLE_PLACES_API_KEY=your-google-places-key
OPENWEATHER_API_KEY=your-openweather-key
```

### STEP 3 — Start the Server
```bash
uvicorn app.main:app --reload
```
*Note: On first run, it automatically creates database tables and the Super Admin account.*

### STEP 4 — Access the Platform
- **Swagger UI:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

---

## 7. Key Features & Highlights

1. **Groq-Powered Intelligence:** Exclusively utilizing `llama-3.1-8b-instant` for lightning-fast responses and advanced itinerary generation.
2. **Live Google Places:** Direct integration with Google Places API (New) for fetching up-to-date attractions, reviews, and addresses.
3. **Enterprise RBAC:** Multi-tenant architecture isolated at the ORM query level.
4. **Audit Logging & PDF Export:** Full accountability trail and branded PDF itinerary generation.
5. **Multi-Turn Memory:** Context-aware conversations maintaining state across node executions.
