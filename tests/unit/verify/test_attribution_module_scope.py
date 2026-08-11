"""T-2156: `frob verify explain`/`attribute_batch` used to fabricate an
attribution whenever a private helper name (e.g. `_run`) was independently
defined, with the identical name, in an UNRELATED file -- `_attribution.py`
built its reference graph via `build_reference_graph`, whose short-name
resolution deliberately wires an edge between EVERY same-named private
symbol in the whole tree (safe for its original consumer, T-0422's
dead-symbol gate; wrong for causal reachability). Two independent
`frob verify explain` reproductions during the T-2156 investigation both
attributed an unrelated finding to a land purely because that land's own
test file happened to define a helper of the same name as one already
present elsewhere in the repo.

This is the full end-to-end acceptance test: real files on disk, real
`load_attribution_context` (the exact seam `frob verify explain` itself
calls), real `attribute_batch` -- not a hand-constructed `CallGraph` that
would bypass the actual regression."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


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


class TestAttributionDoesNotCrossFileOnSameNamedHelper:
    # frob:tests tests/unit/verify/test_attribution_module_scope.py::TestAttributionDoesNotCrossFileOnSameNamedHelper.test_finding_in_file_a_does_not_attribute_through_unrelated_file_bs_same_named_helper kind="unit"  # noqa: E501
    def test_finding_in_file_a_does_not_attribute_through_unrelated_file_bs_same_named_helper(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """FAILS FIRST against current main: file A defines its own
        private `_run`; file B, in an unrelated later commit, defines a
        DIFFERENT `_run` with no import relationship to A at all. A
        finding anchored in A must attribute to A's own commit (or read
        unattributed), never to B's commit through a fabricated cross-
        file `_run` edge -- exactly the shape both `frob verify explain`
        reproductions in this ticket's investigation hit."""
        from frob.verify._attribution import attribute_batch, build_ad_hoc_batch
        from frob.verify._attribution import load_attribution_context

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.py").write_text(
            "def _run():\n    pass\n\n\ndef caller():\n    _run()\n"
        )
        sha_a = _commit(repo, "T-1111 add a.py with its own _run")

        # An unrelated LATER commit defines a completely different `_run`
        # in a different file -- no import, no real relationship to a.py.
        (repo / "b.py").write_text("def _run():\n    pass\n")
        _commit(repo, "T-2222 add unrelated b.py with its own _run")

        loaded = load_attribution_context(repo)
        assert loaded.is_ok, loaded
        snapshot, call_graph = loaded.danger_ok

        # Sanity: the bug this ticket fixes would show up here as an
        # edge from a.py::caller to b.py::_run.
        assert call_graph.calls.get("a.py::caller") == ("a.py::_run",), (
            "module-scoped graph must resolve caller's OWN-file _run only, "
            f"got {call_graph.calls.get('a.py::caller')!r}"
        )

        batch = build_ad_hoc_batch(repo, snapshot=snapshot, limit=10)
        result = attribute_batch(
            repo,
            [("RULE1", "a.py", 4)],  # the `caller` function's own line
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok, result
        (attribution,) = result.danger_ok
        # The real assertion: never falsely attributed to B's commit --
        # attributing correctly to A, or honestly reading unattributed,
        # are both acceptable; crossing to the unrelated commit is not.
        assert attribution.ticket_id != "T-2222", (
            "finding in a.py must never attribute to the unrelated b.py "
            f"commit; got attribution={attribution!r}"
        )
        if attribution.status == "attributed":
            assert attribution.commit_sha == sha_a
