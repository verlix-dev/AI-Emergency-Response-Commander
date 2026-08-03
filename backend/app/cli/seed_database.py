"""Command-line entrypoint for populating the database with demonstration data.

Run from the backend directory:

    python -m app.cli.seed_database

The command creates any missing tables, applies the seed, and reports what it wrote. It is
idempotent: running it twice leaves the database unchanged the second time.
"""

import sys

from sqlalchemy import func, select

from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models.incident import Incident
from app.models.resource import Resource
from app.services.seed import SEED_CITIES, seed


def main() -> int:
    """Seed the configured database and print a summary of its contents."""
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        seed(session)
        session.commit()

        resource_total = session.scalar(select(func.count()).select_from(Resource)) or 0
        incident_total = session.scalar(select(func.count()).select_from(Incident)) or 0

        print(f"Resources : {resource_total}")
        print(f"Incidents : {incident_total}")
        print()
        print(f"{'City':<12}{'Units':>7}")
        for city in SEED_CITIES:
            name = str(city["name"])
            count = (
                session.scalar(
                    select(func.count())
                    .select_from(Resource)
                    .where(Resource.current_location == name)
                )
                or 0
            )
            print(f"{name:<12}{count:>7}")
    except Exception as exc:  # noqa: BLE001 - report failure to the operator, do not traceback
        session.rollback()
        print(f"Seeding failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
