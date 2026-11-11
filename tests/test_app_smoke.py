"""Smoke tests: the FastAPI application must import and expose its documented routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/" in paths
    assert "/train" in paths


def test_root_supports_get_and_post() -> None:
    root_methods = {
        method
        for route in app.routes
        if route.path == "/"
        for method in getattr(route, "methods", set())
    }

    assert {"GET", "POST"}.issubset(root_methods)


def test_openapi_schema_builds() -> None:
    schema = app.openapi()

    assert schema["info"]["title"]
    assert "/train" in schema["paths"]


def test_root_renders_the_application_form() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "US Visa Prediction" in response.text
    assert "Visa Prediction Status" in response.text


def test_static_stylesheet_is_served() -> None:
    response = client.get("/static/css/style.css")

    assert response.status_code == 200
