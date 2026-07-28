def test_create_and_get_incident(client):
    create = client.post("/api/v1/incidents", json={"title": "Wildfire", "location": "West ridge"})

    assert create.status_code == 201
    incident_id = create.json()["id"]
    assert client.get(f"/api/v1/incidents/{incident_id}").json()["title"] == "Wildfire"


def test_unknown_incident_returns_standard_error(client):
    response = client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "not_found"
