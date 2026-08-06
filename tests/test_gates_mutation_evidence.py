"""Tests for frob.gates._mutation_evidence: TEST016 (T-0755) severity
resolution over `frob.tickets._mutation_evidence.check_ticket_mutation_evidence`
results, and BUG002 (T-1421) -- a bug/security ticket's designated
evidence test must genuinely FAIL at its parent commit."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import patch

from typani import Ok

from frob.gates import mutation_evidence_violations
from frob.gates._mutation_evidence import (
    _bug002_waiver_reason,
    _bug_repro_outcome_at_ref,
    _BugReproOutcome,
    _designated_repro_test,
    bug_repro_violations,
)
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._mutation_evidence import ConfirmatoryFinding
from tests.test_tickets_mutation_evidence import _commit, _git, _init_repo  # noqa: F401


def _ticket(kind: TicketKind) -> Ticket:
    return Ticket(
        id="T-0900",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=("m.py",),
        evidence=("test_m.py::test_add",),
        attachments=(),
        body="## Description\nsomething\n",
    )


_FINDING = ConfirmatoryFinding(
    ticket_id="T-0900",
    file="m.py",
    tests=("test_m.py::test_add",),
    mutants_total=2,
)


class TestMutationEvidenceViolations:
    def test_confirmatory_finding_is_warn_for_feature_kind(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_warn_for_feature_kind  # noqa: E501
        ticket = _ticket(TicketKind.FEATURE)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].rule == "TEST016"
        assert violations[0].severity == "warn"

    def test_confirmatory_finding_is_error_for_security_kind(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_error_for_security_kind  # noqa: E501
        ticket = _ticket(TicketKind.SECURITY)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].severity == "error"

    def test_confirmatory_finding_is_error_for_bug_kind(self, tmp_path: Path) -> None:
        ticket = _ticket(TicketKind.BUG)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert violations[0].severity == "error"

    def test_no_findings_no_violations(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_findings_no_violations  # noqa: E501
        ticket = _ticket(TicketKind.SECURITY)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok(()),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert violations == ()


# ---------------------------------------------------------------------------
# BUG002 (T-1421)
# ---------------------------------------------------------------------------


def _bug_ticket(
    *,
    evidence: tuple[str, ...] = ("tests/test_x.py::test_x",),
    kind: TicketKind = TicketKind.BUG,
    body: str = "## Description\nsomething\n",
) -> Ticket:
    return Ticket(
        id="T-0900",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=("m.py",),
        evidence=evidence,
        attachments=(),
        body=body,
    )


class TestBug002Waiver:
    def test_reason_present_suppresses(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_reason_present_suppresses  # noqa: E501
        body = '## Description\nsomething\nfrob:waive BUG002 reason="nondeterministic crash, cannot repro in a test"\n'  # noqa: E501
        assert _bug002_waiver_reason(_bug_ticket(body=body)) == (
            "nondeterministic crash, cannot repro in a test"
        )

    def test_bare_directive_without_reason_does_not_suppress(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBug002Waiver.test_bare_directive_without_reason_does_not_suppress  # noqa: E501
        body = "## Description\nfrob:waive BUG002\n"
        assert _bug002_waiver_reason(_bug_ticket(body=body)) is None

    def test_no_directive_at_all(self) -> None:
        assert _bug002_waiver_reason(_bug_ticket()) is None


class TestNoBehaviorChange:
    """`_no_behavior_change_reason` (T-1616): parses `frob:no-behavior-
    change reason="..."` out of a ticket's body, same shape/precedent as
    `_bug002_waiver_reason`."""

    def test_reason_present_recognized(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_reason_present_recognized  # noqa: E501
        from frob.gates._mutation_evidence import _no_behavior_change_reason

        body = (
            "## Description\npure extraction, same call order\n"
            'frob:no-behavior-change reason="split ARCH001 function, no semantic change"\n'  # noqa: E501
        )
        assert _no_behavior_change_reason(_bug_ticket(body=body)) == (
            "split ARCH001 function, no semantic change"
        )

    def test_bare_directive_without_reason_not_recognized(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestNoBehaviorChange.test_bare_directive_without_reason_not_recognized  # noqa: E501
        from frob.gates._mutation_evidence import _no_behavior_change_reason

        body = "## Description\nfrob:no-behavior-change\n"
        assert _no_behavior_change_reason(_bug_ticket(body=body)) is None

    def test_no_directive_at_all(self) -> None:
        from frob.gates._mutation_evidence import _no_behavior_change_reason

        assert _no_behavior_change_reason(_bug_ticket()) is None


class TestBugReproViolationsNoBehaviorChange:
    """BUG002's INVERTED obligation (T-1616) when `frob:no-behavior-change
    reason="..."` is present: the designated test must PASS at the parent
    (proving nothing changed there either); a genuine FAILURE at the
    parent is the violation."""

    _BODY = '## Description\nx\nfrob:no-behavior-change reason="pure extraction"\n'

    def test_passed_at_parent_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_passed_at_parent_no_violation  # noqa: E501
        ticket = _bug_ticket(body=self._BODY)
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.PASSED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert violations == ()

    def test_failed_at_parent_is_error_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_failed_at_parent_is_error_violation  # noqa: E501
        ticket = _bug_ticket(body=self._BODY)
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.FAILED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].rule == "BUG002"
        assert violations[0].severity == "error"
        assert "no-behavior-change" in violations[0].message

    def test_no_verdict_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange.test_no_verdict_no_violation  # noqa: E501
        ticket = _bug_ticket(body=self._BODY)
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.NO_VERDICT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert violations == ()


class TestDesignatedReproTest:
    def test_first_pytest_node_id_is_designated(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_first_pytest_node_id_is_designated  # noqa: E501
        ticket = _bug_ticket(
            evidence=(
                "cmd:make lint exit=0 sha256=0123456789ab",
                "tests/test_a.py::test_a",
                "tests/test_b.py::test_b",
            )
        )
        assert _designated_repro_test(ticket) == "tests/test_a.py::test_a"

    def test_no_pytest_evidence_is_none(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_no_pytest_evidence_is_none  # noqa: E501
        ticket = _bug_ticket(evidence=("cmd:make lint exit=0 sha256=0123456789ab",))
        assert _designated_repro_test(ticket) is None


class TestBugReproAtRef:
    def test_exec_disabled_is_no_verdict(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_exec_disabled_is_no_verdict  # noqa: E501
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        outcome = _bug_repro_outcome_at_ref(tmp_path, "tests/test_x.py::test_x", "main")
        assert outcome is _BugReproOutcome.NO_VERDICT

    def test_worktree_add_failure_is_no_verdict(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_worktree_add_failure_is_no_verdict  # noqa: E501
        # tmp_path is not a git repo at all -- `git worktree add` fails.
        outcome = _bug_repro_outcome_at_ref(tmp_path, "tests/test_x.py::test_x", "main")
        assert outcome is _BugReproOutcome.NO_VERDICT


class TestBugReproViolations:
    def test_non_bug_kind_never_checked(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_non_bug_kind_never_checked  # noqa: E501
        ticket = _bug_ticket(kind=TicketKind.FEATURE)
        with patch("frob.gates._mutation_evidence._bug_repro_outcome_at_ref") as mocked:
            violations = bug_repro_violations(tmp_path, ticket, "main")
        mocked.assert_not_called()
        assert violations == ()

    def test_no_pytest_evidence_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_pytest_evidence_no_violation  # noqa: E501
        ticket = _bug_ticket(evidence=("cmd:make lint exit=0 sha256=0123456789ab",))
        violations = bug_repro_violations(tmp_path, ticket, "main")
        assert violations == ()

    def test_waived_with_reason_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_waived_with_reason_no_violation  # noqa: E501
        body = (
            '## Description\nfrob:waive BUG002 reason="doc correction filed as bug"\n'  # noqa: E501
        )
        ticket = _bug_ticket(body=body)
        with patch("frob.gates._mutation_evidence._bug_repro_outcome_at_ref") as mocked:
            violations = bug_repro_violations(tmp_path, ticket, "main")
        mocked.assert_not_called()
        assert violations == ()

    def test_passed_at_parent_is_error_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_passed_at_parent_is_error_violation  # noqa: E501
        ticket = _bug_ticket()
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.PASSED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].rule == "BUG002"
        assert violations[0].severity == "error"

    def test_failed_at_parent_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_failed_at_parent_no_violation  # noqa: E501
        ticket = _bug_ticket()
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.FAILED_AT_PARENT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert violations == ()

    def test_no_verdict_no_violation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproViolations.test_no_verdict_no_violation  # noqa: E501
        ticket = _bug_ticket()
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.NO_VERDICT,
        ):
            violations = bug_repro_violations(tmp_path, ticket, "main")
        assert violations == ()


class TestBugRepro:
    """The gate itself, end to end: real git commits, no mocking of
    `_bug_repro_outcome_at_ref` -- the regression pair T-1421 requires
    (docs/guides/agent-playbook.md's WHAT SUCCESS LOOKS LIKE), reconstructed
    on the T-1384/T-1391/T-1399 shape: a guard function added and directly
    unit-tested (passes at both commits, since calling it in isolation
    always worked) versus a caller-reaching test (fails until the caller is
    actually wired up)."""

    def test_reconstructed_uncalled_guard_passes_at_both_is_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_uncalled_guard_passes_at_both_is_refused kind="integration"  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "src").mkdir()
        (repo / "src" / "guard.py").write_text(
            "def own_obligations_clean() -> bool:\n    return True\n",
            encoding="utf-8",
        )
        (repo / "tests").mkdir()
        (repo / "tests" / "test_guard.py").write_text(
            "import sys\n"
            "sys.path.insert(0, 'src')\n"
            "import guard\n\n"
            "def test_returns_true():\n"
            "    assert guard.own_obligations_clean() is True\n",
            encoding="utf-8",
        )
        _commit(repo, "parent: add own_obligations_clean, nothing calls it")
        parent = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        # "fix": still nothing calls it -- a confirmatory-only follow-up,
        # the exact T-1384 shape.
        (repo / "src" / "guard.py").write_text(
            "def own_obligations_clean() -> bool:\n    return True  # unchanged\n",
            encoding="utf-8",
        )
        _commit(repo, "fix: still no caller")
        ticket = _bug_ticket(evidence=("tests/test_guard.py::test_returns_true",))
        violations = bug_repro_violations(repo, ticket, parent)
        assert len(violations) == 1
        assert violations[0].rule == "BUG002"

    def test_reconstructed_wired_guard_fails_at_parent_is_permitted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_reconstructed_wired_guard_fails_at_parent_is_permitted kind="integration"  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "src").mkdir()
        (repo / "src" / "guard.py").write_text(
            "def own_obligations_clean() -> bool:\n    return True\n",
            encoding="utf-8",
        )
        (repo / "src" / "caller.py").write_text(
            "def do_the_thing() -> str:\n    return 'old'\n",
            encoding="utf-8",
        )
        (repo / "tests").mkdir()
        (repo / "tests" / "test_caller.py").write_text(
            "import sys\n"
            "sys.path.insert(0, 'src')\n"
            "import caller\n\n"
            "def test_uses_guard():\n"
            "    assert caller.do_the_thing() == 'new'\n",
            encoding="utf-8",
        )
        _commit(repo, "parent: caller ignores guard")
        parent = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        # fix: caller actually wired to the guard now.
        (repo / "src" / "caller.py").write_text(
            "import guard\n\n"
            "def do_the_thing() -> str:\n"
            "    return 'new' if guard.own_obligations_clean() else 'old'\n",
            encoding="utf-8",
        )
        _commit(repo, "fix: caller wired to guard")
        ticket = _bug_ticket(evidence=("tests/test_caller.py::test_uses_guard",))
        violations = bug_repro_violations(repo, ticket, parent)
        assert violations == ()
