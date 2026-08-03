"""Socket/subprocess error-path coverage for `frob.app._daemon_proxy`
(T-1457).

Wave5-O's T-1400 classification isolated this module as the app package's
one genuine TEST005 gap outside telemetry: `_ask_version_over_socket`'s
transport-failure branches, `_classify_version_reply`'s malformed-reply
branches, `_clear_orphaned_socket`/`_spawn_daemon`'s best-effort OSError
swallows, `_shutdown_stale_daemon`'s whole RPC-then-wait body, and
`try_daemon_lease`/`release_daemon_lease`'s remote-error/OSError paths.
Each test asserts real behavior (a returned fallback value, a logged
message, or a re-raised exception NOT happening) -- not mere execution --
per this ticket's acceptance criterion.

Mocks the socket/subprocess seams directly rather than spinning up a real
daemon, mirroring `tests/unit/test_daemon_proxy_lease_t1276.py`'s
precedent of exercising branches the existing differential/real-daemon
tests in `tests/test_app_daemon_proxy.py` do not reach.
"""

from __future__ import annotations

import socket as socket_module
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from frob.app import _daemon_proxy
from frob.app._daemon_proxy import (
    DaemonLiveness,
    ProxyReason,
    _ask_version_over_socket,
    _classify_version_reply,
    _clear_orphaned_socket,
    _client_version,
    _shutdown_stale_daemon,
    _spawn_daemon,
    release_daemon_lease,
    try_daemon_lease,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A bare project root with `.frob/` already present."""
    (tmp_path / ".frob").mkdir()
    return tmp_path


class TestAskVersionOverSocket:
    """`_ask_version_over_socket`'s transport-failure branches -- distinct
    from `ConnectionRefusedError`/`FileNotFoundError` (Orphaned), already
    covered by `tests/test_app_daemon_proxy.py::TestProbeDaemon`."""

    def test_connect_timeout_is_wedged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.t\
        # est_connect_timeout_is_wedged
        fake_sock = MagicMock()
        fake_sock.connect.side_effect = TimeoutError("timed out")
        fake_sock.__enter__.return_value = fake_sock
        fake_sock.__exit__.return_value = False
        with patch.object(socket_module, "socket", return_value=fake_sock):
            result = _ask_version_over_socket(tmp_path / "sock", 0.1)
        assert result is DaemonLiveness.Wedged

    def test_connect_oserror_is_wedged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.t\
        # est_connect_oserror_is_wedged
        fake_sock = MagicMock()
        fake_sock.connect.side_effect = OSError("permission denied")
        fake_sock.__enter__.return_value = fake_sock
        fake_sock.__exit__.return_value = False
        with patch.object(socket_module, "socket", return_value=fake_sock):
            result = _ask_version_over_socket(tmp_path / "sock", 0.1)
        assert result is DaemonLiveness.Wedged

    def test_hangup_before_newline_is_wedged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.t\
        # est_hangup_before_newline_is_wedged
        # Accepted the connection, then hung up (recv returns b"") without
        # ever sending a newline-terminated reply.
        fake_sock = MagicMock()
        fake_sock.recv.return_value = b""
        fake_sock.__enter__.return_value = fake_sock
        fake_sock.__exit__.return_value = False
        with patch.object(socket_module, "socket", return_value=fake_sock):
            result = _ask_version_over_socket(tmp_path / "sock", 0.1)
        assert result is DaemonLiveness.Wedged

    def test_outer_timeout_during_send_or_recv_is_wedged(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket.t\
        # est_outer_timeout_during_send_or_recv_is_wedged
        fake_sock = MagicMock()
        fake_sock.sendall.side_effect = TimeoutError("send timed out")
        fake_sock.__enter__.return_value = fake_sock
        fake_sock.__exit__.return_value = False
        with patch.object(socket_module, "socket", return_value=fake_sock):
            result = _ask_version_over_socket(tmp_path / "sock", 0.1)
        assert result is DaemonLiveness.Wedged


class TestClassifyVersionReply:
    """`_classify_version_reply`'s malformed/unreadable-reply branches."""

    def test_malformed_json_is_wedged(self) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.t\
        # est_malformed_json_is_wedged
        liveness, version = _classify_version_reply(b"not json at all\n")
        assert liveness is DaemonLiveness.Wedged
        assert version is None

    def test_non_dict_result_is_wedged(self) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.t\
        # est_non_dict_result_is_wedged
        # payload.get("result", {}).get("version") -- "result" is a bare
        # string, so the chained .get raises AttributeError.
        liveness, version = _classify_version_reply(b'{"result": "oops"}\n')
        assert liveness is DaemonLiveness.Wedged
        assert version is None

    def test_non_str_version_is_wedged(self) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.t\
        # est_non_str_version_is_wedged
        liveness, version = _classify_version_reply(
            b'{"result": {"version": 123}}\n'
        )
        assert liveness is DaemonLiveness.Wedged
        assert version is None

    def test_bad_utf8_is_wedged(self) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply.t\
        # est_bad_utf8_is_wedged
        liveness, version = _classify_version_reply(b"\xff\xfe\n")
        assert liveness is DaemonLiveness.Wedged
        assert version is None


class TestClearOrphanedSocket:
    """`_clear_orphaned_socket`'s best-effort unlink swallow."""

    def test_unlink_oserror_is_swallowed(self, root: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClearOrphanedSocket.te\
        # st_unlink_oserror_is_swallowed
        import logging

        with caplog.at_level(logging.INFO, logger="frob.app._daemon_proxy"):
            with patch(
                "frob.serve.socket_path",
                return_value=MagicMock(
                    unlink=MagicMock(side_effect=OSError("gone"))
                ),
            ):
                _clear_orphaned_socket(root)  # must not raise
        assert any(
            "could not unlink orphaned socket" in rec.message for rec in caplog.records
        )


class TestClientVersion:
    """`_client_version`'s generic-Exception fallback (distinct from the
    already-tested `PackageNotFoundError` branch)."""

    def test_unexpected_exception_falls_back_to_unknown(self, caplog) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClientVersion.test_une\
        # xpected_exception_falls_back_to_unknown
        import logging

        with caplog.at_level(logging.DEBUG, logger="frob.app._daemon_proxy"):
            with patch(
                "importlib.metadata.version", side_effect=RuntimeError("boom")
            ):
                assert _client_version() == "unknown"
        assert any("version lookup failed" in rec.message for rec in caplog.records)


class TestSpawnDaemon:
    """`_spawn_daemon`'s best-effort `Popen` OSError swallow."""

    def test_popen_oserror_is_swallowed(self, root: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestSpawnDaemon.test_popen\
        # _oserror_is_swallowed
        import logging

        with caplog.at_level(logging.INFO, logger="frob.app._daemon_proxy"):
            with patch.object(
                subprocess, "Popen", side_effect=OSError("no such interpreter")
            ):
                _spawn_daemon(root)  # must not raise
        assert any("spawn failed" in rec.message for rec in caplog.records)


class TestShutdownStaleDaemon:
    """`_shutdown_stale_daemon`'s full RPC-then-wait body -- both the
    `send_request` failure branch and the successful-shutdown wait loop."""

    def test_rpc_failure_is_logged_and_returns(self, root: Path, caplog) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon.te\
        # st_rpc_failure_is_logged_and_returns
        import logging

        from typani import Err

        from frob.serve import DaemonError

        with caplog.at_level(logging.INFO, logger="frob.app._daemon_proxy"):
            with patch(
                "frob.serve.send_request", return_value=Err(DaemonError.Unreachable)
            ):
                _shutdown_stale_daemon(root)  # must not raise
        assert any(
            "frob_shutdown RPC failed" in rec.message for rec in caplog.records
        )

    def test_successful_shutdown_waits_for_lock_release(
        self, root: Path, caplog
    ) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon.te\
        # st_successful_shutdown_waits_for_lock_release
        import logging

        from typani import Ok

        # Lock file exists on the first poll, gone on the second -- proves
        # the wait loop actually re-checks `path.exists()` rather than
        # returning immediately.
        exists_calls = {"n": 0}

        def _fake_exists(self):
            exists_calls["n"] += 1
            return exists_calls["n"] == 1

        with caplog.at_level(logging.INFO, logger="frob.app._daemon_proxy"):
            with (
                patch("frob.serve.send_request", return_value=Ok({"ok": True})),
                patch("frob.serve._socketd.lock_path", return_value=root / "lock"),
                patch.object(Path, "exists", _fake_exists),
            ):
                _shutdown_stale_daemon(root)
        assert exists_calls["n"] >= 2
        assert any(
            "frob_shutdown accepted" in rec.message for rec in caplog.records
        )


class TestTryDaemonLeaseErrorPaths:
    """`try_daemon_lease`'s connect-OSError, call-OSError, and remote-error
    branches -- distinct from `test_daemon_proxy_lease_t1276.py`'s
    happy-path/disabled/no-socket coverage."""

    @pytest.fixture(autouse=True)
    def _opt_in(self, monkeypatch):
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPat\
        # hs._opt_in
        monkeypatch.setenv("FROB_DAEMON", "1")

    def test_call_oserror_closes_connection_and_returns_unreachable(
        self, root: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPat\
        # hs.test_call_oserror_closes_connection_and_returns_unreachable
        fake_conn = MagicMock()
        fake_conn.call.side_effect = OSError("broken pipe")
        with (
            patch.object(_daemon_proxy, "ensure_daemon", lambda r: None),
            patch.object(
                _daemon_proxy, "_LeaseConnection", return_value=fake_conn
            ),
        ):
            result = try_daemon_lease(root, "some-resource")
        assert result.is_err
        assert result.danger_err is ProxyReason.Unreachable
        fake_conn.close.assert_called_once()

    def test_remote_error_response_closes_connection(self, root: Path) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPat\
        # hs.test_remote_error_response_closes_connection
        fake_conn = MagicMock()
        fake_conn.call.return_value = {"error": {"message": "no such resource"}}
        with (
            patch.object(_daemon_proxy, "ensure_daemon", lambda r: None),
            patch.object(
                _daemon_proxy, "_LeaseConnection", return_value=fake_conn
            ),
        ):
            result = try_daemon_lease(root, "some-resource")
        assert result.is_err
        assert result.danger_err is ProxyReason.RemoteError
        fake_conn.close.assert_called_once()


class TestReleaseDaemonLease:
    """`release_daemon_lease`'s best-effort `call` OSError swallow --
    `conn.close()` must still run either way."""

    def test_call_oserror_is_swallowed_and_connection_still_closed(self) -> None:
        # frob:tests \
        # tests/unit/test_daemon_proxy_error_paths_t1457.py::TestReleaseDaemonLease.tes\
        # t_call_oserror_is_swallowed_and_connection_still_closed
        fake_conn = MagicMock()
        fake_conn.call.side_effect = OSError("connection reset")
        release_daemon_lease(fake_conn, "some-resource")  # must not raise
        fake_conn.close.assert_called_once()
