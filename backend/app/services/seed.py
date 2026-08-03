"""Seed data for realistic demonstrations.

Each city carries a resource pool proportional to its population and hazard profile, plus a
handful of historical incidents that exercise the decision pipeline against plausible scenarios.

This module is idempotent: running it against an existing database skips records already
present rather than duplicating them, so it is safe for startup or before demos.
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.models.resource import Resource

SEED_CITIES: list[dict[str, object]] = [
    {
        "name": "Delhi",
        "lat": 28.6139,
        "lon": 77.2090,
        "fire_trucks": 18,
        "ambulances": 24,
        "police": 30,
        "search_rescue": 8,
        "boats": 2,
        "medical_teams": 12,
        "hazmat": 4,
        "heavy_machinery": 8,
    },
    {
        "name": "Mumbai",
        "lat": 19.0760,
        "lon": 72.8777,
        "fire_trucks": 22,
        "ambulances": 28,
        "police": 35,
        "search_rescue": 10,
        "boats": 6,
        "medical_teams": 14,
        "hazmat": 5,
        "heavy_machinery": 10,
    },
    {
        "name": "Bengaluru",
        "lat": 12.9716,
        "lon": 77.5946,
        "fire_trucks": 14,
        "ambulances": 18,
        "police": 24,
        "search_rescue": 6,
        "boats": 2,
        "medical_teams": 10,
        "hazmat": 3,
        "heavy_machinery": 6,
    },
    {
        "name": "Chennai",
        "lat": 13.0827,
        "lon": 80.2707,
        "fire_trucks": 16,
        "ambulances": 20,
        "police": 26,
        "search_rescue": 8,
        "boats": 8,
        "medical_teams": 10,
        "hazmat": 4,
        "heavy_machinery": 7,
    },
    {
        "name": "Hyderabad",
        "lat": 17.3850,
        "lon": 78.4867,
        "fire_trucks": 12,
        "ambulances": 16,
        "police": 20,
        "search_rescue": 5,
        "boats": 2,
        "medical_teams": 8,
        "hazmat": 3,
        "heavy_machinery": 5,
    },
    {
        "name": "Kolkata",
        "lat": 22.5726,
        "lon": 88.3639,
        "fire_trucks": 16,
        "ambulances": 22,
        "police": 28,
        "search_rescue": 7,
        "boats": 5,
        "medical_teams": 11,
        "hazmat": 4,
        "heavy_machinery": 8,
    },
]

SEED_INCIDENTS: list[dict[str, object]] = [
    {
        "title": "Warehouse Fire — Okhla Industrial Area",
        "incident_type": "BUILDING_FIRE",
        "status": IncidentStatus.RESOLVED,
        "priority": "HIGH",
        "location": "Delhi",
        "latitude": 28.51,
        "longitude": 77.28,
        "description": "Plastics warehouse fire. 12 workers evacuated, 3 with smoke inhalation. Fire contained after 4 hours.",
        "offset_hours": 72,
    },
    {
        "title": "Chemical Spill — Trombay Industrial Zone",
        "incident_type": "CHEMICAL_LEAK",
        "status": IncidentStatus.RESOLVED,
        "priority": "CRITICAL",
        "location": "Mumbai",
        "latitude": 19.00,
        "longitude": 72.95,
        "description": "Chlorine cylinder valve failure at water treatment plant. 2 casualties, 50 residents evacuated from 300 m radius. Leak isolated after 90 minutes.",
        "offset_hours": 60,
    },
    {
        "title": "Flash Flood — Mylapore Underpass",
        "incident_type": "FLOOD",
        "status": IncidentStatus.RESOLVED,
        "priority": "HIGH",
        "location": "Chennai",
        "latitude": 13.04,
        "longitude": 80.27,
        "description": "Underpass flooded to 1.8 m after 140 mm rainfall in 3 hours. 3 vehicles submerged, 5 people rescued by boat. Water pumped out over 5 hours.",
        "offset_hours": 48,
    },
    {
        "title": "Building Collapse — Shivaji Nagar",
        "incident_type": "BUILDING_COLLAPSE",
        "status": IncidentStatus.RESOLVED,
        "priority": "CRITICAL",
        "location": "Bengaluru",
        "latitude": 12.99,
        "longitude": 77.60,
        "description": "Three-storey residential building collapsed during renovation. 8 trapped, 6 rescued alive across 18 hours of USAR operations. 2 fatalities.",
        "offset_hours": 36,
    },
    {
        "title": "Multi-Vehicle Collision — NH-44 Bypass",
        "incident_type": "ROAD_ACCIDENT",
        "status": IncidentStatus.RESOLVED,
        "priority": "HIGH",
        "location": "Hyderabad",
        "latitude": 17.45,
        "longitude": 78.51,
        "description": "Four-vehicle collision including one fuel tanker. 7 casualties, 2 trapped requiring extrication. Diesel spill contained before reaching drainage.",
        "offset_hours": 24,
    },
    {
        "title": "Cyclone Damage Assessment — Salt Lake",
        "incident_type": "CYCLONE_STORM",
        "status": IncidentStatus.RESPONDING,
        "priority": "HIGH",
        "location": "Kolkata",
        "latitude": 22.58,
        "longitude": 88.42,
        "description": "Post-cyclone assessment across Sector V and Salt Lake. 40 trees down, 6 roads blocked, power lines compromised in 3 locations. No casualties reported. 200 residents sheltering in place.",
        "offset_hours": 12,
    },
    {
        "title": "Earthquake — Rohini Sector 8",
        "incident_type": "EARTHQUAKE",
        "status": IncidentStatus.RESPONDING,
        "priority": "SEVERE",
        "location": "Delhi",
        "latitude": 28.72,
        "longitude": 77.10,
        "description": "M5.8 earthquake, depth 15 km. Two apartment blocks with visible structural damage, 15 casualties reported, gas leak suspected in one building. USAR teams mobilised.",
        "offset_hours": 6,
    },
    {
        "title": "Train Derailment — CST Suburban Platform",
        "incident_type": "TRAIN_ACCIDENT",
        "status": IncidentStatus.PLANNED,
        "priority": "CRITICAL",
        "location": "Mumbai",
        "latitude": 18.94,
        "longitude": 72.84,
        "description": "Suburban local overshot platform. 4 carriages derailed at low speed. 30 walking wounded, 8 casualties requiring hospital transfer. Traction power isolated. Adjacent line blocked.",
        "offset_hours": 3,
    },
]

_today = datetime.now(timezone.utc)


def _resource_name(city: str, kind: str, index: int) -> str:
    """Build a readable, sortable unit name like 'DEL Fire Engine 5'."""
    label = kind.replace("_", " ").title()
    return f"{city[:3].upper()} {label} {index}"


def seed(session: Session) -> None:
    """Populate resources for every known city, then any historical incidents still absent.

    Both skip existing rows so the call is idempotent.
    """
    if session.query(Resource).first() is not None:
        return

    for city in SEED_CITIES:
        name = str(city["name"])
        for kind, count in [
            ("fire_truck", city["fire_trucks"]),
            ("ambulance", city["ambulances"]),
            ("police", city["police"]),
            ("search_rescue", city["search_rescue"]),
            ("boat", city["boats"]),
            ("medical_team", city["medical_teams"]),
            ("hazmat", city["hazmat"]),
            ("heavy_machinery", city["heavy_machinery"]),
        ]:
            for index in range(1, int(count) + 1):
                session.add(
                    Resource(
                        resource_type=kind,
                        resource_name=_resource_name(name, kind, index),
                        status="AVAILABLE",
                        current_location=name,
                        available=True,
                    )
                )
    session.flush()

    if session.query(Incident).first() is not None:
        return

    for incident in SEED_INCIDENTS:
        offset_hours = int(incident.get("offset_hours", 0))
        created = _today - timedelta(hours=offset_hours)
        session.add(
            Incident(
                title=str(incident["title"]),
                description=str(incident.get("description", "")),
                incident_type=str(incident["incident_type"]),
                status=IncidentStatus(incident["status"]),
                priority=str(incident["priority"]),
                location=str(incident["location"]),
                latitude=float(incident.get("latitude", 0)),
                longitude=float(incident.get("longitude", 0)),
                created_at=created,
                updated_at=created,
            )
        )
    session.flush()
