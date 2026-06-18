"""Server restart API."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from egodary.api.main import app


def test_server_restart_endpoint():
    client = TestClient(app)
    with (
        patch("egodary.core.server_restart.reload_application_caches") as reload_mock,
        patch("egodary.core.server_restart.schedule_process_restart") as restart_mock,
    ):
        response = client.post("/api/server/restart")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    reload_mock.assert_called_once()
    restart_mock.assert_called_once()
