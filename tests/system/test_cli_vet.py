"""End-to-end tests for `frob vet` (docs/vet.md). Uses a local fake HTTP
registry server via `[vet].registry_base_url` -- no real network calls."""

from __future__ import annotations

import http.server
import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.system.conftest import run


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class _FakeRegistryHandler(http.server.BaseHTTPRequestHandler):
    """Mirrors real per-ecosystem JSON shapes under a single fake host, keyed
    by the same path suffixes `frob.vet._registry` builds for real registries."""

    def do_GET(self) -> None:  # noqa: N802
        fresh_time = _iso(datetime.now(UTC) - timedelta(days=2))
        old_time = _iso(datetime.now(UTC) - timedelta(days=900))

        # /pypi/{name}/{version}/json
        if self.path.startswith("/pypi/"):
            parts = self.path.strip("/").split("/")
            name, version = parts[1], parts[2]
            ts = fresh_time if "new" in name else old_time
            body = json.dumps({"releases": {version: [{"upload_time_iso_8601": ts}]}})
            self._send(body)
            return

        # /npm/{name}
        if self.path.startswith("/npm/"):
            name = self.path.strip("/").split("/")[1]
            ts = fresh_time if "new" in name else old_time
            body = json.dumps({"time": {"1.0.0": ts}, "dist-tags": {"latest": "1.0.0"}})
            self._send(body)
            return

        # /crates/{name}/versions
        if self.path.startswith("/crates/"):
            name = self.path.strip("/").split("/")[1]
            ts = fresh_time if "new" in name else old_time
            body = json.dumps({"versions": [{"num": "1.0.0", "created_at": ts}]})
            self._send(body)
            return

        self.send_response(404)
        self.end_headers()

    def _send(self, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: D102 -- silence test server logging
        pass


@pytest.fixture
def fake_registry():
    server = http.server.HTTPServer(("127.0.0.1", 0), _FakeRegistryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        thread.join(timeout=5)


class TestHookMode:
    def test_non_install_command_fast_exits_zero(self, tmp_path: Path) -> None:
        r = run("vet", str(tmp_path), "--hook", "git status")
        assert r.returncode == 0
        assert r.stderr == ""

    def test_empty_hook_command_fast_exits_zero(self, tmp_path: Path) -> None:
        r = run("vet", str(tmp_path), "--hook", "ls -la")
        assert r.returncode == 0

    def test_old_package_passes(self, tmp_path: Path, fake_registry: str) -> None:
        # frob:tests src/frob/vet kind="integration"
        (tmp_path / "frob.toml").write_text(
            f'[vet]\nquarantine_days = 14\nregistry_base_url = "{fake_registry}"\n'
        )
        r = run("vet", str(tmp_path), "--hook", "uv add requests")
        assert r.returncode == 0
        assert "requests" in r.stdout

    def test_fresh_package_blocks(self, tmp_path: Path, fake_registry: str) -> None:
        (tmp_path / "frob.toml").write_text(
            f'[vet]\nquarantine_days = 14\nregistry_base_url = "{fake_registry}"\n'
        )
        r = run("vet", str(tmp_path), "--hook", "npm install some-new-pkg-2026")
        assert r.returncode == 2
        assert "quarantined" in (r.stdout + r.stderr)

    def test_typosquat_blocks_without_network(self, tmp_path: Path) -> None:
        r = run("vet", str(tmp_path), "--hook", "pip install requets")
        assert r.returncode == 2
        assert "typosquat" in (r.stdout + r.stderr)
