from app.api.jobs import router as jobs_router
from app.api.videos import router as videos_router
from fastapi import APIRouter

ROUTERS = (jobs_router, videos_router)


def route_endpoint(path: str, method: str):
    api_path = path.removeprefix("/api")
    for router in ROUTERS:
        endpoint = _find_endpoint(router, api_path, method)
        if endpoint is not None:
            return endpoint
    raise AssertionError(f"Route {method} {path} not found")


def _find_endpoint(router: APIRouter, path: str, method: str):
    for route in router.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return getattr(route, "endpoint", None)
    return None


def test_expensive_job_routes_are_rate_limited():
    assert hasattr(route_endpoint("/api/jobs/{video_id}", "POST"), "__wrapped__")
    assert hasattr(route_endpoint("/api/jobs/{video_id}", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/jobs/{video_id}/cancel", "POST"), "__wrapped__")


def test_expensive_video_routes_are_rate_limited():
    assert hasattr(route_endpoint("/api/videos/{video_id}/slides/download", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/chat", "PUT"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/notes", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/notes/export", "POST"), "__wrapped__")
