import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.gates import (
    GateConfig,
    Severity,
    debt_gate,
    deprecated_current_references,
    deprecated_gate,
    list_debt,
    list_deprecated,
    run_gates,
)
from frob.gates._deprecated_baseline import (
    DeprecatedBaselineEntry,
    DeprecatedBaselineLock,
    save_deprecated_baseline,
)
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
from frob.tickets._store import write_ticket
from tests.conftest import (
    _first_rule,
    _git_init,
    _rules,
    _run,
    _snapshot,
    _ticket,
    _write,
    _write_ticket,
)


# frob:ticket T-0731
# frob:ticket T-0601
class TestDebtGate:
    """T-0412: frob:debt vs frob:waive -- malformed directive (DEBT001),
    non-open ticket (DEBT002), expired until boundary (DEBT003)."""

    def test_debt002_closed_ticket_is_reported(self, tmp_path: Path) -> None:
        """T-0412: a frob:debt bound to a closed ticket is DEBT002 -- a debt
        must point at real, OPEN, owed work."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt002_closed_ticket_is_re\
        # ported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT002")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_debt002_open_ticket_is_silent(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt002_open_ticket_is_sile\
        # nt
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert not any(v.rule == "DEBT002" for v in violations)

    def test_debt003_expired_by_date_is_reported(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt003_expired_by_date_is_\
        # reported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2026-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-06-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT003")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_debt003_not_yet_expired_is_silent(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt003_not_yet_expired_is_\
        # silent
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert not any(v.rule == "DEBT003" for v in violations)

    def test_debt003_expired_by_version_is_reported(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt003_expired_by_version_\
        # is_reported
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="1.0.0"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="1.2.0"
        )
        v = _first_rule(violations, "DEBT003")
        assert v is not None

    def test_debt001_malformed_directive_is_reported(self, tmp_path: Path) -> None:
        """T-0412: frob:debt requires BOTH reason= and ticket= -- missing
        either is DEBT001, mirroring WAIVE001's shape for frob:waive."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_debt001_malformed_directive\
        # _is_reported
        source = 'def helper(x):\n    # frob:debt TEST005 reason="coverage gap"\n    return x\n'
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        v = _first_rule(violations, "DEBT001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "ticket" in v.message

    def test_clean_debt_produces_no_violations(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_clean_debt_produces_no_viol\
        # ations
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = debt_gate(
            snap, queue, current_date="2026-01-01", current_version="0.1.0"
        )
        assert violations == ()

    def test_lists_every_debt_entry(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_lists_every_debt_entry
        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001" '
            'until="2099-01-01"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        entries = list_debt(snap, current_date="2026-01-01", current_version="0.1.0")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.rule == "TEST005"
        assert entry.ticket == "T-0001"
        assert entry.until == "2099-01-01"
        assert entry.expired is False

    def test_release_gate_fails_while_debt_is_open(self, tmp_path: Path) -> None:
        """T-0412's central requirement: a release must never ship with ANY
        open frob:debt, expired or not."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_release_gate_fails_while_de\
        # bt_is_open
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:debt TEST005 reason="coverage gap" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert any(v.rule == "REL001" and "frob:debt" in v.message for v in violations)

    # frob:ticket T-0731
    def test_release_gate_bump_fires_without_frob_agent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0731: with `FROB_AGENT` unset (a coordinator shell), REL001
        still demands the version bump exactly as before."""
        # frob:tests tests/gates_suite/test_debt.py::TestDebtGate.test_release_gate_bump_fires_without_frob_agent  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)
        violations = release_gate(tmp_path, snap2)
        assert any(
            v.rule == "REL001" and "public API changed" in v.message for v in violations
        )

    # frob:ticket T-0731
    def test_release_gate_bump_suppressed_under_frob_agent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0731: with `FROB_AGENT` set (every dispatched worktree agent),
        the version-bump/changelog half of REL001 is suppressed -- the
        bump is a land-time step `frob ticket land` computes, never
        something an agent must do itself."""
        # frob:tests tests/gates_suite/test_debt.py::TestDebtGate.test_release_gate_bump_suppressed_under_frob_agent  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        monkeypatch.setenv("FROB_AGENT", "test-agent-1")
        violations = release_gate(tmp_path, snap2)
        assert not any(
            v.rule == "REL001" and "public API changed" in v.message for v in violations
        )
        assert not any(
            v.rule == "REL001" and "no CHANGELOG.md entry" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_not_land_owned_root_checkout_no_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a plain root-checkout `frob check` run (real git repo, no
        `--ticket`, no live lease, `FROB_AGENT` unset) is NOT land-owned --
        REL001 still errors exactly as before T-0807."""
        # frob:tests tests/gates_suite/test_debt.py::TestDebtGate.test_rel001_not_land_owned_root_checkout_no_ticket  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        violations = release_gate(tmp_path, snap2, None)
        assert any(
            v.rule == "REL001"
            and v.severity is Severity.ERROR
            and "public API changed" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_land_owned_via_linked_worktree_no_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a check run from a LINKED worktree is land-owned even
        with no `--ticket` in play -- the bump reports as an informational
        `WARN`, never an `ERROR`."""
        # frob:tests tests/gates_suite/test_debt.py::TestDebtGate.test_rel001_land_owned_via_linked_worktree_no_ticket  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        monkeypatch.delenv("FROB_AGENT", raising=False)
        main_root = tmp_path / "main"
        main_root.mkdir()
        _run(["git", "init", "-q", "-b", "main"], main_root)
        _run(["git", "config", "user.email", "test@example.com"], main_root)
        _run(["git", "config", "user.name", "Test"], main_root)
        _write(main_root, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(
            main_root, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n'
        )
        snap = _snapshot(main_root)
        assert stamp(main_root, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], main_root)
        _run(["git", "commit", "-q", "-m", "init"], main_root)

        worktree_root = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-q", "-b", "T-0807-wt", str(worktree_root)],
            main_root,
        )
        _write(
            worktree_root,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        snap2 = _snapshot(worktree_root)

        violations = release_gate(worktree_root, snap2, None)
        assert not any(
            v.rule == "REL001" and v.severity is Severity.ERROR for v in violations
        )
        # T-0894 review fix: the note must name the TARGET version (>= 1.1.0
        # for a minor bump off 1.0.0), not just the bump class -- a reviewer
        # otherwise sees "public API changed (minor)" with no idea what
        # `frob ticket land` will actually bump to.
        assert any(
            v.rule == "REL001"
            and v.severity is Severity.WARN
            and "public API changed" in v.message
            and "land will bump to >= 1.1.0" in v.message
            for v in violations
        )

    # frob:ticket T-0807
    # frob:ticket T-0601
    def test_rel001_land_owned_via_ticket_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0807: a check run with `--ticket T-XXXX` whose lease pins to
        THIS root (no linked worktree required -- e.g. a single-checkout
        repo with an in-progress ticket) is also land-owned via the lease."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_rel001_land_owned_via_ticke\
        # t_lease
        from frob.gates import release_gate
        from frob.release import stamp
        from frob.tickets._leases import _LeaseRecord, leases_dir

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        leases_root_result = leases_dir(tmp_path)
        assert leases_root_result.is_ok
        leases_root = leases_root_result.danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        record = _LeaseRecord(
            ticket_id="T-0900",
            scope=("src/a.py",),
            worktree=str(tmp_path.resolve()),
            branch="main",
            recorded_at="2026-07-23T00:00:00+00:00",
        )
        (leases_root / "T-0900.json").write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        violations = release_gate(tmp_path, snap2, "T-0900")
        assert not any(
            v.rule == "REL001" and v.severity is Severity.ERROR for v in violations
        )
        assert any(
            v.rule == "REL001" and v.severity is Severity.WARN for v in violations
        )

    # frob:ticket T-0807
    def test_rel001_linked_worktree_detected(self, tmp_path: Path) -> None:
        """T-0807: `_rel001_is_linked_worktree` is `True` for a linked
        worktree and `False` for the main checkout it was created from."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDebtGate.test_rel001_linked_worktree_dete\
        # cted
        from frob.gates import _rel001_is_linked_worktree

        main_root = tmp_path / "main"
        main_root.mkdir()
        _run(["git", "init", "-q", "-b", "main"], main_root)
        _run(["git", "config", "user.email", "test@example.com"], main_root)
        _run(["git", "config", "user.name", "Test"], main_root)
        (main_root / "README.md").write_text("x\n", encoding="utf-8")
        _run(["git", "add", "-A"], main_root)
        _run(["git", "commit", "-q", "-m", "init"], main_root)

        worktree_root = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-q", "-b", "T-0807-detect", str(worktree_root)],
            main_root,
        )

        assert _rel001_is_linked_worktree(main_root) is False
        assert _rel001_is_linked_worktree(worktree_root) is True


# frob:ticket T-2581
class TestReleaseOpenMilestoneViolations:
    """`_release_open_milestone_violations(root, release_version)`
    (T-2581 M6): REL001 must refuse to cut a release while any OPEN
    ticket still carries that (effective) milestone, and must name every
    blocking ticket by id -- never a bare count."""

    def _milestone_ticket(
        self,
        *,
        ticket_id: str,
        state: TicketState = TicketState.QUEUED,
        milestone: str | None = None,
    ) -> Ticket:
        """Minimal `Ticket` fixture carrying a `milestone` field -- this
        file's own shared `_ticket` helper predates M1 (T-2574) and has
        no `milestone` parameter; kept as a small local twin rather than
        widening that helper's signature for every one of its many other
        call sites."""
        return Ticket(
            id=ticket_id,
            title="Sample",
            state=state,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nx\n\n## Done report\ndone\n",
            milestone=milestone,
        )

    def test_open_ticket_in_cut_milestone_refuses(self, tmp_path: Path) -> None:
        """Positive control: an OPEN ticket declares the exact milestone
        being cut -- REL001 must fire, naming the ticket."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        t = self._milestone_ticket(ticket_id="T-0001", milestone="1.0.0")
        write_ticket(tmp_path, t).danger_ok
        violations = _release_open_milestone_violations(tmp_path, "1.0.0")
        assert len(violations) == 1
        assert violations[0].rule == "REL001"
        assert "T-0001" in violations[0].message
        assert "1.0.0" in violations[0].message

    def test_open_ticket_in_other_milestone_does_not_refuse(
        self, tmp_path: Path
    ) -> None:
        """Negative control: the open ticket's milestone does not match
        the release being cut -- must succeed (no violation)."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        t = self._milestone_ticket(ticket_id="T-0001", milestone="2.0.0")
        write_ticket(tmp_path, t).danger_ok
        assert _release_open_milestone_violations(tmp_path, "1.0.0") == ()

    def test_terminal_ticket_in_cut_milestone_does_not_refuse(
        self, tmp_path: Path
    ) -> None:
        """A DONE ticket in the cut milestone is not a live blocker --
        it already shipped its own work."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        t = self._milestone_ticket(
            ticket_id="T-0001", milestone="1.0.0", state=TicketState.DONE
        )
        write_ticket(tmp_path, t).danger_ok
        assert _release_open_milestone_violations(tmp_path, "1.0.0") == ()

    def test_no_open_tickets_in_milestone_succeeds(self, tmp_path: Path) -> None:
        """Explicit acceptance case: a release cut with no open tickets in
        that milestone at all must succeed (empty queue)."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        assert _release_open_milestone_violations(tmp_path, "1.0.0") == ()

    def test_names_every_blocking_ticket(self, tmp_path: Path) -> None:
        """Two separate open tickets in the cut milestone -- the refusal
        must name BOTH, not just report that something blocks."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        a = self._milestone_ticket(ticket_id="T-0001", milestone="1.0.0")
        b = self._milestone_ticket(ticket_id="T-0002", milestone="1.0.0")
        write_ticket(tmp_path, a).danger_ok
        write_ticket(tmp_path, b).danger_ok
        violations = _release_open_milestone_violations(tmp_path, "1.0.0")
        assert len(violations) == 1
        assert "T-0001" in violations[0].message
        assert "T-0002" in violations[0].message

    def test_queue_unavailable_does_not_crash(self, tmp_path: Path) -> None:
        """A queue-load failure degrades to "skip this check", never a
        hard crash of the whole release gate -- write a malformed ledger
        file that `load_queue` cannot parse."""
        from frob.gates._debt_deprecated import _release_open_milestone_violations

        (tmp_path / "tickets.md").write_text(
            "not a valid ticket ledger at all: [[[", encoding="utf-8"
        )
        assert _release_open_milestone_violations(tmp_path, "1.0.0") == ()


class TestDeprecatedGate:
    """T-0576: frob:deprecated -- frob:debt generalized to a public API's
    own sunset. Malformed directive (DEPR001), non-open ticket (DEPR002),
    still-in-window warning (DEPR003), past-sunset error (DEPR004)."""

    def test_depr001_malformed_directive_is_reported(self, tmp_path: Path) -> None:
        """T-0576: frob:deprecated requires BOTH sunset= and ticket= --
        missing either is DEPR001, mirroring DEBT001's shape."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr001_malformed_directive_is_reported  # noqa: E501
        source = 'def helper(x):\n    # frob:deprecated 0.1.0 ticket="T-0001"\n    return x\n'
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR001")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "sunset" in v.message

    def test_depr001_malformed_sunset_is_reported(self, tmp_path: Path) -> None:
        """T-0576: a `sunset=` that is not a YYYY-MM-DD date is also DEPR001."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr001_malformed_sunset_is_reported  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="soon" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR001")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_depr002_closed_ticket_is_reported(self, tmp_path: Path) -> None:
        """T-0576: a frob:deprecated bound to a closed ticket is DEPR002 --
        the ticket closed but the directive (presumably the symbol) is
        still here."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr002_closed_ticket\
        # _is_reported
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR002")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert not any(v.rule in ("DEPR003", "DEPR004") for v in violations)

    def test_depr003_in_window_warns(self, tmp_path: Path) -> None:
        """T-0576: an open, not-yet-sunset frob:deprecated is a WARNING --
        visible, but does not fail `frob check`."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr003_in_window_war\
        # ns
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR003")
        assert v is not None
        assert v.severity == Severity.WARN
        assert not any(v.rule == "DEPR004" for v in violations)

    def test_depr003_survives_repo_severity_overrides(self, tmp_path: Path) -> None:
        """T-3912: `_depr003_violations` computes `Severity.WARN`, but
        `frob.toml`'s `[gates.severity]` table can re-severity ANY rule
        after the fact (`_apply_severity_overrides`) -- so the gate being
        right is not sufficient on its own; the config must agree. A
        `DEPR003 = "error"` override forces an in-window deprecation to
        ERROR on every run, contradicting the sunset-window contract this
        rule exists to provide (T-3906 hit this live: a fresh, far-future
        `frob:deprecated` failed `frob check` the day it was added). Locks
        that an override forcing DEPR003 to error round-trips as ERROR
        (the mechanism works), so a regression of the opposite kind --
        this repo's OWN `frob.toml` drifting back to `DEPR003 = "error"`
        -- is caught by `test_depr003_not_forced_to_error_in_this_repo`
        below rather than by this generic mechanism check."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr003_survives_repo\
        # _severity_overrides
        from frob.gates._waive import _apply_severity_overrides

        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(
            tmp_path,
            "frob.toml",
            '[gates.severity]\nDEPR003 = "error"\n',
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        overridden = _apply_severity_overrides(violations, tmp_path)
        v = _first_rule(overridden, "DEPR003")
        assert v is not None
        assert v.severity == Severity.ERROR

    def test_depr003_not_forced_to_error_in_this_repo(self) -> None:
        """T-3912: this repo's own `frob.toml` must not re-force DEPR003
        to error -- that config is exactly what turned a documented WARN
        (a deprecation still inside its sunset window) into a hard `frob
        check` failure the day the first live `frob:deprecated` directive
        (T-3906) was added, with no code change and no expiry involved.
        DEPR004 (past-sunset escalation) is unaffected and stays error."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr003_not_forced_to\
        # _error_in_this_repo
        from frob.gates._waive import _severity_overrides

        repo_root = Path(__file__).resolve().parents[2]
        overrides = _severity_overrides(repo_root)
        assert overrides.get("DEPR003") != Severity.ERROR
        assert overrides.get("DEPR004") == Severity.ERROR

    def test_depr004_past_sunset_errors(self, tmp_path: Path) -> None:
        """T-0576: an open frob:deprecated past its sunset date escalates
        from a warning to DEPR004, an ERROR."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr004_past_sunset_e\
        # rrors
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2026-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-06-01")
        v = _first_rule(violations, "DEPR004")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert not any(v.rule == "DEPR003" for v in violations)

    def test_clean_deprecated_produces_no_violations(self, tmp_path: Path) -> None:
        """T-0576: a well-formed, open, still-in-window deprecation whose
        ticket is open produces only the DEPR003 warning, nothing else."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_clean_deprecated_produces_no_violations  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        assert _rules(violations) == ["DEPR003"]

    def test_lists_every_deprecated_entry(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_lists_every_deprecate\
        # d_entry
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        entries = list_deprecated(snap, current_date="2026-01-01")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.since == "0.1.0"
        assert entry.ticket == "T-0001"
        assert entry.sunset == "2099-01-01"
        assert entry.expired is False

    def test_depr005_reference_set_combines_consumers_and_xref(
        self, tmp_path: Path
    ) -> None:
        """T-0639: `deprecated_current_references` sees both an import-line
        consumer and a plain identifier usage, and excludes the symbol's own
        defining file."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr005_reference_set_combines_consumers_and_xref  # noqa: E501
        _write(tmp_path, "src/lib.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "src/importer.py",
            "from lib import helper\nhelper(1)\n",
        )
        _write(tmp_path, "src/mentioner.py", "y = helper(2)\n")
        refs = deprecated_current_references("helper", tmp_path)
        assert any(r.endswith("importer.py:1") for r in refs)
        assert not any(r.startswith("lib.py") or "/lib.py" in r for r in refs)

    def test_depr005_new_caller_errors(self, tmp_path: Path) -> None:
        """T-0639: a `frob:deprecated` symbol with a baselined entry that
        omits a currently-observed reference fires DEPR005, naming the new
        call site."""
        # frob:tests \
        # tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr005_new_caller_er\
        # rors
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "src/caller.py", "from a import helper\nhelper(1)\n")
        save_deprecated_baseline(
            tmp_path,
            DeprecatedBaselineLock(
                entries=(
                    DeprecatedBaselineEntry(symbol="src/a.py::helper", references=()),
                )
            ),
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        v = _first_rule(violations, "DEPR005")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert v.file.endswith("caller.py")
        assert "src/a.py::helper" in v.message

    def test_depr005_no_baseline_entry_is_silent(self, tmp_path: Path) -> None:
        """T-0639: a deprecated symbol never baselined fires no DEPR005 --
        seeding, not flagging, is `tighten_deprecated_baseline`'s job."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_depr005_no_baseline_entry_is_silent  # noqa: E501
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "src/caller.py", "from a import helper\nhelper(1)\n")
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = deprecated_gate(snap, queue, tmp_path, current_date="2026-01-01")
        assert not any(v.rule == "DEPR005" for v in violations)

    def test_release_gate_fails_while_deprecated_is_past_sunset(
        self, tmp_path: Path
    ) -> None:
        """T-0576: a release must never ship while a frob:deprecated is past
        its sunset -- unlike frob:debt, a still-in-window one does not
        block a release."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_release_gate_fails_while_deprecated_is_past_sunset  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2020-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert any(
            v.rule == "REL001" and "frob:deprecated" in v.message for v in violations
        )

    def test_release_gate_silent_while_deprecated_in_window(
        self, tmp_path: Path
    ) -> None:
        """T-0576: unlike frob:debt (blocks release for ANY open debt), a
        deprecation still inside its warning window does not block a
        release."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_release_gate_silent_while_deprecated_in_window  # noqa: E501
        from frob.gates import release_gate
        from frob.release import stamp

        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "0.1.0").is_ok
        violations = release_gate(tmp_path, snap)
        assert not any(
            v.rule == "REL001" and "frob:deprecated" in v.message for v in violations
        )

    def test_deprecated_is_registered_in_all_gates(self) -> None:
        """T-0797: DEPR001-004 were implemented (T-0576) but 'deprecated' was
        never added to `_ALL_GATES`, so no real `frob check` run ever
        evaluated them (catalogued-is-not-enforced). Locks the registration
        so this cannot silently regress again."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_deprecated_is_registered_in_all_gates  # noqa: E501
        from frob.gates import _ALL_GATES

        assert "deprecated" in _ALL_GATES

    def test_deprecated_fires_through_real_gate_dispatch(self, tmp_path: Path) -> None:
        """T-0797: an end-to-end `run_gates` pass (no `--only` filter, the
        default gate selection) over a `frob:deprecated` directive still
        inside its warning window must surface DEPR003 -- proving the gate
        is actually wired into dispatch, not just callable in isolation."""
        # frob:tests tests/gates_suite/test_debt.py::TestDeprecatedGate.test_deprecated_fires_through_real_gate_dispatch  # noqa: E501
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(state=TicketState.QUEUED))
        source = (
            "def helper(x):\n"
            '    # frob:deprecated 0.1.0 sunset="2099-01-01" ticket="T-0001"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add file"], cwd=tmp_path, check=True
        )
        cfg = GateConfig(root=str(tmp_path), base="main")
        result = run_gates(cfg)
        assert result.is_ok
        report = result.danger_ok
        v = _first_rule(report.violations, "DEPR003")
        assert v is not None
        assert v.severity == Severity.WARN
