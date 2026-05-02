# C2D2 — Combat Decision Dominance

AI-Powered Force Intelligence Platform · Army FUZE xTech / National Security Hackathon

## Overview

C2D2 is a three-phase decision-support system for battalion-level commanders:

| Phase | Capability |
|-------|------------|
| **01 — Data Capture** | OCR whiteboard photos, speech-to-text voice logs, AI leadership scoring, soldier skill profiles |
| **02 — Team Optimizer** | Mission-type-specific ML team selection, explainable rationale, commander retains final authority |
| **03 — Adversarial Co-Pilot** | Live battlespace simulation, adversary move modeling, risk vectors, adaptive recommendations |

## Stack

- **Backend**: FastAPI 0.115 · SQLAlchemy 2 · SQLite (dev) / PostgreSQL (prod) · PyJWT · bcrypt
- **AI**: Anthropic Claude (`claude-sonnet-4-6`) · OpenAI Whisper (`whisper-1`)
- **Frontend**: Next.js 15 · React 19 · TypeScript · Tailwind CSS · Recharts
- **Deployment**: Docker · Azure Container Registry · Azure App Service

## Quick Start (Local)

### 1. Backend

```bash
cd "Battalion eval"
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and OPENAI_API_KEY

uvicorn backend.app.main:app --reload --port 8000
```

The database (`c2d2.db`) is created automatically on first run. An admin account is seeded:
- **Email**: `admin@c2d2.local`
- **Password**: `changeme123`

### 2. Seed Demo Data

```bash
source venv/bin/activate
python scripts/seed_demo_data.py
```

Seeds 9 soldiers across Alpha/Bravo/Charlie Co, 3 training events, 1 demo mission, and 1 battlespace session.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # starts on port 3000
```

Open [http://localhost:3000](http://localhost:3000) and log in with the admin credentials above.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./c2d2.db` | SQLite for local dev; set PostgreSQL URL for prod |
| `ANTHROPIC_API_KEY` | — | Required for AI scoring, OCR, team rationale, adversarial sim |
| `OPENAI_API_KEY` | — | Required for speech-to-text (Whisper) |
| `JWT_SECRET` | `change-me-in-production` | Sign JWT tokens — change in prod |
| `JWT_EXPIRE_HOURS` | `24` | Token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `NEXT_PUBLIC_API_URL` | *(empty — uses same host)* | Override API base URL in frontend |

## API Endpoints

All routes require `Authorization: Bearer <token>` except `/api/v1/auth/login`.

```
POST   /api/v1/auth/login                     Login
GET    /api/v1/auth/me                         Current user

GET    /api/v1/soldiers                        List soldiers
POST   /api/v1/soldiers                        Create soldier
GET    /api/v1/soldiers/{id}                   Soldier detail + assessment history
PATCH  /api/v1/soldiers/{id}                   Update soldier

GET    /api/v1/events                          List training events
POST   /api/v1/events                          Create event

POST   /api/v1/assessments                     Manual entry + AI scoring
POST   /api/v1/assessments/capture/ocr         Photo upload → OCR → AI scoring
POST   /api/v1/assessments/capture/stt         Audio upload → Whisper → AI scoring

GET    /api/v1/missions                        List missions
POST   /api/v1/missions                        Create mission
POST   /api/v1/missions/{id}/optimize-team     Run team optimizer (3 ranked compositions)
POST   /api/v1/missions/{id}/select-team/{cid} Commander selects final team

GET    /api/v1/battlespace                     List battlespace sessions
POST   /api/v1/battlespace                     Create session
GET    /api/v1/battlespace/{id}                Session detail
POST   /api/v1/battlespace/{id}/simulate-adversary  Run adversarial AI
```

## Docker / Production

```bash
docker compose up --build
```

The compose file runs FastAPI on port 8000 and Next.js on port 3000 with SQLite by default. Set `DATABASE_URL` to a PostgreSQL connection string for production.

For Azure:

```bash
az acr build --registry <your-acr> --image c2d2:latest .
az webapp create --resource-group <rg> --plan <plan> --name c2d2 \
  --deployment-container-image-name <your-acr>.azurecr.io/c2d2:latest
```

## Without API Keys

The system runs in **demo mode** without API keys — AI scoring returns synthetic mid-range scores, team rationale uses a template, and adversarial simulation returns a canned scenario. All UI flows are fully exercisable.
