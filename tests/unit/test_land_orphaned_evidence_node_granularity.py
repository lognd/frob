"""T-2060: `_check_orphaned_evidence_deletion`/`_orphaned_
evidence_findings` matched at FILE granularity only, so a landing
branch that touches a shared test file for an UNRELATED reason got
refused for another ticket's evidence that was already broken by an
earlier, independent main commit -- the reported incident was T-1959's
land refusing over a node deleted by `7597ba37a`, long before T-1959's
worktree existed.

Fix: a file-level candidate is only flagged if the specific test node
actually existed (syntactically, at the landing branch's own merge-base)
before being narrowed by `_test_node_existed_at_ref`. A node already
absent at merge-base is pre-existing breakage, never this branch's own
deletion.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.testing._models import CollectedTests
from frob.tickets._land import (
    _orphaned_evidence_findings,
    _test_node_existed_at_ref,
    _true_merge_base,
)
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / "tests").mkdir()


def _write_foo(root: Path, body: str) -> None:
    (root / "tests" / "test_foo.py").write_text(body)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


_ONLY_STILL_HERE = "class TestFoo:\n    def test_still_here(self):\n        pass\n"
_PLUS_UNRELATED = (
    "class TestFoo:\n"
    "    def test_still_here(self):\n"
    "        pass\n\n"
    "    def test_new_one(self):\n"
    "        pass\n"
)
_WITH_TARGET = (
    "class TestFoo:\n"
    "    def test_still_here(self):\n"
    "        pass\n\n"
    "    def test_real_deletion_target(self):\n"
    "        pass\n"
)


def _other_ticket(evidence_id: str, ticket_id: str = "T-0500") -> Ticket:
    return Ticket(
        id=ticket_id,
        title="other ticket",
        state=TicketState.DONE,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        created=date(2026, 1, 1),
        evidence=(evidence_id,),
    )


class TestTestNodeExistedAtRef:
    """Direct tests of the new syntactic presence-check primitive."""

    def test_absent_node_reports_false(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef.test_absent_node_reports_false  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "base without test_long_gone")

        result = _test_node_existed_at_ref(
            root, "HEAD", "tests/test_foo.py::TestFoo::test_long_gone"
        )
        assert result is False

    def test_present_node_reports_true(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef.test_present_node_reports_true  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _WITH_TARGET)
        _commit_all(root, "with target")

        result = _test_node_existed_at_ref(
            root, "HEAD", "tests/test_foo.py::TestFoo::test_real_deletion_target"
        )
        assert result is True

    def test_unreadable_ref_reports_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef.test_unreadable_ref_reports_none  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "base")

        result = _test_node_existed_at_ref(
            root, "deadbeef" * 5, "tests/test_foo.py::TestFoo::test_still_here"
        )
        assert result is None

    def test_evidence_with_no_double_colon_reports_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestTestNodeExistedAtRef.test_evidence_with_no_double_colon_reports_none  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "base")

        result = _test_node_existed_at_ref(root, "HEAD", "tests/test_foo.py")
        assert result is None


class TestOrphanedEvidenceFindingsNodeGranularity:
    """FAILS FIRST: `_orphaned_evidence_findings` called with no `worktree`/
    `merge_base` (the OLD, pre-fix call shape every existing caller used)
    reproduces the exact reported incident -- flags a node that was
    already gone before the landing branch's own commits, purely because
    the containing file is in `changed_paths` for an unrelated edit."""

    def test_file_level_only_call_reproduces_the_incident(self) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity.test_file_level_only_call_reproduces_the_incident  # noqa: E501
        """No `worktree`/`merge_base` given -- the OLD call shape.
        Documents the pre-fix behavior stays reachable (a caller with no
        merge-base to offer degrades to it), NOT a claim that this shape
        is still correct on its own."""
        other = _other_ticket("tests/test_foo.py::TestFoo::test_long_gone")
        changed_paths = frozenset({"tests/test_foo.py"})
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_foo.py::TestFoo::test_still_here"})
        )

        orphaned = _orphaned_evidence_findings(
            "T-1959", {"T-0500": other}, changed_paths, tests
        )
        assert orphaned == {"T-0500": ["tests/test_foo.py::TestFoo::test_long_gone"]}

    def test_node_level_narrowing_clears_a_pre_existing_absence(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity.test_node_level_narrowing_clears_a_pre_existing_absence  # noqa: E501
        """THE FIX: with `worktree`/`merge_base` given, the same file-
        level candidate as above is NOT flagged, because the node was
        already absent at the landing branch's own merge-base -- the
        T-1959/`7597ba37a` incident's exact shape, reproduced against a
        real git repo, not a mock."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "base without test_long_gone")
        _run(["git", "checkout", "-q", "-b", "feature"], root)
        _write_foo(root, _PLUS_UNRELATED)
        _commit_all(root, "add an unrelated test in the same file")

        merge_base = _true_merge_base(root, "main")
        assert merge_base.is_ok, merge_base

        other = _other_ticket("tests/test_foo.py::TestFoo::test_long_gone")
        changed_paths = frozenset({"tests/test_foo.py"})
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_foo.py::TestFoo::test_still_here",
                    "tests/test_foo.py::TestFoo::test_new_one",
                }
            )
        )

        orphaned = _orphaned_evidence_findings(
            "T-1959",
            {"T-0500": other},
            changed_paths,
            tests,
            root,
            merge_base.danger_ok,
        )
        assert orphaned == {}

    def test_a_genuine_this_branch_deletion_still_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity.test_a_genuine_this_branch_deletion_still_refuses  # noqa: E501
        """No over-reach: when the landing branch's OWN diff is what
        removed the node (it existed at merge-base, is gone at HEAD),
        the refusal must still fire exactly as before."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _WITH_TARGET)
        _commit_all(root, "base with target")
        _run(["git", "checkout", "-q", "-b", "feature"], root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "delete test_real_deletion_target")

        merge_base = _true_merge_base(root, "main")
        assert merge_base.is_ok, merge_base

        other = _other_ticket("tests/test_foo.py::TestFoo::test_real_deletion_target")
        changed_paths = frozenset({"tests/test_foo.py"})
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_foo.py::TestFoo::test_still_here"})
        )

        orphaned = _orphaned_evidence_findings(
            "T-1959",
            {"T-0500": other},
            changed_paths,
            tests,
            root,
            merge_base.danger_ok,
        )
        assert orphaned == {
            "T-0500": ["tests/test_foo.py::TestFoo::test_real_deletion_target"]
        }

    def test_merge_base_lookup_failure_falls_back_to_file_level(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_orphaned_evidence_node_granularity.py::TestOrphanedEvidenceFindingsNodeGranularity.test_merge_base_lookup_failure_falls_back_to_file_level  # noqa: E501
        """`merge_base=None` (the caller's own lookup failed) degrades to
        the OLD, more conservative file-level-only behavior rather than
        silently passing -- never worse than before this fix, only
        better when merge-base IS available."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_foo(root, _ONLY_STILL_HERE)
        _commit_all(root, "base")

        other = _other_ticket("tests/test_foo.py::TestFoo::test_long_gone")
        changed_paths = frozenset({"tests/test_foo.py"})
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_foo.py::TestFoo::test_still_here"})
        )

        orphaned = _orphaned_evidence_findings(
            "T-1959", {"T-0500": other}, changed_paths, tests, root, None
        )
        assert orphaned == {"T-0500": ["tests/test_foo.py::TestFoo::test_long_gone"]}
