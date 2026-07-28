import os

os.environ.update(
    {
        "APP_NAME": "ARES API",
        "APP_VERSION": "1.0.0",
        "ENVIRONMENT": "development",
        "API_V1_PREFIX": "/api/v1",
        "DATABASE_URL": "postgresql+psycopg://ares:ares@localhost:5432/ares",
        "LLM_PROVIDER": "",
        "LLM_MODEL": "",
        "LLM_API_KEY": "",
        "UPLOAD_DIRECTORY": "uploads",
        "LOG_LEVEL": "INFO",
        "DEBUG": "false",
        "MAX_UPLOAD_SIZE": "1",
        "CORS_ORIGINS": "[\"http://localhost:3000\"]",
        "TRUSTED_HOSTS": "[\"testserver\"]",
    }
)

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0", "environment": "development"}
