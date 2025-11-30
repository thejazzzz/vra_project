# File: tests/test_research.py
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}




def test_research_endpoint():
    payload = {"query": "What is AI?"}
    r = client.post("/research/", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "success"
    assert body.get("data", {}).get("query") == payload["query"]