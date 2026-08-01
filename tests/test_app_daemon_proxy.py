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
    @pytest.fixture(autouse=True)
    def _opt_in(self, monkeypatch):
        """T-1379 made the daemon opt-IN, so every test here that exercises
        the daemon path must ask for it explicitly. The bypass test below
        overrides this with FROB_NO_DAEMON, which still wins."""
        monkeypatch.setenv("FROB_DAEMON", "1")

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
        monkeypatch.setattr(
            _daemon_proxy,
            "probe_daemon",
            lambda r, **k: (_daemon_proxy.DaemonLiveness.NoSocket, None),
        )
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
            "probe_daemon",
            lambda r, **k: (
                _daemon_proxy.DaemonLiveness.Live,
                _daemon_proxy._client_version(),
            ),
        )
        spawned = []
        monkeypatch.setattr(_daemon_proxy, "_spawn_daemon", lambda r: spawned.append(r))
        ensure_daemon(root)
        assert spawned == []

    def test_restarts_on_version_skew(self, root: Path, monkeypatch) -> None:
        # frob:tests \
        # tests/test_app_daemon_proxy.py::TestEnsureDaemon.test_restarts_on_version_skew
        monkeypatch.setattr(
            _daemon_proxy,
            "probe_daemon",
            lambda r, **k: (_daemon_proxy.DaemonLiveness.VersionSkew, "0.0.0-stale"),
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
            liveness, version = _daemon_proxy.probe_daemon(root)
            assert liveness is _daemon_proxy.DaemonLiveness.Live
            assert version == _daemon_proxy._client_version()
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

    def test_touched_tests_json_daemon_matches_in_process(self, tmp_path: Path) -> None:
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
        subprocess.run(["git", "config", "user.name", "t"], cwd=project, check=True)
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project, check=True)

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


# frob:ticket T-1377
class TestProbeDaemon:
    """T-1377: socket-file existence is not liveness. These pin that each
    unhealthy state is told APART -- collapsing them (the pre-T-1377
    behavior) is what made an unhealthy daemon cost 10s per invocation and
    spawn rivals it could never win against."""

    @staticmethod
    def _socket_dir(tmp_path):
        (tmp_path / ".frob").mkdir(parents=True, exist_ok=True)
        return tmp_path

    def test_missing_socket_is_nosocket(self, tmp_path):
        """Nothing there at all -- the spawn case."""
        from frob.app._daemon_proxy import DaemonLiveness, probe_daemon

        liveness, version = probe_daemon(self._socket_dir(tmp_path))
        assert liveness is DaemonLiveness.NoSocket
        assert version is None

    def test_dead_socket_file_is_orphaned(self, tmp_path):
        """A socket file that no process is listening on. This is the state
        a crashed daemon leaves behind, and the one the old code could not
        distinguish from 'no daemon'."""
        import socket as _socket

        from frob.app._daemon_proxy import DaemonLiveness, probe_daemon

        root = self._socket_dir(tmp_path)
        path = root / ".frob" / "daemon.sock"
        # Bind (creating the file), then close WITHOUT listening/accepting.
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.bind(str(path))
        sock.close()
        assert path.exists(), "the socket file must outlive its process"

        liveness, version = probe_daemon(root)
        assert liveness is DaemonLiveness.Orphaned
        assert version is None

    def test_silent_listener_is_wedged(self, tmp_path):
        """A process IS listening but never answers. Spawning a rival here
        is the harmful case: the singleton lock refuses it, so every later
        invocation pays another failed spawn."""
        import socket as _socket

        from frob.app._daemon_proxy import DaemonLiveness, probe_daemon

        root = self._socket_dir(tmp_path)
        path = root / ".frob" / "daemon.sock"
        server = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)
        try:
            liveness, version = probe_daemon(root, timeout_s=0.2)
            assert liveness is DaemonLiveness.Wedged
            assert version is None
        finally:
            server.close()

    def test_probe_of_a_silent_listener_stays_within_budget(self, tmp_path):
        """The POINT of T-1377: an unhealthy daemon must cost the probe
        budget, not `send_request`'s 10s query timeout."""
        import socket as _socket
        import time

        from frob.app._daemon_proxy import probe_daemon

        root = self._socket_dir(tmp_path)
        path = root / ".frob" / "daemon.sock"
        server = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)
        try:
            started = time.monotonic()
            probe_daemon(root, timeout_s=0.2)
            elapsed = time.monotonic() - started
        finally:
            server.close()
        # Generous ceiling: the claim is "sub-second, not 10s", and this
        # must not flake on a loaded box the way a tight bound would.
        assert elapsed < 3.0, f"probe took {elapsed:.2f}s, budget was 0.2s"

    def test_orphaned_socket_is_unlinked(self, tmp_path):
        """The orphan must be cleared, so the NEXT probe is a clean
        NoSocket instead of another refused connect forever."""
        import socket as _socket

        from frob.app._daemon_proxy import (
            DaemonLiveness,
            _clear_orphaned_socket,
            probe_daemon,
        )

        root = self._socket_dir(tmp_path)
        path = root / ".frob" / "daemon.sock"
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.bind(str(path))
        sock.close()

        assert probe_daemon(root)[0] is DaemonLiveness.Orphaned
        _clear_orphaned_socket(root)
        assert not path.exists()
        assert probe_daemon(root)[0] is DaemonLiveness.NoSocket


# frob:ticket T-1377
class TestProbeDaemonVersion:
    """`probe_daemon` must tell a version-matched daemon from a skewed one
    against a REAL listener, not just a mocked seam -- the skew branch is
    what decides between reusing a daemon and restarting it."""

    @staticmethod
    def _serve_one_version(path, version):
        """A minimal listener that answers exactly one frob_version RPC."""
        import json
        import socket as _socket
        import threading

        server = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        server.bind(str(path))
        server.listen(1)

        def _run():
            try:
                conn, _ = server.accept()
                with conn:
                    conn.recv(65536)
                    conn.sendall(
                        (
                            json.dumps({"id": 1, "result": {"version": version}}) + "\n"
                        ).encode("utf-8")
                    )
            except OSError:
                pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return server, thread

    def test_matching_version_is_live(self, tmp_path):
        from frob.app._daemon_proxy import (
            DaemonLiveness,
            _client_version,
            probe_daemon,
        )

        (tmp_path / ".frob").mkdir(parents=True, exist_ok=True)
        path = tmp_path / ".frob" / "daemon.sock"
        server, thread = self._serve_one_version(path, _client_version())
        try:
            liveness, version = probe_daemon(tmp_path, timeout_s=2.0)
            assert liveness is DaemonLiveness.Live
            assert version == _client_version()
        finally:
            server.close()
            thread.join(timeout=2)

    def test_different_version_is_skew_not_live(self, tmp_path):
        """The mutation that matters: flipping this comparison would make
        every stale daemon look Live and never be restarted."""
        from frob.app._daemon_proxy import DaemonLiveness, probe_daemon

        (tmp_path / ".frob").mkdir(parents=True, exist_ok=True)
        path = tmp_path / ".frob" / "daemon.sock"
        server, thread = self._serve_one_version(path, "0.0.0-stale")
        try:
            liveness, version = probe_daemon(tmp_path, timeout_s=2.0)
            assert liveness is DaemonLiveness.VersionSkew
            assert version == "0.0.0-stale"
        finally:
            server.close()
            thread.join(timeout=2)


# frob:ticket T-1379
class TestDaemonOptIn:
    """T-1379: while T-1378's shutdown/leak/CPU defects stand, the daemon
    must not engage unless explicitly asked for. Opt-out meant every
    unsuspecting session paid for those defects by default."""

    def test_unset_env_disables_the_daemon(self, tmp_path, monkeypatch):
        """The default. Nothing set -> no daemon, no spawn."""
        from frob.app._daemon_proxy import ProxyReason, query

        monkeypatch.delenv("FROB_DAEMON", raising=False)
        monkeypatch.delenv("FROB_NO_DAEMON", raising=False)
        result = query(tmp_path, "frob_version")
        assert result.is_err
        assert result.danger_err is ProxyReason.Disabled

    def test_frob_daemon_1_enables_the_daemon(self, monkeypatch):
        """The opt-in must actually opt in -- a flag stuck off is as broken
        as one stuck on."""
        from frob.app import _daemon_proxy

        monkeypatch.setenv("FROB_DAEMON", "1")
        monkeypatch.delenv("FROB_NO_DAEMON", raising=False)
        assert _daemon_proxy._daemon_enabled() is True

    def test_no_daemon_still_wins_over_opt_in(self, monkeypatch):
        """FROB_NO_DAEMON=1 remains an unconditional bypass, so existing
        scripts and the differential test are unaffected."""
        from frob.app import _daemon_proxy

        monkeypatch.setenv("FROB_DAEMON", "1")
        monkeypatch.setenv("FROB_NO_DAEMON", "1")
        assert _daemon_proxy._daemon_enabled() is False
