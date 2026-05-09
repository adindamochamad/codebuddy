"""Uji endpoint kesehatan dasar."""

from fastapi.testclient import TestClient


def test_health_ok(klien_http: TestClient) -> None:
    respons = klien_http.get("/health")
    assert respons.status_code == 200
    muatan = respons.json()
    assert muatan.get("status") == "ok"


def test_root_docs_pointer(klien_http: TestClient) -> None:
    respons = klien_http.get("/")
    assert respons.status_code == 200
    assert "docs" in respons.json()
