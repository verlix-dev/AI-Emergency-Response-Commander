# Architecture — Milestone 1

The frontend and backend are independently deployable services. The browser calls only versioned HTTP endpoints under `/api/v1`. FastAPI routes are kept thin; application concerns are organized into dedicated service, database, agent, planner, prompt, and vision packages as the platform grows.

PostgreSQL is the system of record. SQLAlchemy owns the ORM metadata, Alembic owns schema evolution, and FastAPI dependencies provide database sessions to request handlers. The initial migration creates no domain tables; later milestones will add those through explicit revisions.

Runtime configuration is read from environment variables through Pydantic settings. Docker Compose supplies a local PostgreSQL instance and starts the backend only after the database is healthy.
