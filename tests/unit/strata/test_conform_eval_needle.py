"""T-0882 regression: SYS100 extended's `eval` capability must not self-
match an identifier that merely CONTAINS the substring `eval(` (e.g. a
function named `_mutation_for_eval`) -- only a genuine bare `eval(`/`exec(`
builtin call site should fire (docs/strata/selfconform.md#the-three-rules).
"""


from __future__ import annotations

from pathlib import Path

from frob.strata import (
    SYS_UNDECLARED_INTERFACE,
    KernelModel,
    Node,
    check_self_conformance,
)
from frob.vet._capability import scan_file_capabilities


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestEvalNeedleSelfMatch:
    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_ident\
    # ifier_suffix_does_not_fire_eval
    def test_identifier_suffix_does_not_fire_eval(self, tmp_path: Path) -> None:
        """A function named `_mutation_for_eval` (no real eval/exec call
        anywhere in the file) must not be observed as the `eval` capability
        by `scan_file_capabilities` -- the T-0860 self-match false positive
        this ticket fixes."""
        _write(
            tmp_path,
            "src/frob/widget/_conform.py",
            "def _mutation_for_eval(tokens, start):\n    return set()\n",
        )
        capabilities = scan_file_capabilities(
            tmp_path / "src" / "frob" / "widget" / "_conform.py"
        )
        assert "eval" not in capabilities

    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_ident\
    # ifier_suffix_does_not_fire_sys100
    def test_identifier_suffix_does_not_fire_sys100(self, tmp_path: Path) -> None:
        """The same fixture through the full SYS100-extended self-conform
        path (`check_self_conformance`): no `eval` finding for a node whose
        only `eval(`-shaped text is a function name suffix."""
        _write(
            tmp_path,
            "src/frob/widget/_conform.py",
            "def _mutation_for_eval(tokens, start):\n    return set()\n",
        )
        model = KernelModel(
            nodes=(
                Node(id="widget", trust="trusted", attrs=("code=src/frob/widget/**",)),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok
        eval_hits = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_UNDECLARED_INTERFACE and v.capability == "eval"
        ]
        assert eval_hits == []

    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_genui\
    # ne_bare_eval_call_still_fires
    def test_genuine_bare_eval_call_still_fires(self, tmp_path: Path) -> None:
        """A real bare `eval(` builtin call must still be observed -- the
        fix must not weaken detection of an actual dynamic-code-execution
        capability, only the identifier-suffix self-match."""
        _write(
            tmp_path,
            "src/frob/widget/_conform.py",
            "def run(user_input):\n    return eval(user_input)\n",
        )
        capabilities = scan_file_capabilities(
            tmp_path / "src" / "frob" / "widget" / "_conform.py"
        )
        assert "eval" in capabilities

    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_genui\
    # ne_bare_exec_call_still_fires
    def test_genuine_bare_exec_call_still_fires(self, tmp_path: Path) -> None:
        """Sibling of the eval( case above for the bare `exec(` builtin."""
        _write(
            tmp_path,
            "src/frob/widget/_conform.py",
            "def run(user_input):\n    exec(user_input)\n",
        )
        capabilities = scan_file_capabilities(
            tmp_path / "src" / "frob" / "widget" / "_conform.py"
        )
        assert "eval" in capabilities

    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_ident\
    # ifier_suffix_for_exec_does_not_fire
    def test_identifier_suffix_for_exec_does_not_fire(self, tmp_path: Path) -> None:
        """Sibling of the `eval(` identifier-suffix case for `exec(` --
        e.g. a function named `_plan_for_exec` must not self-match."""
        _write(
            tmp_path,
            "src/frob/widget/_conform.py",
            "def _plan_for_exec(tokens, start):\n    return set()\n",
        )
        capabilities = scan_file_capabilities(
            tmp_path / "src" / "frob" / "widget" / "_conform.py"
        )
        assert "eval" not in capabilities

    # frob:tests \
    # tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch.test_real_\
    # repo_design_selfconform_has_no_eval_gap
    def test_real_repo_design_selfconform_has_no_eval_gap(self) -> None:
        """T-0882 acceptance [2]: with the T-0860 `waive "SYS100:eval"`
        clause deleted from `design/frob.strata`'s `deploy` node, the real
        repo's self-conformance pass (the same `load_design_ids` +
        `merge_models` + `check_self_conformance` composition
        `run_native_sys_audit`/`frob sys audit` use) must report zero
        violations -- mirrors `run_native_sys_audit`'s own composition
        rather than importing it directly, since that helper's `proved`
        verdict also folds in unrelated exhaustiveness gaps (pre-existing
        compliance debt, out of this ticket's scope) that would make a
        direct `proved` assertion here brittle to unrelated drift."""
        from frob.strata._design_load import load_design_ids
        from frob.strata._selfconform import check_self_conformance
        from frob.strata._sysdoc import merge_models

        repo_root = Path(__file__).resolve().parents[3]
        ids = load_design_ids(repo_root)
        assert not ids.errors
        model = merge_models(ids.models)
        result = check_self_conformance(model, repo_root)
        assert result.is_ok
        # T-0667: SYS103 (SYS-COV) joins SYS100-102 at zero here too --
        # `_coverage_totality_scan_prefix` restricts it to `_PACKAGE_ROOT`
        # on frob's own tree (docs/modules/strata.md#sys-cov-coverage-
        # totality-sys103-t-0667), so it does not see tests/**/scripts/**/
        # frob-core/src/**/strata-core/src/**, which design/frob.strata
        # does not model.
        assert result.danger_ok.violations == ()
