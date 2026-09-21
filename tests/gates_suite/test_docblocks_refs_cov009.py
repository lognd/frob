"""T-4254: COV009 -- symbols sharing one `frob:doc` anchor are one shared
contract. Consumer F-386 item 4's finding: a shared contract's fix and
its miss landed in two different tickets' scopes because frob had no
notion that these call sites implement one thing -- the `frob:doc` edges
all pointed at the same anchor, which is the right grouping hook.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._docblocks_refs import (
    _shared_doc_anchor_groups,
    cov009_violations,
)
from frob.gitio import Diff, Hunk
from tests.conftest import _snapshot, _write


def _diff(*hunks: Hunk) -> Diff:
    """A `Diff` fixture built directly from `hunks` -- COV009's own
    evaluator (`cov009_violations`) is pure over `(snapshot, diff)`, so
    tests never need a real git working tree to exercise it."""
    return Diff(base="0" * 40, hunks=hunks)


class TestSharedDocAnchorGrouping:
    """`_shared_doc_anchor_groups` -- the grouping helper in isolation."""

    def test_two_symbols_same_anchor_form_a_group(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#shared\ndef foo():\n    pass\n",
        )
        _write(
            tmp_path,
            "pkg/b.py",
            "# frob:doc docs/x.md#shared\ndef bar():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        groups = _shared_doc_anchor_groups(snapshot)
        assert groups.get("docs/x.md#shared") == (
            "pkg/a.py::foo",
            "pkg/b.py::bar",
        )

    def test_lone_anchor_participant_is_not_a_group(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#solo\ndef foo():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        assert "docs/x.md#solo" not in _shared_doc_anchor_groups(snapshot)


class TestCov009SharedAnchorReview:
    """`cov009_violations` -- the end-to-end diff-driven gate."""

    def test_touching_one_sibling_flags_the_other(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#shared\ndef foo():\n    pass\n",
        )
        _write(
            tmp_path,
            "pkg/b.py",
            "# frob:doc docs/x.md#shared\ndef bar():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        # Touch only pkg/a.py::foo's own line span (line 2).
        diff = _diff(Hunk(file="pkg/a.py", span=(2, 2)))
        violations = cov009_violations(snapshot, diff)
        assert len(violations) == 1
        assert violations[0].rule == "COV009"
        assert violations[0].file == "pkg/b.py"
        assert "pkg/a.py::foo" in violations[0].message

    def test_touching_both_siblings_flags_neither(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#shared\ndef foo():\n    pass\n",
        )
        _write(
            tmp_path,
            "pkg/b.py",
            "# frob:doc docs/x.md#shared\ndef bar():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        diff = _diff(
            Hunk(file="pkg/a.py", span=(2, 2)),
            Hunk(file="pkg/b.py", span=(2, 2)),
        )
        violations = cov009_violations(snapshot, diff)
        assert violations == ()

    def test_untouched_group_is_silent(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#shared\ndef foo():\n    pass\n",
        )
        _write(
            tmp_path,
            "pkg/b.py",
            "# frob:doc docs/x.md#shared\ndef bar():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        diff = _diff(Hunk(file="pkg/unrelated.py", span=(1, 1)))
        violations = cov009_violations(snapshot, diff)
        assert violations == ()

    def test_lone_anchor_participant_is_not_a_group(self, tmp_path: Path) -> None:
        """A symbol with no sibling sharing its anchor never fires, even
        when this diff touches it directly."""
        _write(
            tmp_path,
            "pkg/a.py",
            "# frob:doc docs/x.md#solo\ndef foo():\n    pass\n",
        )
        snapshot = _snapshot(tmp_path)
        diff = _diff(Hunk(file="pkg/a.py", span=(2, 2)))
        violations = cov009_violations(snapshot, diff)
        assert violations == ()
