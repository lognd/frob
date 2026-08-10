"""Unit tests for `frob.verify._attribution` (T-1690): symbolic
attribution of a red batch's findings to the commit that caused them."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.graph import CallGraph, GraphSnapshot
from frob.verify._attribution import (
    AttributionError,
    attribute_batch,
    build_ad_hoc_batch,
)
from tests.unit.verify.conftest import make_queue_entry, make_symbol


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="the same tiny init-a-throwaway-git-repo-for-a-test helper \
# already exists verbatim in a dozen+ test files across this repo (test_gitio.py, \
# test_docblocks_gate.py, test_refs_gate.py, ...) -- an established, accepted \
# repo-wide test-fixture pattern, not a fresh duplication this ticket introduced; \
# consolidating it into one shared helper is a real repo-wide test-hygiene cleanup, \
# out of T-2018's own narrow attribution-reachability scope"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


class TestAttributeBatch:
    """The graph-reachability rule: a finding attributes to the batch
    commit whose touched symbols REACH it, never a lexical file match or
    a newest-commit tiebreak."""

    def test_caller_break_attributes_to_the_caller_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_caller_break_attributes_to_the_caller_commit  # noqa: E501
        # Commit A touches `caller`, which calls `callee` -- commit B
        # touched `callee` itself, unrelated to the finding. The finding
        # is anchored at `caller` (a broken caller, not the callee), so it
        # must attribute to A, not B.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::caller": make_symbol("a.py", "caller", 1, 5),
                "b.py::callee": make_symbol("b.py", "callee", 1, 5),
            },
            edges=(),
        )
        call_graph = CallGraph(calls={"a.py::caller": ("b.py::callee",)})
        batch = (
            make_queue_entry("commitA", "T-0001", ("a.py::caller",)),
            make_queue_entry("commitB", "T-0002", ("b.py::callee",)),
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 3)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.ticket_id == "T-0001"
        assert attribution.reachability_path == ("a.py::caller",)

    def test_direct_touch_attributes_at_depth_zero(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_direct_touch_attributes_at_depth_zero  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (make_queue_entry("commitA", "T-0001", ("a.py::fn",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.reachability_path == ("a.py::fn",)

    def test_two_reaching_commits_is_unattributed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_two_reaching_commits_is_unattributed  # noqa: E501
        # Both commits touch symbols that reach the same finding -- never
        # pick the newest as a tiebreak; report UNATTRIBUTED with both
        # candidates named.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"shared.py::fn": make_symbol("shared.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (
            make_queue_entry("commitA", "T-0001", ("shared.py::fn",)),
            make_queue_entry("commitB", "T-0002", ("shared.py::fn",)),
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "shared.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "unattributed"
        assert set(attribution.candidate_commits) == {"commitA", "commitB"}
        assert attribution.commit_sha is None
        assert attribution.ticket_id is None

    def test_zero_reaching_commits_is_unattributed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_zero_reaching_commits_is_unattributed  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"orphan.py::fn": make_symbol("orphan.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (make_queue_entry("commitA", "T-0001", ("unrelated.py::other",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "orphan.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "unattributed"
        assert attribution.candidate_commits == ()

    def test_missing_line_falls_back_to_whole_file_candidates(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_missing_line_falls_back_to_whole_file_candidates  # noqa: E501
        # No line number: the finding's candidate set is every symbol in
        # the file. One of two symbols is reachable from commit A -- still
        # a clean single-candidate attribution.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn_one": make_symbol("a.py", "fn_one", 1, 5),
                "a.py::fn_two": make_symbol("a.py", "fn_two", 6, 10),
            },
            edges=(),
        )
        call_graph = CallGraph(calls={"caller.py::caller": ("a.py::fn_two",)})
        batch = (make_queue_entry("commitA", "T-0001", ("caller.py::caller",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py")],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.symbol is None  # no line -> no single-symbol resolution

    def test_graph_unavailable_is_an_error_for_the_whole_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_graph_unavailable_is_an_error_for_the_whole_batch  # noqa: E501
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod, "_load_snapshot_and_call_graph", lambda root: None
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 1)],
            (make_queue_entry("commitA", "T-0001", ("a.py::fn",)),),
        )
        assert result.is_err
        assert result.danger_err is AttributionError.GraphUnavailable


# frob:ticket T-2018
class TestBuildAdHocBatch:
    """T-2018: `build_ad_hoc_batch` builds a REAL candidate-commit batch
    from git history -- the fix for `frob verify explain`'s measured
    "queue is empty, nothing to attribute against" refusal, which fired
    whether or not the commit that actually caused a finding was
    reachable through real git history."""

    def test_covers_a_commit_the_persisted_queue_never_saw(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        # The exact shape T-2018 measured: NOTHING is in the persisted
        # verify queue (a fresh repo, or one whose watermark already
        # advanced past this commit) -- attribution must still work off
        # real git history alone.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.py").write_text("def fn():\n    pass\n")
        _commit(repo, "init")
        (repo / "a.py").write_text("def fn():\n    return 1\n")
        sha = _commit(repo, "T-0001 change fn")

        snapshot = GraphSnapshot(
            root=str(repo),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 2)},
            edges=(),
        )
        batch = build_ad_hoc_batch(repo, snapshot=snapshot, limit=10)
        matching = [e for e in batch if e.commit_sha == sha]
        assert len(matching) == 1
        assert matching[0].touched_symbols == ("a.py::fn",)
        assert matching[0].ticket_id == "T-0001"
        assert matching[0].profile == "ad-hoc"

    def test_end_to_end_attributes_through_attribute_batch(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        # T-2018's own worked example, end to end: an ad-hoc batch (no
        # persisted queue involved at all) feeds attribute_batch exactly
        # like a real persisted batch would, and a finding attributes to
        # the real causing commit.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.py").write_text("def fn():\n    pass\n")
        _commit(repo, "init")
        (repo / "a.py").write_text("def fn():\n    return 1\n")
        sha = _commit(repo, "T-0001 change fn")

        snapshot = GraphSnapshot(
            root=str(repo),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 2)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = build_ad_hoc_batch(repo, snapshot=snapshot, limit=10)
        result = attribute_batch(
            repo,
            [("RULE1", "a.py", 1)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == sha

    def test_commit_touching_no_resolvable_symbol_is_omitted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "other.py").write_text("x = 1\n")
        _commit(repo, "init")
        (repo / "other.py").write_text("x = 2\n")
        _commit(repo, "unrelated change")

        # Snapshot names only a.py::fn -- a symbol nowhere in this repo's
        # own history -- so no commit should ever yield a touched symbol.
        snapshot = GraphSnapshot(
            root=str(repo),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 2)},
            edges=(),
        )
        batch = build_ad_hoc_batch(repo, snapshot=snapshot, limit=10)
        assert batch == ()

    def test_since_bounds_the_candidate_range(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.py").write_text("def fn():\n    pass\n")
        base_sha = _commit(repo, "init")
        (repo / "a.py").write_text("def fn():\n    return 1\n")
        sha = _commit(repo, "T-0001 change fn")

        snapshot = GraphSnapshot(
            root=str(repo),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 2)},
            edges=(),
        )
        batch = build_ad_hoc_batch(repo, snapshot=snapshot, since=base_sha)
        shas = {e.commit_sha for e in batch}
        assert shas == {sha}

    def test_ambiguous_two_commits_reach_the_same_symbol_is_unattributed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        # T-2018 acceptance criterion 4: ad-hoc attribution must preserve
        # T-1690's own "never guess" rule -- two candidate commits that
        # BOTH touch the finding's symbol report UNATTRIBUTED with both
        # shas named, never a newest-commit tiebreak.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.py").write_text("def fn():\n    pass\n")
        _commit(repo, "init")
        (repo / "a.py").write_text("def fn():\n    return 1\n")
        sha1 = _commit(repo, "T-0001 first change")
        (repo / "a.py").write_text("def fn():\n    return 2\n")
        sha2 = _commit(repo, "T-0002 second change")

        snapshot = GraphSnapshot(
            root=str(repo),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 2)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = build_ad_hoc_batch(repo, snapshot=snapshot, limit=10)
        result = attribute_batch(
            repo,
            [("RULE1", "a.py", 1)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "unattributed"
        assert set(attribution.candidate_commits) == {sha1, sha2}

    def test_unreadable_git_history_degrades_to_empty_batch(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_attribution.py::build_ad_hoc_batch kind="unit"  # noqa: E501
        # Not a git repo at all -- `recent_commits` fails; must degrade to
        # an empty batch (logged), never raise.
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        batch = build_ad_hoc_batch(tmp_path, snapshot=snapshot, limit=10)
        assert batch == ()


# frob:ticket T-2018
class TestLoadAttributionContext:
    """T-2018: the public seam that lets a caller (e.g. `frob verify
    explain`) build the graph snapshot + call graph pair ONCE and thread
    it into both `build_ad_hoc_batch` and `attribute_batch`."""

    def test_returns_a_usable_snapshot_and_call_graph(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestLoadAttributionContext.test_returns_a_usable_snapshot_and_call_graph  # noqa: E501
        import frob.verify._attribution as attribution_mod
        from frob.verify._attribution import load_attribution_context

        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )
        result = load_attribution_context(tmp_path)
        assert result.is_ok
        got_snapshot, got_call_graph = result.danger_ok
        assert got_snapshot is snapshot
        assert got_call_graph is call_graph

    def test_build_failure_is_graph_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestLoadAttributionContext.test_build_failure_is_graph_unavailable  # noqa: E501
        import frob.verify._attribution as attribution_mod
        from frob.verify._attribution import load_attribution_context

        monkeypatch.setattr(
            attribution_mod, "_load_snapshot_and_call_graph", lambda root: None
        )
        result = load_attribution_context(tmp_path)
        assert result.is_err
        assert result.danger_err is AttributionError.GraphUnavailable
