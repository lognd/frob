"""Tests for `frob.app._daemon_proxy` (T-1093): the CLI-side auto-proxy to
the T-1092 unix-socket daemon, its `FROB_NO_DAEMON=1` bypass, its
version-skew self-heal, and the epic's #1 safety invariant -- daemon-served
and in-process answers must be byte-for-byte identical for a proxied query.
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import pytest

from frob.app import _daemon_proxy
from frob.app._daemon_proxy import ProxyReason, ensure_daemon, query
from frob.serve import SocketDaemonConfig, run_socket_daemon
from frob.serve._socketd import socket_path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with `.frob/` already present."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


def _start_daemon(root: Path, idle_timeout_s: float = 5.0) -> threading.Thread:
    """Start a real `run_socket_daemon` in a background thread and block
    until its socket file exists, mirroring `tests/test_serve_socket.py`'s
    own pattern -- an actual process-shaped daemon, not a mock, is the only
    thing that can prove the differential invariant below."""
    cfg = SocketDaemonConfig(root=root, idle_timeout_s=idle_timeout_s)
    thread = threading.Thread(target=lambda: run_socket_daemon(cfg), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not socket_path(root).exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert socket_path(root).exists()
    return thread


class TestQuery:
    def test_no_daemon_env_bypass(self, root: Path, monkeypatch) -> None:
        # frob:tests tests/test_app_daemon_proxy.py::TestQuery.test_no_daemon_env_bypass
        monkeypatch.setenv("FROB_NO_DAEMON", "1")
        result = query(root, "frob_doable_tickets")
        assert result.is_err
        assert result.danger_err is ProxyReason.Disabled

    def test_no_daemon_no_socket_falls_back(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestQuery.test_no_daemon_no_socket_falls_back
        # No daemon running and spawning is disabled (nonexistent
        # interpreter path) -- query() must still resolve quickly to Err,
        # never hang or raise.
        monkeypatch.setattr(_daemon_proxy.sys, "executable", "/nonexistent/python")
        result = query(root, "frob_doable_tickets")
        assert result.is_err
        assert result.danger_err is ProxyReason.Unreachable

    def test_live_daemon_hit(self, root: Path) -> None:
        # frob:tests tests/test_app_daemon_proxy.py::TestQuery.test_live_daemon_hit
        thread = _start_daemon(root)
        try:
            result = query(root, "frob_doable_tickets")
            assert result.is_ok
            assert result.danger_ok == []
        finally:
            _shutdown(root, thread)

    def test_remote_error_falls_back(self, root: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestQuery.test_remote_error_falls_back
        thread = _start_daemon(root)
        try:
            result = query(root, "not_a_real_method")
            assert result.is_err
            assert result.danger_err is ProxyReason.RemoteError
        finally:
            _shutdown(root, thread)


def _shutdown(root: Path, thread: threading.Thread) -> None:
    """Force the idle-timeout daemon down promptly rather than waiting out
    its full `idle_timeout_s` at teardown."""
    from frob.serve._socketd import lock_path

    deadline = time.monotonic() + 5
    while (
        lock_path(root).exists() and time.monotonic() < deadline and thread.is_alive()
    ):
        time.sleep(0.05)
        if not socket_path(root).exists():
            break
    thread.join(timeout=1)


class TestEnsureDaemon:
    def test_spawns_when_nothing_recorded(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_spawns_when_nothing_rec\
        # orded
        # No daemon is up, so the frob_version RPC finds nothing to answer
        # and ensure_daemon must spawn one.
        monkeypatch.setattr(_daemon_proxy, "_query_daemon_version", lambda r: None)
        spawned = []
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert spawned == [root]

    def test_noop_when_version_matches(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_noop_when_version_match\
        # es
        monkeypatch.setattr(
            _daemon_proxy,
            "_query_daemon_version",
            lambda r: _daemon_proxy._client_version(),
        )
        spawned = []
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert spawned == []

    def test_restarts_on_version_skew(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_restarts_on_version_skew
        monkeypatch.setattr(
            _daemon_proxy, "_query_daemon_version", lambda r: "0.0.0-stale"
        )
        shutdown_calls = []
        spawned = []
        monkeypatch.setattr(
            _daemon_proxy, "_shutdown_stale_daemon", lambda r: shutdown_calls.append(r)
        )
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert shutdown_calls == [root]
        assert spawned == [root]

    def test_version_handshake_end_to_end(self, root: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_version_handshake_end_t\
        # o_end
        # A real running daemon (not mocked): frob_version RPC must report
        # this client's own version, so ensure_daemon must not spawn a
        # second, redundant daemon.
        thread = _start_daemon(root)
        try:
            assert (
                _daemon_proxy._query_daemon_version(root)
                == _daemon_proxy._client_version()
            )
        finally:
            _shutdown(root, thread)


class TestDifferentialParity:
    """T-0321's #1 safety invariant: daemon-served and in-process answers
    must be byte-for-byte identical for every proxied query shape."""

    def test_perf_hot_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_perf_hot_json_dae\
        # mon_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        # FROB_NO_DAEMON=1 in-process reference run.
        in_process = subprocess.run(
            ["uv", "run", "frob", "perf", "hot", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "perf", "hot", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        # Compare only the rendered JSON payload -- the log lines above it
        # legitimately differ (they narrate which path answered the query,
        # which is exactly the decision this ticket adds); the safety
        # invariant under test is that the ANSWER is byte-for-byte
        # identical, not the diagnostic narration around it.
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_graph_affects_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_graph_affects_jso\
        # n_daemon_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        (project / "helper.py").write_text(
            "def helper():\n    return 1\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        # FROB_NO_DAEMON=1 in-process reference run.
        in_process = subprocess.run(
            ["uv", "run", "frob", "graph", "affects", "helper.py::helper", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                [
                    "uv",
                    "run",
                    "frob",
                    "graph",
                    "affects",
                    "helper.py::helper",
                    "--json",
                ],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_graph_query_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_graph_query_json_\
        # daemon_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        (project / "helper.py").write_text(
            "def helper():\n    return 1\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        in_process = subprocess.run(
            ["uv", "run", "frob", "graph", "query", "helper.py::helper", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "graph", "query", "helper.py::helper", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_doable_tickets_json_daemon_matches_in_process(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_doable_tickets_js\
        # on_daemon_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        in_process = subprocess.run(
            ["uv", "run", "frob", "ticket", "doable", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "ticket", "doable", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_check_delta_gates_only_json_daemon_matches_in_process(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_check_delta_gates\
        # _only_json_daemon_matches_in_process
        # T-1147: the one narrow `frob check --only gates --delta --json`
        # shape `_try_check_delta_via_daemon` proxies -- everything else
        # (a mixed --only, no --delta, a non-python/polyglot project) must
        # keep falling through to the in-process path unchanged, which is
        # exactly the narrowness this parity test (not a broader one) is
        # meant to prove.
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        in_process = subprocess.run(
            ["uv", "run", "frob", "check", "--only", "gates", "--delta", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "check", "--only", "gates", "--delta", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        # A fresh project's own `--only gates` run may exit 1 (real
        # ERROR-severity findings against a bare `pyproject.toml` project)
        # -- the parity invariant under test is that daemon-served and
        # in-process agree on BOTH the exit code and the rendered payload,
        # not that the run is clean.
        assert daemon_served.returncode == in_process.returncode
        # T-1147: the `gate-summary` `ToolResult`'s own `summary` carries a
        # real per-gate wall/cpu timing blob (`_gate_summary_result`'s
        # trailing `[gate=0.02s, ...]`) that is GENUINELY non-reproducible
        # between two independent process runs (one warm-cache via the
        # daemon, one cold in-process) -- this is the one field this
        # parity test normalizes away, not a formatting divergence being
        # papered over; every other field (every violation, diagnostic,
        # per-family `ToolResult`, exit code, and the summary's own error/
        # warning/waived counts) is still compared byte-for-byte.
        assert _normalize_gate_timing(
            _json_tail(daemon_served.stdout)
        ) == _normalize_gate_timing(_json_tail(in_process.stdout))

    def test_touched_tests_json_daemon_matches_in_process(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_touched_tests_jso\
        # n_daemon_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        # .frob/ must be gitignored -- otherwise the daemon's own untracked
        # runtime files (daemon.lock, cache.db, ...) show up as "touched"
        # in the daemon-served run but not the earlier in-process
        # reference run (which never started a daemon), a spurious
        # environmental divergence, not a real payload-shape mismatch.
        (project / ".gitignore").write_text(".frob/\n")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"], cwd=project, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "t"], cwd=project, check=True
        )
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init"], cwd=project, check=True
        )

        # Nothing touched (no diff against main after the initial commit) --
        # the parity-sensitive empty-selection branch both the CLI and
        # `_try_touched_via_daemon` special-case identically (T-1128).
        in_process = subprocess.run(
            ["uv", "run", "frob", "test", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "test", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_exports_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_exports_json_daem\
        # on_matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        pkg = project / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "mod.py").write_text(
            "def helper():\n    return 1\n\n\ndef _private():\n    return 2\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        in_process = subprocess.run(
            ["uv", "run", "frob", "exports", "pkg", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "exports", "pkg", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)

    def test_stats_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestDifferentialParity.test_stats_json_daemon\
        # _matches_in_process
        pytest.importorskip("frob_core")
        project = tmp_path
        (project / ".frob").mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.0"\n'
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"], cwd=project, check=True
        )
        subprocess.run(["git", "config", "user.name", "t"], cwd=project, check=True)
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project, check=True)

        in_process = subprocess.run(
            ["uv", "run", "frob", "stats", "--json"],
            cwd=project,
            env={**_env(), "FROB_NO_DAEMON": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert in_process.returncode == 0, in_process.stderr

        thread = _start_daemon(project)
        try:
            daemon_served = subprocess.run(
                ["uv", "run", "frob", "stats", "--json"],
                cwd=project,
                env=_env(),
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            _shutdown(project, thread)
        assert daemon_served.returncode == 0, daemon_served.stderr
        assert _json_tail(daemon_served.stdout) == _json_tail(in_process.stdout)


def _normalize_gate_timing(payload_text: str) -> str:
    """Blank out `_gate_summary_result`'s trailing `[gate=0.02s, ...]`
    timing blob wherever it appears in a rendered `gate-summary` `ToolResult`
    -- real elapsed-time measurements that legitimately differ between two
    independent process runs (T-1147's differential-parity test is the one
    caller of this; every other field in the payload stays a strict,
    unnormalized byte comparison)."""
    import re

    return re.sub(r"\[[a-z_]+=[0-9.]+s(?:, [a-z_]+=[0-9.]+s)*\]", "[...]", payload_text)


def _json_tail(stdout: str) -> str:
    """The final JSON payload a proxied `--json` command writes -- log
    lines precede it, so find the line starting the JSON block (a bare
    array `frob perf hot --json` prints, or a bare object `frob graph
    affects --json` prints, T-1106) and return everything from there,
    verbatim (byte-for-byte, not re-parsed -- re-parsing would hide a
    real formatting divergence)."""
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(("[", "{")):
            return "\n".join(lines[i:])
    raise AssertionError(f"no JSON payload found in stdout: {stdout!r}")


def _env() -> dict[str, str]:
    """A minimal, real environment for the subprocess CLI calls above --
    `os.environ` verbatim (the CLI needs PATH/HOME/etc.), overridden per
    call by the caller's own `**` merge."""
    import os

    return dict(os.environ)
