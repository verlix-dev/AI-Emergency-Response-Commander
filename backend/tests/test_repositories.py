from app.repositories import IncidentRepository


def test_incident_repository_persists_incident(session):
    incident = IncidentRepository(session).create({"title": "River overflow", "location": "North district"})

    assert IncidentRepository(session).get(incident.id).title == "River overflow"
