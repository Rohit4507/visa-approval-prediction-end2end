"""Smoke tests: the FastAPI application must import and expose its documented routes."""

from __future__ import annotations

from app import app


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
