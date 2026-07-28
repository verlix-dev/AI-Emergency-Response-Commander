from app.repositories import IncidentRepository
from app.schemas.entities import IncidentCreateSchema
from app.services import IncidentService


def test_incident_service_creates_incident(session):
    incident = IncidentService(IncidentRepository(session)).create(IncidentCreateSchema(title="Bridge collapse", location="Route 7"))

    assert incident.location == "Route 7"
