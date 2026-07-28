# Sentinel AI

Sentinel AI is an emergency-response decision-support platform. It is designed to help commanders combine incident reports, visual analysis, available resources, and explainable planning; it does not autonomously dispatch emergency services.

## Milestone 1

This milestone establishes the ARES backend core infrastructure: environment configuration, database plumbing, Alembic setup, vendor-neutral LLM abstractions, structured logging, middleware, exception handling, OpenAPI configuration, and a health endpoint. It intentionally excludes database models, CRUD, repositories, business logic, AI providers, and operational decision engines.

## Run locally

Backend (Python 3.10):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload
```

Frontend (Node 20+):

```powershell
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and provide every required environment value before starting the API.

## Layout

- `backend/app`: API, application configuration, data access, services, future domain modules, and utilities.
- `frontend`: Next.js application shell and reusable UI primitives.
- `docs`: architecture and operating notes.
