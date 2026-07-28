def test_invalid_incident_request_returns_standard_validation_error(client):
    response = client.post("/api/v1/incidents", json={"title": "", "location": ""})

    assert response.status_code == 422
    assert response.json() == {"success": False, "error": {"code": "validation_error", "message": "Request validation failed."}}
