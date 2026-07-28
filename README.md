# Sentinel AI

Sentinel AI is an emergency-response decision-support platform. It is designed to help commanders combine incident reports, visual analysis, available resources, and explainable planning; it does not autonomously dispatch emergency services.

## Milestone 1

This milestone establishes the production-oriented project foundation: Next.js frontend, FastAPI backend, PostgreSQL configuration, Alembic migrations, versioned API routing, repository and service layers, and health endpoints. It intentionally excludes AI agents, computer vision, allocation, severity, planning, and simulation logic.

## Run with Docker

1. Copy `.env.example` to `.env` and replace the database password.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`. The backend health endpoint is `http://localhost:8000/api/v1/health`.

## Run locally

Backend (Python 3.12):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend (Node 20+):

```powershell
cd frontend
npm install
npm run dev
```

Set `DATABASE_URL` for a locally reachable PostgreSQL database when running the backend outside Docker.

## Layout

- `backend/app`: API, application configuration, data access, services, future domain modules, and utilities.
- `frontend`: Next.js application shell and reusable UI primitives.
- `docs`: architecture and operating notes.
