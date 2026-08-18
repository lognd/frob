"""T-2462: unit tests for `frob.gates`'s new "deferred, not missing"
REL001 posture -- `_rel001_fragments_pending`/`_rel001_deferred_note`, and
`release_gate`'s plain-root-checkout branch using both to downgrade an
ERROR to a WARN when `changelog.d/` fragments (T-2445) already track a
pending bump. `frob.app.ticket_runner._close_cmd`'s companion
`_rel001_fragment_exists_for_ticket` has its own coverage in
`tests/unit/test_close_rel001_bump.py` (an existing, in-scope file for
this ticket)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates import release_gate
from frob.graph import build_graph
from frob.release import BumpClass, ReleaseManifest, stamp


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent directories."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit -- mirrors
    `tests/test_gates.py::_run`."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _snapshot(root: Path):
    """Build a fresh graph snapshot at `root`, matching `tests/test_gates.
    py::_snapshot`'s own throwaway-cache convention."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestRel001FragmentsPending:
    """`_rel001_fragments_pending`: whether `root/changelog.d/` has at
    least one parseable fragment."""

    def test_true_with_a_fragment(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestRel001FragmentsPending.test_true_with_a_fragment  # noqa: E501
        from frob.gates import _rel001_fragments_pending
        from frob.release._fragments import write_changelog_fragment

        assert write_changelog_fragment(tmp_path, "T-0001", "minor", "note").is_ok
        assert _rel001_fragments_pending(tmp_path) is True

    def test_false_with_no_fragments(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestRel001FragmentsPending.test_false_with_no_fragments  # noqa: E501
        from frob.gates import _rel001_fragments_pending

        assert _rel001_fragments_pending(tmp_path) is False

    def test_false_on_malformed_fragment(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestRel001FragmentsPending.test_false_on_malformed_fragment  # noqa: E501
        """Fail-closed: an unparseable fragment must never count as
        "tracked", the same posture `read_changelog_fragments` itself
        already takes."""
        from frob.gates import _rel001_fragments_pending

        _write(tmp_path, "changelog.d/T-0001.md", "not a valid fragment\n")
        assert _rel001_fragments_pending(tmp_path) is False


class TestRel001DeferredNote:
    """`_rel001_deferred_note`: the WARN-severity message naming the bump
    class and the deferred-via-fragments remedy."""

    def test_names_bump_and_fragment_mechanism(self) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestRel001DeferredNote.test_names_bump_and_fragment_mechanism  # noqa: E501
        from frob.gates import Severity, _rel001_deferred_note

        manifest = ReleaseManifest(version="1.0.0", api={})
        violations = _rel001_deferred_note(BumpClass.MINOR, manifest, "1.0.0")
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "REL001"
        assert v.severity == Severity.WARN
        assert "minor" in v.message
        assert "1.1.0" in v.message
        assert "changelog.d" in v.message
        assert "release cut" in v.message

    def test_empty_for_none_bump(self) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestRel001DeferredNote.test_empty_for_none_bump  # noqa: E501
        from frob.gates import _rel001_deferred_note

        manifest = ReleaseManifest(version="1.0.0", api={})
        assert _rel001_deferred_note(BumpClass.NONE, manifest, "1.0.0") == []


# frob:ticket T-2462
class TestReleaseGatePlainCheckoutDeferredPosture:
    """`release_gate`'s plain-root-checkout branch (no ticket, no lease,
    no `FROB_AGENT`): T-2462's WARN-not-ERROR downgrade when `changelog.
    d/` fragments already track a pending bump, vs the unchanged strict
    ERROR posture when nothing tracks it."""

    def test_pending_bump_with_fragment_is_warn_not_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture.test_pending_bump_with_fragment_is_warn_not_error  # noqa: E501
        from frob.gates import Severity
        from frob.release._fragments import write_changelog_fragment

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        _write(tmp_path, "CHANGELOG.md", "# Changelog\n\n## [1.0.0] - unreleased\n")
        snap = _snapshot(tmp_path)
        assert stamp(tmp_path, snap, "1.0.0").is_ok
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        # A real MINOR-class public API addition since the manifest was
        # stamped, WITH a T-2445 fragment recorded for it -- the deferred,
        # tracked case.
        _write(
            tmp_path,
            "src/a.py",
            "def a(x: int) -> int:\n    return x\ndef b() -> int:\n    return 0\n",
        )
        assert write_changelog_fragment(
            tmp_path, "T-9001", "minor", "T-9001: add b()"
        ).is_ok
        (tmp_path / ".frob" / "cache.db").unlink()
        snap2 = _snapshot(tmp_path)

        violations = release_gate(tmp_path, snap2, None)
        rel_violations = [v for v in violations if v.rule == "REL001"]
        assert rel_violations, "expected at least one REL001 note"
        assert all(v.severity == Severity.WARN for v in rel_violations)
        assert any("changelog.d" in v.message for v in rel_violations)

    def test_pending_bump_without_fragment_stays_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture.test_pending_bump_without_fragment_stays_error  # noqa: E501
        """The genuinely-missing case (a hand-edited public API change
        outside `frob ticket land`, with no fragment tracking it) must
        keep erroring exactly as before T-2462 -- nothing to defer to."""
        from frob.gates import Severity

        monkeypatch.delenv("FROB_AGENT", raising=False)
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        _write(tmp_path, "src/a.py", "def a(x: int) -> int:\n    return x\n")
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\nversion = "1.0.0"\n')
        _write(tmp_path, "CHANGELOG.md", "# Changelog\n\n## [1.0.0] - unreleased\n")
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
        rel_violations = [v for v in violations if v.rule == "REL001"]
        assert rel_violations, "expected at least one REL001 violation"
        assert any(v.severity == Severity.ERROR for v in rel_violations)
