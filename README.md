# 🌍 AI Travel Planner Agent

> A production-grade, AI-powered travel planning system built with **FastAPI**, **LangChain**, **LangGraph**, and **RAG** technology. Features enterprise-level **Role-Based Access Control (RBAC)** with Super Admin, Admin, and User tiers.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-orange.svg)](https://langchain-ai.github.io/langgraph/)
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
- [AI Agent](#ai-agent)
- [RAG Knowledge Base](#rag-knowledge-base)
- [Testing](#testing)
- [Docker Deployment](#docker-deployment)
- [GitHub Setup](#github-setup)
- [Project Structure](#project-structure)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Agent** | LangGraph-powered multi-step agent with intent routing |
| 📚 **RAG** | ChromaDB vector store with pre-loaded travel knowledge |
| 🔐 **RBAC** | Three-tier role system (Super Admin → Admin → User) |
| 🏗️ **FastAPI** | High-performance async API with auto Swagger docs |
| 🌤️ **Weather** | Real-time weather data via OpenWeatherMap |
| 💰 **Budget** | Intelligent cost estimation by region and tier |
| 🗓️ **Itinerary** | AI-generated day-by-day travel plans |
| 💱 **Currency** | Live exchange rates for 35+ currencies |
| 📱 **Multi-turn** | Session-based conversation memory |
| 🐳 **Docker** | Full containerization with docker-compose |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────┐
│            FastAPI Application               │
│  /auth  /superadmin  /admin  /agent         │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────▼────────────┐
    │   LangGraph Agent        │
    │  classify → rag →        │
    │  weather → budget →      │
    │  itinerary → synthesize  │
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────┐
    │  ChromaDB  │  SQLite     │
    │  (RAG)     │  (Data)     │
    └─────────────────────────┘
```

---

## 📦 Prerequisites

- **Python 3.11+**
- **Git**
- **pip** (Python package manager)
- **Google Gemini API Key** OR **OpenAI API Key**
- (Optional) OpenWeatherMap API Key
- (Optional) Docker Desktop

---

## 🚀 Installation

### Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/travel-planner-agent.git
cd travel-planner-agent
```

### Step 2 — Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ This installs ~500MB of packages including ML models. Allow 5-10 minutes.

---

## ⚙️ Configuration

### Step 4 — Set Up Environment Variables

```bash
# Copy the template
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux
```

Edit `.env` with your API keys:

```env
# REQUIRED: Choose one LLM provider
GOOGLE_API_KEY=your-google-gemini-api-key
# OR
OPENAI_API_KEY=your-openai-api-key
LLM_PROVIDER=google    # or openai

# REQUIRED: Change this secret key!
SECRET_KEY=your-random-32-char-secret-key-here

# OPTIONAL but recommended
OPENWEATHER_API_KEY=your-openweathermap-key
EXCHANGE_RATE_API_KEY=your-exchangerate-key

# Super admin credentials (auto-created on first run)
SUPER_ADMIN_EMAIL=superadmin@yourcompany.com
SUPER_ADMIN_PASSWORD=YourSecurePassword@123!
```

**Getting API Keys:**
- **Google Gemini**: https://aistudio.google.com/app/apikey (Free tier available)
- **OpenAI**: https://platform.openai.com/api-keys
- **OpenWeatherMap**: https://openweathermap.org/api (Free tier: 1000 calls/day)
- **ExchangeRate-API**: https://www.exchangerate-api.com/ (Free tier: 1500 calls/month)

---

## ▶️ Running the App

### Step 5 — Start the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
1. Auto-create database tables
2. Seed the super admin account
3. Start listening on http://localhost:8000

### Step 6 — Seed the RAG Knowledge Base (Recommended)

```bash
python scripts/seed_rag.py
```

This loads 8 comprehensive travel documents (destinations, budgeting, visa info, packing guides) into ChromaDB.

### Step 7 — View API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 📚 API Documentation

### Authentication

#### Login
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "superadmin@yourcompany.com",
  "password": "YourSecurePassword@123!"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "superadmin@yourcompany.com",
    "role": "super_admin"
  }
}
```

#### Use Token
Add to all authenticated requests:
```
Authorization: Bearer eyJ...your-access-token...
```

---

### Super Admin Endpoints

```bash
# Get system analytics
GET /superadmin/analytics

# List all admins
GET /superadmin/admins

# Create new admin
POST /superadmin/admins
{
  "email": "admin@company.com",
  "full_name": "John Smith",
  "password": "Admin@Pass123!"
}

# View specific admin's users
GET /superadmin/admins/{admin_id}/users

# Deactivate admin
PATCH /superadmin/admins/{admin_id}
{ "is_active": false }

# Delete admin
DELETE /superadmin/admins/{admin_id}
```

---

### Admin Endpoints

```bash
# List own users
GET /admin/users

# Create user under this admin
POST /admin/users
{
  "email": "user@company.com",
  "full_name": "Jane Doe",
  "password": "User@Pass123!"
}

# View user's travel history
GET /admin/users/{user_id}/trips

# Update/deactivate user
PATCH /admin/users/{user_id}
{ "is_active": false }
```

---

### AI Agent Endpoints

```bash
# Start a new conversation
POST /agent/chat
{
  "message": "Plan a 7-day trip to Japan for 2 people with a mid-range budget"
}

# Continue existing session
POST /agent/chat
{
  "message": "Add more temple visits to day 3",
  "session_id": 42
}

# List all conversations
GET /agent/sessions

# Get full conversation history
GET /agent/sessions/{session_id}

# List saved travel plans
GET /agent/trips

# Get specific travel plan
GET /agent/trips/{trip_id}
```

---

## 🔐 Role-Based Access Control

### Role Hierarchy

```
SUPER ADMIN
├── Full system control
├── Create/manage all admins
├── View all users across all admins
├── Global analytics dashboard
└── Endpoints: /superadmin/* + /admin/* + /agent/*

ADMIN
├── Manage only their own users
├── Create users assigned to themselves
├── View their users' travel plans
└── Endpoints: /admin/* + /agent/*

USER
├── Use the AI travel planner
├── View own conversations and trips
└── Endpoints: /agent/* + /auth/*
```

### Key RBAC Design Decision
Admin isolation is enforced **at the ORM query level**, not just API middleware. Even if an admin somehow bypasses authentication, the SQL query will never return data belonging to other admins. This prevents cross-admin data leakage.

---

## 🤖 AI Agent

The LangGraph agent processes messages through these sequential nodes:

```
User Message
    ↓
1. Classify Intent
   (itinerary_planning | budget_estimation | weather_info | destination_research)
    ↓
2. RAG Retrieval
   (Search ChromaDB knowledge base)
    ↓
3. Weather Tool
   (OpenWeatherMap API or intelligent fallback)
    ↓
4. Budget Estimator
   (Region-aware cost breakdown)
    ↓
5. Itinerary Builder
   (LLM-generated day-by-day plan as JSON)
    ↓
6. Synthesize Response
   (Format everything into a polished response)
    ↓
Saved to Database + Returned to User
```

### Example Conversations

```
User: "Plan a 5-day trip to Bali for 2 people"
Agent: Generates itinerary, budget ($80-150/day mid-range), weather info,
       packing tips, and saves it as a travel plan.

User: "What's the best time to visit Japan?"
Agent: Retrieves from RAG + adds current weather context.

User: "Convert 500 USD to Thai Baht"
Agent: Returns live or cached exchange rate.
```

---

## 📚 RAG Knowledge Base

The system includes pre-loaded knowledge about:
- 🗺️ Paris, Bali, Japan (Tokyo/Kyoto/Osaka), Dubai, Thailand
- 💰 Budget planning guide
- 📋 Visa requirements overview
- 🎒 Packing guides for all climates

### Adding Custom Documents

```bash
# Via API (Admin+)
POST /rag/upload
Content-Type: multipart/form-data
file: your_document.pdf

# Via script
python scripts/seed_rag.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage report
pytest --cov=app --cov-report=html
```

---

## 🐳 Docker Deployment

```bash
# Build and start
cd docker
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

Access: http://localhost:8000/docs

---

## 📤 GitHub Setup

### Step 1 — Initialize Git Repository

```bash
cd "c:\Users\Ahamed Najah\Desktop\Artificizen\Travel Planner Agent"
git init
git add .
git commit -m "feat: initial commit — AI Travel Planner Agent with RBAC"
```

### Step 2 — Create GitHub Repository

1. Go to https://github.com/new
2. Name: `travel-planner-agent`
3. Description: `AI Travel Planner with FastAPI, LangGraph, RAG, and RBAC`
4. Set to **Public** or **Private**
5. Do NOT initialize with README (we have one)
6. Click **Create repository**

### Step 3 — Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/travel-planner-agent.git
git branch -M main
git push -u origin main
```

### Step 4 — Set Up GitHub Secrets (for CI/CD)

In GitHub → Settings → Secrets → Actions:
- `GOOGLE_API_KEY`
- `SECRET_KEY`
- `OPENWEATHER_API_KEY`

### Step 5 — Future Updates

```bash
git add .
git commit -m "feat: add new destination to RAG knowledge base"
git push origin main
```

---

## 📁 Project Structure

```
travel-planner-agent/
│
├── app/
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/routes/
│   │   ├── auth.py                # Login, refresh, me
│   │   ├── superadmin.py          # Super admin CRUD + analytics
│   │   ├── admin.py               # Admin user management
│   │   └── agent.py               # AI chat + travel plans
│   │
│   ├── agent/
│   │   ├── graph.py               # LangGraph agent definition
│   │   ├── llm.py                 # LLM factory (Gemini/OpenAI)
│   │   └── tools/
│   │       ├── weather.py         # OpenWeatherMap integration
│   │       ├── budget.py          # Budget estimation
│   │       ├── itinerary.py       # Day-by-day plan generator
│   │       └── currency.py        # Currency converter
│   │
│   ├── core/
│   │   ├── config.py              # Pydantic settings
│   │   ├── database.py            # SQLAlchemy async engine
│   │   ├── security.py            # JWT + bcrypt + RBAC guards
│   │   └── logging.py             # Loguru configuration
│   │
│   ├── models/
│   │   ├── user.py                # User + UserRole ORM
│   │   ├── chat.py                # ChatSession + Message ORM
│   │   └── travel.py              # TravelPlan ORM
│   │
│   ├── schemas/
│   │   ├── user.py                # User Pydantic schemas
│   │   ├── chat.py                # Chat schemas
│   │   └── travel.py              # Travel plan schemas
│   │
│   └── rag/
│       └── retriever.py           # ChromaDB RAG pipeline
│
├── scripts/
│   └── seed_rag.py                # Load travel documents into RAG
│
├── tests/
│   └── test_auth.py               # Auth + RBAC test suite
│
├── docker/
│   ├── Dockerfile                 # Container definition
│   └── docker-compose.yml         # Multi-service compose
│
├── .env.example                   # Environment template
├── .gitignore
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 🔒 Security Checklist for Production

- [ ] Generate a strong `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Change default super admin password
- [ ] Set `DEBUG=False`
- [ ] Configure PostgreSQL instead of SQLite
- [ ] Set up HTTPS/SSL (use Nginx or Caddy as reverse proxy)
- [ ] Restrict `ALLOWED_ORIGINS` to your frontend domain
- [ ] Enable rate limiting (already implemented)
- [ ] Set up log monitoring (already configured with rotation)
- [ ] Never commit `.env` to Git

---

## 📞 Support

For issues, feature requests, or contributions:
1. Open an issue on GitHub
2. Submit a pull request
3. Check the `/docs` endpoint for interactive API testing

---

*Built with ❤️ using FastAPI + LangGraph + ChromaDB*
