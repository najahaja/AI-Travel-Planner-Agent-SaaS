# 🌍 AI Travel Planner Agent — Professional System Plan

## 1. Executive Overview

A production-grade, AI-powered Travel Planner platform built with **FastAPI**, **LangChain**, and **LangGraph**. The system features a conversational AI agent enhanced with **Retrieval-Augmented Generation (RAG)** for accurate travel recommendations, backed by a secure **Role-Based Access Control (RBAC)** system with three tiers: **Super Admin → Admin → User**.

---

## 2. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| **API Framework** | FastAPI | High performance, async, auto Swagger docs |
| **AI Orchestration** | LangGraph | Stateful multi-step agent workflows |
| **LLM Integration** | LangChain | Tool chaining, memory, prompt management |
| **RAG / Vector Store** | ChromaDB + HuggingFace Embeddings | Local, fast, no cloud dependency |
| **LLM Provider** | Google Gemini / OpenAI (configurable) | Best-in-class responses |
| **Database** | SQLite (dev) → PostgreSQL (prod) via SQLAlchemy | RBAC + chat history |
| **Auth** | JWT (OAuth2 Bearer) + bcrypt | Secure, stateless |
| **External APIs** | OpenWeatherMap, Amadeus / Skyscanner (flights), Unsplash | Real data |
| **Testing** | Pytest + httpx | Full coverage |

---

## 3. Role-Based Access Control (RBAC)

```
SUPER ADMIN
├── Can view ALL admins
├── Can view ALL users under any admin
├── Can create / suspend / delete admins
├── Can assign users to admins
├── Has global analytics dashboard

ADMIN (each admin is isolated)
├── Can view ONLY their own users
├── Can create users under themselves
├── Can view users' travel plans & chat history
├── Cannot see other admins or their users

USER
├── Belongs to exactly ONE admin
├── Can use the Travel Planner Agent (chat)
├── Can view their own trips & history
└── Cannot access any admin features
```

---

## 4. System Architecture

```
FastAPI Backend
├── Auth APIs
├── Admin APIs (role-scoped)
├── User APIs
└── Agent APIs

LangGraph Agent Engine
├── Router Node
├── RAG Tool Node
├── Web Search Tool
├── Itinerary Planner Node
├── Weather Tool
└── Budget Estimator

Storage
├── ChromaDB (RAG Vector Store)
└── SQLAlchemy ORM (Users, Roles, Trips, Chat)
```

---

## 5. LangGraph Agent Workflow

```
User Message → Classify Intent → Intent Router
    ├── Itinerary Planning
    ├── Budget Estimation
    ├── Weather Info
    └── RAG Search
         └── Synthesize → Format Response → Save to DB → Return
```

---

## 6. Database Schema

```sql
users          (id, email, password_hash, full_name, role, admin_id, is_active, created_at)
chat_sessions  (id, user_id, title, created_at)
messages       (id, session_id, role, content, timestamp)
travel_plans   (id, user_id, destination, start_date, end_date, itinerary_json, budget_json)
rag_documents  (id, title, source, content, metadata_json)
```

---

## 7. API Endpoints

### Authentication
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout

### Super Admin
- GET /superadmin/admins
- POST /superadmin/admins
- DELETE /superadmin/admins/{id}
- GET /superadmin/admins/{id}/users
- GET /superadmin/analytics

### Admin
- GET /admin/users
- POST /admin/users
- DELETE /admin/users/{id}
- GET /admin/users/{id}/trips

### User / Agent
- POST /agent/chat
- GET /agent/sessions
- GET /agent/sessions/{id}
- GET /agent/trips

---

## 8. AI Agent Features

1. Smart Itinerary Builder (day-by-day plans)
2. Budget Estimator (flights, hotels, food, activities)
3. Weather Advisor (best time to visit, packing tips)
4. RAG Knowledge Base (500+ travel guides, visa info)
5. Multi-turn Memory (session context)
6. Currency Converter (live rates)
7. Hotel Recommendations (budget/mid/luxury tiers)

---

## 9. Implementation Phases

### Phase 1 — Foundation
- Project structure & dependencies
- Database models & Alembic migrations
- JWT Auth + RBAC middleware
- Super Admin, Admin, User APIs

### Phase 2 — AI Agent
- LangGraph agent graph
- Tool nodes (weather, budget, itinerary)
- RAG pipeline + seed documents
- Chat session management

### Phase 3 — External Integrations
- OpenWeatherMap API
- Currency exchange API
- Unsplash image API

### Phase 4 — Polish & Production
- Error handling & logging
- Rate limiting
- Pytest test suite
- Docker + docker-compose
- README + GitHub guide

---

## 10. Security

- bcrypt password hashing
- JWT with expiry + refresh rotation
- Admin isolation at ORM query level
- Rate limiting on /agent/chat
- CORS configured
- .env for all secrets
