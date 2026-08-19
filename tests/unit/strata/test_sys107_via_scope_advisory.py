"""Unit tests for SYS107 (T-1451): the via-less-may-on-a-large-node
advisory (docs/strata/surface.md#may-scope, `_selfconform.py`).

Split into its own file rather than `test_selfconform.py` because T-1451
was worked in the same worktree as (and after) T-1450, which already
leases `test_selfconform.py` -- see this ticket's scope-change reasons.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import (
    SYS_VIA_LESS_LARGE_NODE,
    KernelModel,
    MayGrant,
    Node,
    check_self_conformance,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestViaLessLargeNodeAdvisory:
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_via_less_grant_on_large_node_fires(self, tmp_path: Path):
        """A node bound to more files than the threshold, with a via-less
        `may`, is an advisory SYS107 finding."""
        for i in range(25):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_VIA_LESS_LARGE_NODE
        ]
        assert any(v.node == "widget" for v in hit)

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_via_less_grant_on_small_node_is_silent(self, tmp_path: Path):
        """A small node (file count at or under the threshold) never fires
        SYS107, no matter how it declares `may`."""
        for i in range(3):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_VIA_LESS_LARGE_NODE for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_via_scoped_grant_on_large_node_is_silent(self, tmp_path: Path):
        """A large node whose ONLY `may` grant is fully `via`-scoped never
        fires SYS107 -- it has already done the narrowing the advisory
        exists to nudge toward."""
        for i in range(25):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                    may_grants=(MayGrant(atom="net", via=("src/frob/widget/_f0.py",)),),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_VIA_LESS_LARGE_NODE for v in result.danger_ok.violations
        )

    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_node_with_no_may_never_fires(self, tmp_path: Path):
        """A large node that declares NO `may` at all has nothing to
        narrow -- SYS107 only concerns whole-node GRANTS, not size alone."""
        for i in range(25):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        assert not any(
            v.rule == SYS_VIA_LESS_LARGE_NODE for v in result.danger_ok.violations
        )

    # frob:ticket T-2224
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    # frob:waive DUP001 reason="deliberately near-identical to test_via_less_grant_on_large_node_fires -- same large-node/via-less-grant fixture shape, the only difference is asserting the new capability=<atom> field this ticket adds; a shared fixture builder would obscure exactly what changed between the two tests"  # noqa: E501
    def test_via_less_grant_carries_the_offending_atom(self, tmp_path: Path):
        """T-2224: each SYS107 finding now carries `capability=<atom>` --
        the field a per-capability severity decision (fail-closed kinds
        always ERROR) needs to key off of."""
        for i in range(25):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("exec",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_VIA_LESS_LARGE_NODE
        ]
        assert any(v.node == "widget" and v.capability == "exec" for v in hit)

    # frob:ticket T-2224
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_via_less_grants_on_two_atoms_fire_two_separate_findings(
        self, tmp_path: Path
    ):
        """T-2224: a node with BOTH a via-less exec grant and a via-less
        net grant produces one finding PER atom, not one finding covering
        both -- required so the fail-closed atom can be escalated to
        ERROR independently of the non-fail-closed one staying WARN."""
        for i in range(25):
            _write(tmp_path, f"src/frob/widget/_f{i}.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("exec", "net"),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        hit = [
            v for v in result.danger_ok.violations if v.rule == SYS_VIA_LESS_LARGE_NODE
        ]
        capabilities = {v.capability for v in hit if v.node == "widget"}
        assert capabilities == {"exec", "net"}


class TestTestsuiteExecViaListRestored:
    """T-2666: `testsuite`'s `exec` grant collided with T-2224's SYS107
    fail-closed policy after T-2503 made it ambient (via-less) -- exec is in
    `SYS107_FAIL_CLOSED_ATOMS`, testsuite binds well over the 20-file
    threshold, so a via-less `exec` grant there is unconditionally an ERROR.
    Scans the REAL `design/frob.strata` against the REAL repo tree (same
    shape as `test_selfconform.py::TestRealGateGreen`, but scoped to just
    this one node/atom pair so it stays green independent of the separate,
    already-filed fs.read/fs.write SYS107 severity-filtering gap on the
    same node -- see this ticket's Done report)."""

    # frob:ticket T-2666
    # frob:tests src/frob/strata/_selfconform.py::check_self_conformance kind="unit"
    def test_testsuite_exec_has_no_via_less_sys107_finding(self):
        """`design/frob.strata`'s real `testsuite` node no longer declares
        a via-less `exec` grant -- the SYS107 finding for (testsuite, exec)
        is gone after T-2666 restored the enumerated `via` list."""
        import pytest

        pytest.importorskip("strata_core")
        from frob.strata._design_load import load_design_ids
        from frob.strata._sysdoc import merge_models

        root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(root, "design")
        assert not ids.errors, f"design load failed: {ids.errors}"
        model = merge_models(ids.models)

        result = check_self_conformance(model, root)
        assert result.is_ok, result.err
        hit = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_VIA_LESS_LARGE_NODE
            and v.node == "testsuite"
            and v.capability == "exec"
        ]
        assert hit == [], hit
