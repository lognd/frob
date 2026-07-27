"""Tests for frob.tickets._mutation_evidence (T-0755): the diff-scoped
adversarial evidence obligation's touched-file/test-id selection and
mutation-run orchestration."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._mutation_evidence import (
    MutationEvidenceError,
    _evidence_test_ids,
    _matches_base_ref_tip,
    _touched_python_files,
    check_ticket_mutation_evidence,
)


# frob:waive DUP001 reason="parallel per-domain test scaffolding across 9 sibling test modules \
# (9 sites) -- each file exercises a structurally similar check for \
# a distinct domain/module with the same arrange-act shape; \
# extracting would blur which domain owns which check"
def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _ticket(
    *,
    evidence: tuple[str, ...] = (),
    scope: tuple[str, ...] = ("m.py",),
    kind: TicketKind = TicketKind.BUG,
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
        scope=scope,
        evidence=evidence,
        attachments=(),
        body="## Description\nsomething\n",
    )


class TestEvidenceTestIds:
    def test_filters_non_node_id_entries(self) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestEvidenceTestIds.test_filters_non_node_id_entries  # noqa: E501
        ticket = _ticket(
            evidence=(
                "tests/test_m.py::test_add",
                "cmd:make lint exit=0 sha256=0123456789ab",
                "not-a-node-id",
            )
        )
        assert _evidence_test_ids(ticket) == ("tests/test_m.py::test_add",)

    def test_empty_when_no_evidence(self) -> None:
        assert _evidence_test_ids(_ticket(evidence=())) == ()


# frob:ticket T-0855
class TestTouchedPythonFiles:
    def test_filters_to_scope_and_python(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles.test_filters_to_scope_and_python  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (repo / "notes.md").write_text("# notes\n", encoding="utf-8")
        _commit(repo, "init")

        (repo / "m.py").write_text("def f():\n    return 2\n", encoding="utf-8")
        (repo / "notes.md").write_text("# notes changed\n", encoding="utf-8")

        ticket = _ticket(scope=("m.py",))
        files = _touched_python_files(repo, ticket, "main")
        assert files == (Path("m.py"),)

    def test_empty_when_nothing_touched(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        _commit(repo, "init")

        ticket = _ticket(scope=("m.py",))
        assert _touched_python_files(repo, ticket, "main") == ()

    # frob:ticket T-0855
    def test_already_landed_sibling_content_excluded(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles.test_already_landed_sibling_content_excluded  # noqa: E501
        """T-0855 repro: a sibling ticket committed earlier in this same
        worktree branch (`sibling.py`) has ALSO already landed separately
        onto `main`'s current tip (identical content, different commit
        history) -- the merge-base-relative diff still lists it as
        touched, but it must be excluded since nothing about it is this
        ticket's own unlanded change. A genuinely still-unlanded file
        (`m.py`) must still be reported."""
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (repo / "sibling.py").write_text("def g():\n    return 1\n", encoding="utf-8")
        _commit(repo, "init")

        # This worktree's own branch (like the agent's real worktree
        # branch): diverges from "main" here.
        _git(repo, "checkout", "-q", "-b", "feature")

        # Simulate this worktree's own earlier sibling-ticket commit.
        (repo / "sibling.py").write_text("def g():\n    return 2\n", encoding="utf-8")
        _commit(repo, "sibling ticket change")

        # Simulate the coordinator squash-applying that SAME sibling
        # change onto main INDEPENDENTLY -- a different commit (built
        # directly on "main", not a descendant of the feature-branch
        # commit above) with identical resulting content. main's tip now
        # already carries sibling.py's content, but this branch's own
        # merge-base with main is still the ORIGINAL "init" commit (git
        # cannot know the two commits share content just from history).
        _git(repo, "checkout", "-q", "main")
        (repo / "sibling.py").write_text("def g():\n    return 2\n", encoding="utf-8")
        _commit(repo, "land T-sibling")
        _git(repo, "checkout", "-q", "feature")

        # This ticket's own genuine, still-unlanded change.
        (repo / "m.py").write_text("def f():\n    return 2\n", encoding="utf-8")

        ticket = _ticket(scope=("m.py", "sibling.py"))
        files = _touched_python_files(repo, ticket, "main")
        assert files == (Path("m.py"),)

    # frob:ticket T-0855
    def test_matches_base_ref_tip_true_for_identical_content(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles.test_matches_base_ref_tip_true_for_identical_content  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        _commit(repo, "init")
        assert _matches_base_ref_tip(repo, "m.py", "main") is True

    # frob:ticket T-0855
    def test_matches_base_ref_tip_false_for_differing_content(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles.test_matches_base_ref_tip_false_for_differing_content  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        _commit(repo, "init")
        (repo / "m.py").write_text("def f():\n    return 2\n", encoding="utf-8")
        assert _matches_base_ref_tip(repo, "m.py", "main") is False


class TestCheckTicketMutationEvidence:
    def _repo_with_change(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "m.py").write_text(
            "def add(a, b):\n    return a + b\n", encoding="utf-8"
        )
        _commit(repo, "init")
        (repo / "m.py").write_text(
            "def add(a, b):\n    return a + b + 0\n", encoding="utf-8"
        )
        return repo

    def test_confirmatory_test_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_confirmatory_test_flagged  # noqa: E501
        repo = self._repo_with_change(tmp_path)
        (repo / "test_m.py").write_text(
            "import m\ndef test_add():\n    m.add(2, 3)\n", encoding="utf-8"
        )
        ticket = _ticket(evidence=("test_m.py::test_add",), scope=("m.py", "test_m.py"))
        result = check_ticket_mutation_evidence(
            repo, ticket, "main", max_mutants_per_file=4, timeout_s=30.0
        )
        assert result.is_ok, result.err
        findings = result.danger_ok
        assert len(findings) == 1
        assert findings[0].file == "m.py"
        assert findings[0].tests == ("test_m.py::test_add",)

    def test_adversarial_test_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_adversarial_test_not_flagged  # noqa: E501
        repo = self._repo_with_change(tmp_path)
        (repo / "test_m.py").write_text(
            "import m\ndef test_add():\n    assert m.add(2, 3) == 5\n",
            encoding="utf-8",
        )
        ticket = _ticket(evidence=("test_m.py::test_add",), scope=("m.py", "test_m.py"))
        result = check_ticket_mutation_evidence(
            repo, ticket, "main", max_mutants_per_file=4, timeout_s=30.0
        )
        assert result.is_ok, result.err
        assert result.danger_ok == ()

    def test_no_test_evidence_is_ok_empty(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_no_test_evidence_is_ok_empty  # noqa: E501
        repo = self._repo_with_change(tmp_path)
        ticket = _ticket(evidence=(), scope=("m.py",))
        result = check_ticket_mutation_evidence(repo, ticket, "main")
        assert result.is_ok
        assert result.danger_ok == ()

    def test_exec_disabled_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_exec_disabled_is_err  # noqa: E501
        # A refused mutant spawn (T-0803's ExecDisabled) must propagate as
        # a hard Err, not degrade to a false-clean "no findings" -- the git
        # diff itself is left untouched (working_diff succeeds normally) so
        # this isolates run_mutations' own refusal path, the thing this
        # module's Err(ExecDisabled) branch actually guards.
        import frob.tickets._mutation_evidence as mod
        from frob.mutate import MutateError

        repo = self._repo_with_change(tmp_path)
        (repo / "test_m.py").write_text(
            "import m\ndef test_add():\n    assert m.add(2, 3) == 5\n",
            encoding="utf-8",
        )
        ticket = _ticket(evidence=("test_m.py::test_add",), scope=("m.py", "test_m.py"))

        def _fake_run_mutations(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            from typani import Err

            return Err(MutateError.ExecDisabled)

        monkeypatch.setattr(mod, "run_mutations", _fake_run_mutations)
        result = check_ticket_mutation_evidence(repo, ticket, "main")
        assert result.is_err
        assert result.danger_err is MutationEvidenceError.ExecDisabled

    def test_large_file_unmutable_changed_lines_is_skipped_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_large_file_unmutable_changed_lines_is_skipped_not_flagged  # noqa: E501
        # T-0755 reviewer round 2 CRITICAL fix, reproduced directly: a
        # LARGE file (many mutable points elsewhere) whose actual DIFF
        # only touches an unmutable line (a comment) must be SKIPPED, not
        # flagged -- the pre-fix implementation mutated the first N points
        # of the WHOLE file regardless of what the diff touched, which is
        # exactly what turned this ticket's own 2-line gates/__init__.py
        # diff into a false TEST016 finding.
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Many mutable points, none of which will be touched by the diff.
        lines = [f"def f{i}(a, b):\n    return a < b and a + b\n" for i in range(20)]
        (repo / "big.py").write_text("".join(lines) + "# trailing comment\n")
        _commit(repo, "init")
        # The only change: an unmutable comment line appended at the end.
        (repo / "big.py").write_text(
            "".join(lines) + "# trailing comment, edited\n", encoding="utf-8"
        )
        (repo / "test_big.py").write_text(
            "import big\ndef test_f0():\n    big.f0(1, 2)\n", encoding="utf-8"
        )
        ticket = _ticket(
            evidence=("test_big.py::test_f0",), scope=("big.py", "test_big.py")
        )
        result = check_ticket_mutation_evidence(
            repo, ticket, "main", max_mutants_per_file=8, timeout_s=30.0
        )
        assert result.is_ok, result.err
        assert result.danger_ok == ()  # skipped, not flagged, despite a weak test

    def test_self_check_t0755_own_diff_zero_error_findings(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence.test_self_check_t0755_own_diff_zero_error_findings  # noqa: E501
        # T-0755 reviewer round 2 finding 2's mandated self-test: run the
        # REAL obligation against this repo's own T-0755 diff (this
        # worktree, base_ref=main) and assert zero ERROR-severity TEST016
        # findings -- proving the reviewer's reproduction (an unrelated
        # line in gates/__init__.py supplying every mutant for a 2-line
        # diff) is actually fixed, not just individually unit-tested.
        import os

        from frob.gates import mutation_evidence_violations
        from frob.mutate import MUTATION_RUN_ENV
        from frob.tickets import load_all

        if os.environ.get(
            MUTATION_RUN_ENV
        ):  # frob:waive SEC110 reason="mutation-harness run-mode flag, not a secret"
            # This test is itself T-0755 evidence, so the harness re-runs it
            # against every mutant; without this skip each mutant run
            # re-enters the real-repo self-check and the suite forks
            # without bound (observed 2026-07-23: orphaned full-suite
            # pytest processes self-sustaining after the driver died).
            pytest.skip("inside a mutation child run -- recursion guard")

        repo_root = Path(__file__).resolve().parents[1]
        loaded = load_all(repo_root)
        assert loaded.is_ok, loaded.err
        ticket = loaded.danger_ok.get("T-0755")
        if ticket is None or not _evidence_test_ids(ticket):
            pytest.skip("T-0755 not present/bound in this checkout's ledger")
        violations = mutation_evidence_violations(repo_root, ticket, "main")
        errors = [v for v in violations if v.severity == "error"]
        assert errors == [], [v.message for v in errors]
