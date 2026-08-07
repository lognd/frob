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

    # frob:ticket T-1733
    def test_evidence_weakened_and_confirmatory_refuses_outright(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_evidence_weakened_and_confirmatory_refuses_outright  # noqa: E501
        # The exact fingerprint T-1733 exists to catch: evidence was
        # rebound (evidence_changes non-empty) AND the surviving
        # evidence is confirmatory-only per TEST016. Must produce a
        # SECOND, always-ERROR TEST018 violation ON TOP of the ordinary
        # TEST016 finding, refusing outright regardless of ticket kind
        # (here FEATURE, which alone would only WARN on TEST016).
        from frob.tickets._models import EvidenceChangeEntry

        ticket = _ticket(TicketKind.FEATURE).model_copy(
            update={
                "evidence_changes": (
                    EvidenceChangeEntry(
                        old_node="tests/test_slow.py::test_watchdog",
                        new_node="test_m.py::test_add",
                        reason="test timed out locally",
                        actor="agent",
                        at=date(2026, 8, 7),
                    ),
                )
            }
        )
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        rules = [v.rule for v in violations]
        assert "TEST016" in rules
        assert "TEST018" in rules
        test018 = next(v for v in violations if v.rule == "TEST018")
        assert test018.severity == "error"

    # frob:ticket T-1733
    def test_no_evidence_changes_never_produces_test018(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_evidence_changes_never_produces_test018  # noqa: E501
        # A confirmatory finding alone (no --replace ever used on this
        # ticket) is ordinary TEST016 territory -- T-1733's outright
        # refusal is specifically about evidence that was WEAKENED, not
        # merely evidence that happens to be weak from the start.
        ticket = _ticket(TicketKind.FEATURE)
        assert ticket.evidence_changes == ()
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert [v.rule for v in violations] == ["TEST016"]

    # frob:ticket T-1733
    def test_evidence_changes_with_strong_surviving_evidence_no_test018(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_evidence_changes_with_strong_surviving_evidence_no_test018  # noqa: E501
        # Evidence WAS rebound, but the surviving evidence still kills
        # mutants (no ConfirmatoryFinding at all) -- an honest rename to
        # an equally- or more-adversarial test, not the incident this
        # rule exists to catch.
        from frob.tickets._models import EvidenceChangeEntry

        ticket = _ticket(TicketKind.FEATURE).model_copy(
            update={
                "evidence_changes": (
                    EvidenceChangeEntry(
                        old_node="test_m.py::test_add_old",
                        new_node="test_m.py::test_add",
                        reason="renamed for clarity",
                        actor="agent",
                        at=date(2026, 8, 7),
                    ),
                )
            }
        )
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
    designated_repro_test: str | None = None,
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
        designated_repro_test=designated_repro_test,
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

    def test_explicit_designation_wins_over_bind_order(self) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_wins_over_bind_order  # noqa: E501
        """T-1670: a pre-existing test bound FIRST, the real new repro
        test bound SECOND -- the exact T-1652/T-1653/T-1635 shape. Without
        an explicit designation, `test_a` (positional-first) would win;
        with one, `test_b` (the real repro) wins instead."""
        ticket = _bug_ticket(
            evidence=(
                "tests/test_a.py::test_a",
                "tests/test_b.py::test_b",
            ),
            designated_repro_test="tests/test_b.py::test_b",
        )
        assert _designated_repro_test(ticket) == "tests/test_b.py::test_b"

    def test_explicit_designation_not_in_evidence_falls_back_to_positional(
        self,
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestDesignatedReproTest.test_explicit_designation_not_in_evidence_falls_back_to_positional  # noqa: E501
        """A designation whose id was since dropped from `evidence` (e.g.
        via `--replace`) must not silently check a test no longer bound at
        all -- falls back to the ordinary positional-first rule instead."""
        ticket = _bug_ticket(
            evidence=("tests/test_a.py::test_a",),
            designated_repro_test="tests/test_stale.py::test_gone",
        )
        assert _designated_repro_test(ticket) == "tests/test_a.py::test_a"


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

    def test_same_as_head_is_vacuous(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugReproAtRef.test_same_as_head_is_vacuous  # noqa: E501
        # T-1678: a fix committed directly to main (the coordinator's flow,
        # no divergent branch) leaves HEAD and "main" pointing at the SAME
        # commit -- the exact shape that made T-1676's BUG002 message call
        # the fix commit "the parent commit" and refuse a genuinely-fixed
        # ticket. This must resolve to SAME_AS_HEAD, never a checkout+
        # subprocess run against the fix commit re-labeled as "parent".
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "README.md").write_text("placeholder\n", encoding="utf-8")
        _commit(repo, "only commit -- HEAD and main are identical")
        outcome = _bug_repro_outcome_at_ref(repo, "tests/test_x.py::test_x", "main")
        assert outcome is _BugReproOutcome.SAME_AS_HEAD


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

    def test_fix_committed_direct_to_main_is_unresolved_not_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestBugRepro.test_fix_committed_direct_to_main_is_unresolved_not_refused kind="integration"  # noqa: E501
        # T-1678, reproducing T-1676 exactly: the fix lands as a single
        # commit directly onto main (the coordinator's flow, no worktree
        # branch), so `base_ref="main"` resolves to HEAD itself -- the fix
        # commit under test. The old code ran the repro test against that
        # commit, called it "the parent commit", saw it PASS (since it IS
        # the fix), and refused with a false EvidenceConfirmatoryOnly. The
        # fixed check must report no violation at all (UNRESOLVED, not a
        # failed obligation) for a test that genuinely proves the fix.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "src").mkdir()
        (repo / "src" / "thing.py").write_text(
            "def do_the_thing() -> str:\n    return 'new'\n",
            encoding="utf-8",
        )
        (repo / "tests").mkdir()
        (repo / "tests" / "test_thing.py").write_text(
            "import sys\n"
            "sys.path.insert(0, 'src')\n"
            "import thing\n\n"
            "def test_returns_new():\n"
            "    assert thing.do_the_thing() == 'new'\n",
            encoding="utf-8",
        )
        _commit(repo, "fix: committed straight to main, no separate parent ref")
        ticket = _bug_ticket(evidence=("tests/test_thing.py::test_returns_new",))
        violations = bug_repro_violations(repo, ticket, "main")
        assert violations == ()
