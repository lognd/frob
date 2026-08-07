"""T-1317: `frob ack` accountability -- a mandatory reason and a recorded
digest delta, so an ack is auditable evidence rather than a silent clear
(docs/modules/gates.md#ack-accountability-t-1317).

Complements `tests/test_graph_lock.py::TestAckDrift` (the pre-existing
acknowledge/drift suite, now updated to pass `reason=` at every call
site): this file drives the T-1317-specific behavior -- the reason gate
itself (missing/boilerplate refusal) and the `ack_log` digest-delta audit
trail `acknowledge` now appends to.
"""

from __future__ import annotations

from pathlib import Path

from frob.app.ack_runner import run
from frob.app.config import AppConfig
from frob.graph import build_graph
from frob.graph.lock import LockError, acknowledge, load_lock, write_lock

# T-1317: reuse test_graph_lock's own tmp_path-writing fixture helper rather
# than defining a second copy here -- same fixture shape (write a source
# file under tmp_path so build_graph has something to parse), one home.
from tests.test_graph_lock import _write  # noqa: I001

_WIDGET_PY = '''class Widget:
    """A widget."""

    def render(self, value: int) -> str:
        """Render the widget."""
        # frob:doc docs/x.md#widget
        return str(value)
'''

_REASON = "re-verified against the current render() body, still accurate"


class TestAckAccountability:
    def _snapshot(self, tmp_path: Path):
        _write(tmp_path, "src/a.py", _WIDGET_PY)
        cache = tmp_path / ".frob" / "cache.db"
        return build_graph(tmp_path, cache).danger_ok

    def test_ack_requires_reason(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        """A blank reason is `Err(AckReasonMissing)`, not a silent clear."""
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        result = acknowledge(lock, snap, ["src/a.py::Widget.render"], reason="   ")
        assert result.is_err
        assert result.danger_err is LockError.AckReasonMissing

    def test_ack_rejects_boilerplate_reason(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        """A rubber-stamp reason ("lgtm") and a short, non-listed reason
        ("yep") are both refused -- the boilerplate list is a floor, not
        the whole check; rubber-stamping is a gate failure either way."""
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        for boilerplate_reason in ("lgtm", "yep"):
            result = acknowledge(
                lock, snap, ["src/a.py::Widget.render"], reason=boilerplate_reason
            )
            assert result.is_err
            assert result.danger_err is LockError.AckReasonBoilerplate

    def test_first_ack_records_none_old_digest(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        """A genuine first-ever ack of a (ref, facet) records `old_digest
        =None` -- distinct from "delta could not be computed"."""
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(
            lock, snap, ["src/a.py::Widget.render"], reason=_REASON
        ).danger_ok
        sig_entries = [e for e in acked.ack_log if e.facet == "sig"]
        assert len(sig_entries) == 1
        assert sig_entries[0].old_digest is None
        assert sig_entries[0].new_digest
        assert sig_entries[0].reason == _REASON
        assert sig_entries[0].actor
        assert sig_entries[0].at is not None

    def test_ack_records_digest_delta(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::acknowledge
        """Re-acking after a real edit records the true old->new digest
        delta in a NEW ack_log entry -- the prior entry is never edited,
        only appended past."""
        ref = "src/a.py::Widget.render"
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        first = acknowledge(lock, snap, [ref], reason=_REASON).danger_ok
        write_lock(first, tmp_path / "frob.lock")

        _write(
            tmp_path,
            "src/a.py",
            _WIDGET_PY.replace(
                "def render(self, value: int) -> str:",
                "def render(self, value: int, extra: int = 0) -> str:",
            ),
        )
        cache = tmp_path / ".frob" / "cache.db"
        snap2 = build_graph(tmp_path, cache).danger_ok
        second = acknowledge(
            first, snap2, [ref], reason="re-verified again after signature edit"
        ).danger_ok

        assert len(second.ack_log) == len(first.ack_log) + 2  # sig + body
        sig_log = [e for e in second.ack_log if e.facet == "sig"]
        assert len(sig_log) == 2
        assert sig_log[0].old_digest is None
        assert sig_log[1].old_digest == sig_log[0].new_digest
        assert sig_log[1].new_digest != sig_log[1].old_digest

    def test_ack_log_persists_through_write_and_load(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/lock.py::write_lock
        # frob:tests src/frob/graph/lock.py::load_lock
        """`ack_log` round-trips through `write_lock`/`load_lock` -- the
        audit trail is durable, not just an in-memory artifact of one
        `acknowledge` call."""
        ref = "src/a.py::Widget.render"
        snap = self._snapshot(tmp_path)
        lock = load_lock(tmp_path / "frob.lock").danger_ok
        acked = acknowledge(lock, snap, [ref], reason=_REASON).danger_ok
        lock_path = tmp_path / "frob.lock"
        write_lock(acked, lock_path)

        reloaded = load_lock(lock_path).danger_ok
        assert len(reloaded.ack_log) == len(acked.ack_log)
        assert {e.reason for e in reloaded.ack_log} == {_REASON}

    def test_ack_cli_requires_reason(self, tmp_path: Path, caplog) -> None:  # noqa: ANN001
        # frob:tests src/frob/app/ack_runner.py::run
        """`frob ack <ref>` with no `--reason`/`--reason-file` refuses
        (exit 1) before writing anything -- the CLI-level half of the
        `acknowledge` reason gate."""
        import logging

        import pytest

        caplog.set_level(logging.ERROR)
        self._snapshot(tmp_path)
        cfg = AppConfig(ack_refs=["src/a.py::Widget.render"], ack_path=tmp_path)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "requires --reason" in caplog.text
        assert not (tmp_path / "frob.lock").exists()

    def test_ack_list_renders_audit_trail(self, tmp_path: Path, capsys) -> None:  # noqa: ANN001
        # frob:tests src/frob/app/ack_runner.py::run
        """`frob ack --list` surfaces the recorded reason and digest delta
        for a prior ack -- the audit trail is inspectable, not just
        durable (T-1317's own "must be surfaced" requirement)."""
        self._snapshot(tmp_path)
        cfg = AppConfig(
            ack_refs=["src/a.py::Widget.render"], ack_path=tmp_path, ack_reason=_REASON
        )
        run(cfg)

        list_cfg = AppConfig(ack_path=tmp_path, ack_list=True)
        run(list_cfg)
        out = capsys.readouterr().out
        assert "src/a.py::Widget.render" in out
        assert _REASON in out
        assert "(new)->" in out

    def test_ack_cli_reason_file_reads_verbatim(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_mutate.py::read_reason_file_verbatim
        """`frob ack --reason-file PATH` reads the reason verbatim (T-0737)
        via the shared `read_reason_file_verbatim` helper -- a backtick or
        `$(...)` in the file's prose must survive untouched, never routed
        through a shell that could execute it."""
        self._snapshot(tmp_path)
        reason_file = _write(
            tmp_path,
            "reason.txt",
            "re-verified against `render()`'s current body; still accurate",
        )
        cfg = AppConfig(
            ack_refs=["src/a.py::Widget.render"],
            ack_path=tmp_path,
            ack_reason_file=reason_file,
        )
        run(cfg)

        lock = load_lock(tmp_path / "frob.lock").danger_ok
        assert any("`render()`" in e.reason for e in lock.ack_log)

    def test_content_verified_gates_take_no_lock_ack_cannot_clear_them(self) -> None:
        # frob:tests src/frob/gates/_docenum.py::docenum001_gate
        # frob:tests src/frob/gates/_negexist.py::negexist001_gate
        """DOCENUM001/NEGEXIST001 are ack-immune by construction, not by
        convention: neither gate function even accepts a `LockFile`
        parameter, so no `frob ack` -- however well-reasoned -- can reach
        into their evaluation. Acceptance criterion [2]: ack never clears a
        finding a checker can already prove true or false."""
        import inspect

        from frob.gates._docenum import docenum001_gate
        from frob.gates._negexist import negexist001_gate

        for gate_fn in (docenum001_gate, negexist001_gate):
            params = inspect.signature(gate_fn).parameters
            assert "lock" not in params, (
                f"{gate_fn.__qualname__} must never accept a LockFile -- "
                "content-verified gates are ack-immune by construction"
            )
