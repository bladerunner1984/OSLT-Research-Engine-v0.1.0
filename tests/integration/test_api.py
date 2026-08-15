from fastapi.testclient import TestClient

from oslt_research.api.app import app


def test_health_constitution_registries_and_preflight():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        constitution = client.get("/constitution")
        assert constitution.status_code == 200
        assert "counterevidence_lanes_required" in constitution.json()["rules"]
        registries = client.get("/registries/summary").json()
        assert registries["valid"] is True
        assert registries["counts"]["variables.csv"] == 640
        assert client.get("/preflight").json()["passed"] is True


def test_sample_envelope_endpoint():
    with TestClient(app) as client:
        response = client.post(
            "/sample-size/envelope",
            json={
                "available_n": 1000,
                "effective_parameters": 10,
                "outcome_events": 200,
                "design_effect": 1.0,
                "attrition_fraction": 0.1,
            },
        )
        assert response.status_code == 200
        assert response.json()["effective_n"] == 900.0
