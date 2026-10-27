from app.main import app


def route_endpoint(path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            endpoint = getattr(route, "endpoint", None)
            if endpoint is not None:
                return endpoint
    raise AssertionError(f"Route {method} {path} not found")


def test_expensive_job_routes_are_rate_limited():
    assert hasattr(route_endpoint("/api/jobs/{video_id}", "POST"), "__wrapped__")
    assert hasattr(route_endpoint("/api/jobs/{video_id}", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/jobs/{video_id}/cancel", "POST"), "__wrapped__")


def test_expensive_video_routes_are_rate_limited():
    assert hasattr(route_endpoint("/api/videos/{video_id}/slides/download", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/chat", "PUT"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/notes", "GET"), "__wrapped__")
    assert hasattr(route_endpoint("/api/videos/{video_id}/notes/export", "POST"), "__wrapped__")
