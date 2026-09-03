import json
import subprocess
from pathlib import Path

import pytest

from frob.gates import (
    GateConfig,
    Severity,
    SystemSpec,
    TestPolicy,
    Violation,
    drift_gate,
    run_gates,
)
from frob.gates import (
    test_gate as run_test_gate,
)
from frob.graph import GraphSnapshot
from frob.graph._models import LockFile
from frob.testing import CollectedTests
from tests.conftest import (
    _DESIGN_STRATA,
    _first_rule,
    _rules,
    _snapshot,
    _write,
)


# frob:ticket T-0549
# frob:ticket T-1763
# frob:ticket T-2438
# frob:ticket T-2999
class TestTestGate:
    def test_test001_public_symbol_no_unit_edge(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::test_gate
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST001" for v in violations)

    # frob:ticket T-0589
    # frob:tests tests/gates_suite/test_test_gate.py::TestTestGate.test_test001_zero_branch_coverage_flags_when_opted_in kind="unit"  # noqa: E501
    def test_test001_zero_branch_coverage_flags_when_opted_in(
        self, tmp_path: Path
    ) -> None:
        """T-0589: with `require_branch_coverage_for_test001=True`, a
        symbol that satisfies TEST001 by name/edge match ALONE, but whose
        `coverage.xml` shows the symbol's file was measured and the symbol
        itself never ran (0% branch coverage, the T-0557 dead-code signal),
        still fires TEST001 -- the def-myfunc-pass-shaped B1 gap TEST015
        only ever WARNed about, now blocking when this policy flag is on."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 0.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1, require_branch_coverage_for_test001=True)
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        v = next(
            (v for v in violations if v.rule == "TEST001"),
            None,
        )
        assert v is not None, violations
        assert "0% measured branch coverage" in v.message

    # frob:ticket T-0589
    # frob:tests tests/gates_suite/test_test_gate.py::TestTestGate.test_test001_zero_branch_coverage_silent_when_flag_off kind="unit"  # noqa: E501
    def test_test001_zero_branch_coverage_silent_when_flag_off(
        self, tmp_path: Path
    ) -> None:
        """T-0589: the SAME zero-branch-coverage symbol as the sibling test
        above must NOT fire TEST001 when
        `require_branch_coverage_for_test001` is left at its default
        (`False`) -- the new check is opt-in, not a silent global
        behavior change, since promoting it repo-wide requires the
        compat survey this ticket's own body calls for."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 0.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1)
        assert cfg.require_branch_coverage_for_test001 is False
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        assert not any(v.rule == "TEST001" for v in violations)

    # frob:ticket T-0589
    # frob:tests tests/gates_suite/test_test_gate.py::TestTestGate.test_test001_nonzero_branch_coverage_stays_silent_when_opted_in kind="unit"  # noqa: E501
    def test_test001_nonzero_branch_coverage_stays_silent_when_opted_in(
        self, tmp_path: Path
    ) -> None:
        """T-0589: a symbol WITH nonzero measured branch coverage must not
        fire the new check even with the flag on -- the promoted check
        targets zero coverage specifically (a test that never actually
        called the symbol), not any coverage below the TEST005 floor
        (that remains TEST005's own, separate, WARN-severity job)."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        coverage = Some(
            CoverageData(
                source_sha="x",
                symbol_branch={"src/frob/pkg/a.py::helper": 42.0},
                module_line={"src/frob/pkg/a.py": 90.0},
            )
        )
        cfg = TestPolicy(min_unit_cases=1, require_branch_coverage_for_test001=True)
        violations = run_test_gate(snap, (), coverage, tests, cfg)
        assert not any(v.rule == "TEST001" for v in violations)

    def test_test002_below_min_unit_cases(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/frob/pkg/a.py", source)
        test_source = (
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_helper"
        tests = CollectedTests(node_ids=frozenset({node}))
        cfg = TestPolicy(min_unit_cases=3)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" in rule_ids
        assert "TEST001" not in rule_ids

    def test_test002_satisfied_by_rust_directive_bound_cross_file(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-0090: a `frob:tests` directive living in a
        different rust file than its target symbol must still count as unit
        evidence. T-0092 gave rust a real execution-based collector
        (`collect_rust_tests`), so this now asserts through the FIRST branch
        of `_valid_edges` (real collected node id), not the structural
        fallback the T-0090 comment used to describe -- `.rs` was removed
        from `_NATIVE_TEST_EXTENSIONS` accordingly."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n",
        )
        _write(
            tmp_path,
            "strata-core/src/parse.rs",
            '// frob:tests strata-core/src/lib.rs::parse_source kind="unit"\n'
            "#[test]\n"
            "fn test_parse_basic() {\n"
            "    assert_eq!(1, 1);\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"strata-core/src/parse.rs::test_parse_basic"})
        )
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" not in rule_ids
        assert "TEST001" not in rule_ids

    def test_test002_rust_directive_from_non_test_symbol_does_not_satisfy(
        self, tmp_path: Path
    ) -> None:
        """Regression for the T-0090 review finding: a `frob:tests` directive
        whose `src` is a real symbol but NOT test code (no `tests` module
        segment, no `test_`/`_test` leaf name) must not count as evidence --
        extension alone (`.rs`) is not enough, or any non-test rust/ts/c/cpp
        symbol could rubber-stamp coverage for anything it names."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n\n"
            '// frob:tests strata-core/src/lib.rs::parse_source kind="unit"\n'
            "pub fn unrelated_helper(x: &str) -> i32 {\n    0\n}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" in rule_ids

    def test_test001_002_explicit_unit_edge_honored_regardless_of_test_name(
        self, tmp_path: Path
    ) -> None:
        """Regression for T-0336 (root-caused while adding
        `tests/test_graph.py::TestGeneratedSource` for T-0234's
        `is_generated_source`): `_test_edges` used to index unit TESTS
        edges by `edge.target` only, but the directive convention used
        throughout this codebase for "written directly above the source
        function, naming its covering test" (`docs/modules/testing.md`)
        binds `src` to the source symbol and `target` to the test id --
        `record.symref` (the source) can then only ever match `edge.src`,
        never `edge.target`, so a target-only index can structurally never
        find it. `zebra_helper` is deliberately tested by
        `test_alpha_omega_case`, a name that shares no token with
        `zebra_helper` -- `_inferred_unit_cases`' naming-convention fallback
        cannot match it, so TEST001/002 can only stay clean here via the
        explicit `frob:tests ... kind="unit"` edge being both found
        (`_unit_test_edges` indexing `edge.src`) and honored as real
        execution evidence (`_valid_edges` checking `edge.target` too)."""
        from typani.option import Nothing

        source = (
            '# frob:tests tests/test_a.py::test_alpha_omega_case kind="unit"\n'
            "def zebra_helper(x):\n    return x\n"
        )
        _write(tmp_path, "src/frob/pkg/a.py", source)
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_alpha_omega_case():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_alpha_omega_case"
        tests = CollectedTests(node_ids=frozenset({node}))
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" not in rule_ids

    def test_test003_interface_without_integration(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST003" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestTestGate.test_test003_exempts_strata_des\
    # ign_files kind="unit"
    def test_test003_exempts_strata_design_files(self, tmp_path: Path) -> None:
        """T-0225: `design/*.strata` must not be counted as a TEST003
        "interface package" -- it owns no pytest surface, so
        "0 integration tests" is a category error, not a real gap. The
        design-file obligation is TEST009's e2e floor instead."""
        from typani.option import Nothing

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST003" and v.file == "design" for v in violations)

    def test_test003_satisfied_by_parametrized_test_node_id(
        self, tmp_path: Path
    ) -> None:
        """Root-cause regression (feldspar FROBLEMS.md 2026-07-18,
        `test_library_thermo.py`): a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test looked like a broken
        comment-to-decorator attachment, but `frob.lang._extract` already
        resolves that binding correctly -- the real mismatch is that
        `pytest --collect-only` never emits the bare `path::func` node id
        for a parametrized test, only per-case `path::func[case-id]`
        ids, so an exact `in tests.node_ids` membership check could never
        validate a directive whose src is the bare (unparametrized)
        symref. `_node_id_collected` must accept any collected id that is
        the base id itself OR a `[...]`-suffixed parametrized expansion
        of it."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/thermo.py", "def helper(x):\n    return x\n")
        test_source = (
            '# frob:tests src/frob/pkg/thermo.py kind="integration"\n'
            "@pytest.mark.parametrize('x', [1, 2])\n"
            "def test_density(x):\n"
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_thermo.py", test_source)
        snap = _snapshot(tmp_path)
        # Exactly what pytest --collect-only emits for a parametrized test:
        # bracketed per-case ids, never the bare function name.
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_thermo.py::test_density[1]",
                    "tests/test_thermo.py::test_density[2]",
                }
            )
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST003" not in _rules(violations)

    def test_test003_satisfied_by_parametrized_case_with_dot_in_case_id(
        self, tmp_path: Path
    ) -> None:
        """T-0324 regression, TEST003 side of the same bug: a `frob:tests`
        directive bound to a parametrized test whose ONLY collected cases
        carry a dot inside their `[...]` case text (e.g. `[3.11]`, a float
        or version-string parametrize value) must still satisfy TEST003 --
        `_symref_to_nodeid` must not corrupt those in-bracket dots into
        `::` while converting the directive's own dotted qualname."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/thermo.py", "def helper(x):\n    return x\n")
        test_source = (
            '# frob:tests src/frob/pkg/thermo.py kind="integration"\n'
            "@pytest.mark.parametrize('x', [3.11, 4.22])\n"
            "def test_density(x):\n"
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_thermo.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_thermo.py::test_density[3.11]",
                    "tests/test_thermo.py::test_density[4.22]",
                }
            )
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST003" not in _rules(violations)

    def test_test003_satisfied_by_proptest_macro_block(self, tmp_path: Path) -> None:
        """T-0318 litmus (feldspar): a `frob:tests` comment sitting directly
        above a `proptest! { ... }` block must satisfy TEST003. proptest's
        expansion synthesizes real `#[test]` fns at compile time (one per
        `fn` inside the macro's braces), which `cargo test --list` collects
        under THEIR OWN names -- never under a `proptest`-named node id --
        and tree-sitter parses the macro's braces as one opaque `token_tree`
        with no `function_item` descendants at all, so the directive has no
        literal AST node to bind to without `_walk_rust.py` emitting a
        stand-in symbol for the macro block itself (`_macro_symbol`).
        `_macro_symbol_file`/`_macro_file_collected` then resolve that
        stand-in's TESTS edge at file granularity: satisfied because the
        file has >=1 real collected case, not because any node id matches
        the stand-in's own synthesized qualname (which never collects)."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "strata-core/src/lib.rs",
            "pub fn parse_source(x: &str) -> i32 {\n    0\n}\n",
        )
        _write(
            tmp_path,
            "strata-core/tests/prop_parse.rs",
            '// frob:tests strata-core/src/lib.rs kind="integration"\n'
            "proptest! {\n"
            "    #[test]\n"
            "    fn prop_parse_roundtrip(x in 0..100u32) {\n"
            "        assert!(x < 100);\n"
            "    }\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "strata-core/tests/prop_parse.rs::prop_parse_roundtrip",
                }
            )
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST003" not in _rules(violations)

    def test_test002_parametrized_test_counts_each_case(self, tmp_path: Path) -> None:
        """T-0307 litmus: a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test with 3 cases must count
        as 3 collected unit cases, not 1. Before the fix, `_valid_edges`
        returned one Edge per directive and `_test001_002_one` used
        `len(valid)` as the case count -- so a parametrized test with any
        number of collected `[case-id]` variants always reported exactly 1
        case, silently failing to clear `min_unit_cases > 1` no matter how
        many cases actually ran (lograder/aprog-public/feldspar all hit
        this and worked around it with dishonest non-parametrized twin
        tests). `min_unit_cases=3` here would fail pre-fix (effective=1)
        and passes post-fix (effective=3, one per collected case id)."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        test_source = (
            "@pytest.mark.parametrize('x', [1, 2, 3])\n"
            "def test_helper(x):\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_a.py::test_helper[1]",
                    "tests/test_a.py::test_helper[2]",
                    "tests/test_a.py::test_helper[3]",
                }
            )
        )
        cfg = TestPolicy(min_unit_cases=3)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" not in rule_ids
        assert "TEST001" not in rule_ids

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_test002_noop_parametrize_does_not_inflate_case_count(
        self, tmp_path: Path
    ) -> None:
        """T-0549 counterexample: a `frob:tests` directive bound to a
        `@pytest.mark.parametrize`-decorated test whose body asserts
        NOTHING must not clear `min_unit_cases` just because it collected
        many `[case-id]` variants. Before the fix, `_case_count` credited
        one case per collected variant unconditionally -- a 10-variant
        no-op test cleared `min_unit_cases=3` the same as a genuinely
        assertion-bearing one (B7 in docs/audits/gates-accounting.md).
        Post-fix, a no-op parametrized test is capped to 1 case (like the
        structural fallback), so TEST002 still fires."""
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        test_source = (
            "@pytest.mark.parametrize('x', [1, 2, 3])\n"
            "def test_helper(x):\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    helper(x)\n"  # calls helper, asserts nothing
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset(
                {
                    "tests/test_a.py::test_helper[1]",
                    "tests/test_a.py::test_helper[2]",
                    "tests/test_a.py::test_helper[3]",
                }
            )
        )
        cfg = TestPolicy(min_unit_cases=3)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST002" in rule_ids
        assert "TEST001" not in rule_ids  # an edge does exist, just thin

    def test_case_count_direct(self) -> None:
        """Direct unit coverage of `_case_count` (T-0307): a valid edge's
        collected cases are counted individually (parametrize expansions),
        and a validated edge with no execution-based match (native
        structural fallback) still counts as exactly one case."""
        from frob.gates import _case_count
        from frob.graph import Edge, EdgeKind

        ids = frozenset(
            {
                "tests/test_x.py::test_density[1]",
                "tests/test_x.py::test_density[2]",
                "tests/test_x.py::test_density[3]",
            }
        )
        tests = CollectedTests(node_ids=ids)
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_density",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_x.py:1",
        )
        assert _case_count([edge], tests) == 3

        # An edge with no matching collected id at all (structural
        # fallback territory) still contributes exactly one case.
        empty_tests = CollectedTests(node_ids=frozenset())
        assert _case_count([edge], empty_tests) == 1

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_case_count_root_none_skips_assertion_check(self) -> None:
        """T-0549: `root=None` (the default) is the pre-T-0549 behavior
        exactly -- `_case_count` never touches the filesystem and cannot
        discount a no-op test, matching every caller that has no root to
        check against (and this file's own node ids, which name no file
        that exists on disk)."""
        from frob.gates import _case_count
        from frob.graph import Edge, EdgeKind

        ids = frozenset(
            {
                "tests/test_x.py::test_density[1]",
                "tests/test_x.py::test_density[2]",
                "tests/test_x.py::test_density[3]",
            }
        )
        tests = CollectedTests(node_ids=ids)
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_x.py::test_density",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_x.py:1",
        )
        assert _case_count([edge], tests) == 3
        assert _case_count([edge], tests, root=None) == 3

    # frob:ticket T-0549
    # frob:tests src/frob/gates/__init__.py::_case_count kind="unit"
    def test_case_count_root_aware_caps_noop_parametrize(self, tmp_path: Path) -> None:
        """T-0549: with a real `root`, a parametrized test function with no
        assertion-shaped construct in its body is capped to 1 case no
        matter how many `[case-id]` variants collected; a real assertion
        in the same shape of function still counts every variant."""
        from frob.gates import _case_count
        from frob.graph import Edge, EdgeKind

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_noop(x):\n    helper(x)\n",
        )
        ids = frozenset(
            {
                "tests/test_a.py::test_noop[1]",
                "tests/test_a.py::test_noop[2]",
                "tests/test_a.py::test_noop[3]",
            }
        )
        tests = CollectedTests(node_ids=ids)
        edge = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_a.py::test_noop",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_a.py:1",
        )
        assert _case_count([edge], tests, root=tmp_path) == 1

        _write(
            tmp_path,
            "tests/test_b.py",
            "def test_real(x):\n    assert helper(x) == x\n",
        )
        ids_real = frozenset(
            {
                "tests/test_b.py::test_real[1]",
                "tests/test_b.py::test_real[2]",
                "tests/test_b.py::test_real[3]",
            }
        )
        tests_real = CollectedTests(node_ids=ids_real)
        edge_real = Edge(
            kind=EdgeKind.TESTS,
            src="tests/test_b.py::test_real",
            target="src/frob/pkg/a.py::helper",
            origin="tests/test_b.py:1",
        )
        assert _case_count([edge_real], tests_real, root=tmp_path) == 3

    def test_node_id_collected_direct(self) -> None:
        """Direct unit coverage of `_node_id_collected` itself, independent
        of the gate machinery around it."""
        from frob.gates import _node_id_collected

        ids = frozenset(
            {"tests/test_x.py::test_density[1]", "tests/test_x.py::test_density[2]"}
        )
        assert _node_id_collected("tests/test_x.py::test_density", ids)
        assert _node_id_collected("tests/test_x.py::test_density[1]", ids)
        assert not _node_id_collected("tests/test_x.py::test_other", ids)
        # a bare-prefix collision must not false-positive
        assert not _node_id_collected("tests/test_x.py::test_dens", ids)

    def test_test003_waiver_in_a_file_under_the_package_matches(
        self, tmp_path: Path
    ) -> None:
        """T-0276: TEST003's `violation.file` is a PACKAGE interface id
        (e.g. `crates/feldspar-core/src`), never a real single file --
        found while investigating why a `frob:waive TEST003 reason="..."`
        written in a rust integration test file reported `0 waived` in
        feldspar's adoption sweep. Root cause was NOT check_type gating
        `.rs` directives (disproven directly: build_graph/_load_tests are
        check_type-agnostic) -- it was that `_match_waiver`'s file-scoped
        comparison required the waiver's own file to be LITERALLY EQUAL
        to the package id string, which no real file path (always has an
        extension) can ever be. A waiver written in any file living
        under that package directory must now match."""
        from typani.option import Nothing

        from frob.gates import _apply_waivers  # noqa: PLC0415

        _write(
            tmp_path,
            "src/frob/pkg/a.py",
            '# frob:waive TEST003 reason="covered elsewhere"\n'
            "def helper(x):\n"
            "    return x\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST003" for v in violations)

        kept, waived = _apply_waivers(violations, snap)
        assert not any(v.rule == "TEST003" for v in kept)
        assert any(v.rule == "TEST003" for v in waived)

    def test_match_waiver_prefix_reach_gated_to_package_scoped_rules(self) -> None:
        """T-0470 counterexample: BEFORE this fix, `_match_waiver`'s
        directory-prefix branch ran for every symref-less violation
        regardless of rule -- any rule whose `violation.file` happened to
        be directory-shaped (no extension) inherited unbounded prefix
        reach it was never reviewed for. A non-package-scoped rule (i.e.
        not in `_PACKAGE_SCOPED_RULES`) with a directory-shaped `file`
        must now match ONLY a waiver whose own site is that exact
        file/directory string -- never a waiver nested somewhere under
        it via the prefix fallback."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        directory_shaped_violation = Violation(
            rule="SYS002",  # not in _PACKAGE_SCOPED_RULES
            severity=Severity.WARN,
            file="design/boundary/foo",
            line=0,
            message="x",
        )
        nested_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="design/boundary/foo/bar.py",
            target="SYS002",
            origin="design/boundary/foo/bar.py:1",
            attrs={"reason": "x"},
        )
        assert (
            _match_waiver(directory_shaped_violation, {"SYS002": [nested_waiver]})
            is None
        )

        # The package-scoped rules keep their prefix reach unchanged.
        package_violation = Violation(
            rule="TEST003",
            severity=Severity.ERROR,
            file="src/frob/pkg",
            line=0,
            message="x",
        )
        package_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/pkg/a.py",
            target="TEST003",
            origin="src/frob/pkg/a.py:1",
            attrs={"reason": "x"},
        )
        assert (
            _match_waiver(package_violation, {"TEST003": [package_waiver]})
            == package_waiver
        )

    # frob:ticket T-2338
    def test_match_waiver_picks_line_nearest_of_two_same_file_same_rule(
        self,
    ) -> None:
        """T-2338: a file with 2+ `frob:waive PERF008` comments at
        DIFFERENT lines (the real T-2321 incident shape) must have each
        violation matched to the waiver comment nearest ITS OWN line, not
        whichever waiver happens to come first in build order -- this
        MUST FAIL on main (the old code always returned `candidates[0]`)."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        far_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/x.py",
            target="PERF008",
            origin="src/frob/x.py:10",
            attrs={"reason": "far waiver, near line 10"},
        )
        near_waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/x.py",
            target="PERF008",
            origin="src/frob/x.py:500",
            attrs={"reason": "near waiver, near line 500"},
        )
        violation_near_500 = Violation(
            rule="PERF008",
            severity=Severity.WARN,
            file="src/frob/x.py",
            line=501,
            message="x",
        )
        matched = _match_waiver(
            violation_near_500, {"PERF008": [far_waiver, near_waiver]}
        )
        assert matched is near_waiver, (
            f"expected the line-501 violation matched to the line-500 waiver, "
            f"got reason={matched.attrs.get('reason') if matched else None!r}"
        )

        violation_near_10 = Violation(
            rule="PERF008",
            severity=Severity.WARN,
            file="src/frob/x.py",
            line=11,
            message="x",
        )
        matched2 = _match_waiver(
            violation_near_10, {"PERF008": [far_waiver, near_waiver]}
        )
        assert matched2 is far_waiver, (
            f"expected the line-11 violation matched to the line-10 waiver, "
            f"got reason={matched2.attrs.get('reason') if matched2 else None!r}"
        )

    # frob:ticket T-2338
    def test_match_waiver_still_suppresses_regardless_of_which_one_wins(
        self,
    ) -> None:
        """Must-still-pass control: suppression itself is unaffected by
        this fix -- ANY matching waiver (near or far) still suppresses
        the finding; only the DISPLAYED reason's attribution changes."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        waiver_a = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/x.py",
            target="PERF008",
            origin="src/frob/x.py:10",
            attrs={"reason": "A"},
        )
        waiver_b = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/x.py",
            target="PERF008",
            origin="src/frob/x.py:500",
            attrs={"reason": "B"},
        )
        violation = Violation(
            rule="PERF008",
            severity=Severity.WARN,
            file="src/frob/x.py",
            line=250,
            message="x",
        )
        matched = _match_waiver(violation, {"PERF008": [waiver_a, waiver_b]})
        assert matched is not None

    # frob:ticket T-2438
    def test_match_waiver_symref_formatting_difference_still_waives(self) -> None:
        """T-2438 must-now-waive control: reproduces the confirmed live
        mismatch -- `frob.arch`'s hand-rolled C++ symref producer
        (`frob.lang._common._cpp_class_methods`, shared by
        `frob.arch._cpp`/`_cpp_mayraise`) spells a method's symref with
        the native `Class::method` scope operator
        (`violation.symref == "x.cpp::Foo::bar"`), while the DSL/graph
        symbol table that binds a symbol-bound `frob:waive` comment
        (`frob.lang._walk_c`) always dot-joins qualname segments
        (`waiver.src == "x.cpp::Foo.bar"`). BEFORE this fix, `_match_
        waiver`'s symbol-exact branch compared these two spellings with
        plain `==`, found no match, and returned None unconditionally --
        the waiver never suppressed the finding even though both sides
        genuinely name the same method. Verified directly against real
        producers: `frob.arch._cpp._check_long_functions` on a synthetic
        long C++ method yields `symref='<path>::Foo::bar'`, and `frob.
        lang.parse_file` + `frob.graph.dsl.parse_directives` on the same
        source with a `frob:waive ARCH001` comment above `bar` binds
        `Edge.src == '<path>::Foo.bar'` -- the exact two strings this
        test hardcodes."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        violation = Violation(
            rule="ARCH001",
            severity=Severity.WARN,
            file="x.cpp",
            line=4,
            message="x",
            symref="x.cpp::Foo::bar",
            metric=20,
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="x.cpp::Foo.bar",
            target="ARCH001",
            origin="x.cpp:3",
            attrs={"reason": "x"},
        )
        assert _match_waiver(violation, {"ARCH001": [waiver]}) is waiver

    # frob:ticket T-2438
    def test_match_waiver_different_symbol_same_file_still_not_waived(
        self,
    ) -> None:
        """T-2438 must-still-keep control: a waiver bound to a DIFFERENT
        symbol in the same file must still NOT suppress an unrelated
        finding -- proves the T-2438 normalization fix did not trade
        symbol-exact precision for a blanket file-scoped waiver. `Foo.bar`
        and `Foo.qux` normalize to two different strings regardless of
        separator spelling, so this must stay None both before and after
        the fix."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        violation = Violation(
            rule="ARCH001",
            severity=Severity.WARN,
            file="x.cpp",
            line=40,
            message="x",
            symref="x.cpp::Foo::qux",
            metric=20,
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="x.cpp::Foo.bar",
            target="ARCH001",
            origin="x.cpp:3",
            attrs={"reason": "x"},
        )
        assert _match_waiver(violation, {"ARCH001": [waiver]}) is None

    # frob:ticket T-2438
    def test_match_waiver_logs_diagnostic_on_genuine_symref_mismatch(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-2438 acceptance [1]: a symref-carrying violation with no
        symbol-exact (post-normalization) waiver match, but a same-file
        same-rule waiver present, must emit a diagnostic naming BOTH
        strings rather than silently returning None -- fail-loudly
        (T-2391) applied to the waiver-matching layer."""
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        import logging

        from frob.gates import _match_waiver
        from frob.graph import Edge, EdgeKind

        violation = Violation(
            rule="ARCH001",
            severity=Severity.WARN,
            file="x.cpp",
            line=40,
            message="x",
            symref="x.cpp::Foo::qux",
            metric=20,
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="x.cpp::Foo.bar",
            target="ARCH001",
            origin="x.cpp:3",
            attrs={"reason": "x"},
        )
        with caplog.at_level(logging.WARNING):
            result = _match_waiver(violation, {"ARCH001": [waiver]})
        assert result is None
        assert any(
            "x.cpp::Foo::qux" in rec.message and "x.cpp::Foo.bar" in rec.message
            for rec in caplog.records
        ), f"expected a diagnostic naming both symref strings, got {caplog.records!r}"

    def test_waive003_flags_waiver_reaching_multiple_packages(self) -> None:
        """T-0470: one `frob:waive TEST003` written in a file nested under
        `src/frob/pkg/sub` also reaches the ANCESTOR package `src/frob/pkg`
        via the same directory-prefix fallback -- both are real TEST003
        violations the same directive silently suppresses. WAIVE003 must
        flag that as over-broad."""
        # frob:tests src/frob/gates/_waive.py::_waive003_violations
        from frob.gates import _waive003_violations
        from frob.graph import Edge, EdgeKind

        violations = (
            Violation(
                rule="TEST003",
                severity=Severity.ERROR,
                file="src/frob/pkg",
                line=0,
                message="x",
            ),
            Violation(
                rule="TEST003",
                severity=Severity.ERROR,
                file="src/frob/pkg/sub",
                line=0,
                message="x",
            ),
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/frob/pkg/sub/deep.py",
            target="TEST003",
            origin="src/frob/pkg/sub/deep.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive003_violations(violations, snap)
        assert len(found) == 1
        assert found[0].rule == "WAIVE003"
        assert "src/frob/pkg" in found[0].message
        assert "src/frob/pkg/sub" in found[0].message

        # A waiver that reaches only ONE package is not over-broad.
        single = _waive003_violations(violations[:1], snap)
        assert single == ()

    def test_waive004_fires_on_valid_rule_zero_findings(self) -> None:
        """T-0753: a waiver targeting a real, matchable rule id but whose
        site produces ZERO findings under that rule this run is the stale
        class WAIVE002 cannot see (the rule id is known; only the site is
        stale) -- WAIVE004 must flag it."""
        # frob:tests src/frob/gates/_waive.py::_waive004_violations
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        # No COV001 violation at all this run -- the waiver matches nothing.
        found = _waive004_violations((), snap, frozenset())
        assert len(found) == 1
        assert found[0].rule == "WAIVE004"
        assert found[0].severity == Severity.WARN
        assert "COV001" in found[0].message

    def test_waive004_stays_silent_on_a_genuinely_needed_waiver(self) -> None:
        """T-0753: a waiver whose site DOES still produce a matching finding
        must never fire WAIVE004 -- only a truly stale/unnecessary waiver is
        in scope."""
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        live_violation = Violation(
            rule="COV001",
            severity=Severity.ERROR,
            file="src/a.py",
            line=2,
            symref="src/a.py::helper",
            message="still missing a doc anchor",
        )
        found = _waive004_violations((live_violation,), snap, frozenset())
        assert found == ()

    def test_waive004_skips_a_waive002_unrecognized_rule(self) -> None:
        """T-0753: an edge WAIVE002 already flags as targeting an
        unrecognized rule id has no findings to compare against by
        construction -- WAIVE004 must not pile a second, redundant finding
        onto the same directive."""
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="NOTAREALRULE",
            origin="src/a.py:2",
            attrs={"reason": "typo"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive004_violations((), snap, frozenset())
        assert found == ()

    # frob:ticket T-1064
    # frob:ticket T-1763
    def test_waive004_exempts_a_diff_scoped_rule(self) -> None:
        """T-1064/T-1763: `AFFECT001` only ever emits a finding for a
        symbol in the diff's OWN touched-ref set -- a full, unscoped run's
        diff is essentially never the exact diff that originally
        triggered the waived finding, so WAIVE004 must not misreport it as
        stale just because this run's diff never reaches it. (T-1064's
        original example here was INV006, a SELF-SUPPRESSING rule that
        never let a covered finding reach `all_violations` at all --
        deleted by T-1763 for producing zero live findings across its
        whole lifetime; `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` no
        longer needs a self-suppressing example to stay covered, so this
        test now exercises the still-live diff-scoped class instead.)"""
        # frob:tests src/frob/gates/_waive.py::_waive004_violations
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py",
            target="AFFECT001",
            origin="src/a.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        # No AFFECT001 violation in `all_violations` -- by construction,
        # since this run's diff never touches the symbol the waiver was
        # written against -- yet WAIVE004 must stay silent rather than
        # call the waiver stale.
        found = _waive004_violations((), snap, frozenset())
        assert found == ()

    # frob:ticket T-1577
    @pytest.mark.parametrize(
        ("rule", "src"),
        [
            ("WIRE001", "src/a.py::helper"),
            ("SCOPE001", "src/a.py"),
        ],
        ids=["wire001", "scope001"],
    )
    def test_waive004_exempts_diff_scoped_rules(self, rule: str, src: str) -> None:
        """T-1577: WIRE001 only ever constructs a finding from a diff's
        added hunks (`frob.gates._wire`), and SCOPE001 is already
        documented as diff-scoped like COV002/TODO001 via `SCOPED_RUN_
        FLAKY_RULE_IDS` -- a full unscoped run's diff is essentially never
        the exact diff that originally introduced/waived the site, so a
        zero-match waiver on either rule must not be reported as stale."""
        # frob:tests src/frob/gates/_waive.py::_waive004_violations
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src=src,
            target=rule,
            origin="src/a.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive004_violations((), snap, frozenset())
        assert found == ()

    # frob:ticket T-1064
    def test_waive004_still_fires_for_a_non_exempt_rule_with_the_same_shape(
        self,
    ) -> None:
        """T-1064: the structurally-unverifiable exemption is a narrow,
        named allowlist, not a blanket "file-scoped waiver" carve-out --
        a zero-match waiver on a rule NOT in that set must still fire
        WAIVE004 exactly as before."""
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py",
            target="DOC001",
            origin="src/a.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive004_violations((), snap, frozenset())
        assert len(found) == 1
        assert found[0].rule == "WAIVE004"
        assert "DOC001" in found[0].message

    # frob:ticket T-1133
    def test_waive004_suppressed_entirely_on_a_scoped_run(self) -> None:
        """T-1133: `full_unscoped_run=False` (the `--only`/`--ticket`
        scoped-run signal) must short-circuit to `()` even for a waiver
        that would otherwise clearly read as stale (zero matching findings,
        a real known rule) -- on a scoped run, "the gate did not run" and
        "the waiver is stale" are indistinguishable, so the check must not
        fire at all rather than emit an advisory a caller has to filter."""
        # frob:tests tests/gates_suite/test_test_gate.py::TestTestGate.test_waive004_suppressed_entirely_on_a_scoped_run  # noqa: E501
        from frob.gates import _waive004_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive004_violations((), snap, frozenset(), full_unscoped_run=False)
        assert found == ()

    # frob:ticket T-1803
    def test_waive008_fires_on_a_now_rescued_autouse_fixture(
        self, tmp_path: Path
    ) -> None:
        """T-1803's confirmed incident: a WIRE001 waiver on an autouse
        pytest fixture -- WIRE001's own `_is_autouse_pytest_fixture` rescue
        (T-1510) exempts it unconditionally, so the waiver has suppressed
        nothing since that rescue landed, regardless of diff. WAIVE004
        cannot see this (WIRE001 is diff-scoped); WAIVE008 tests the
        rescue predicate directly against the symbol's own record."""
        # frob:tests tests/gates_suite/test_test_gate.py::TestTestGate.test_waive008_fires_on_a_now_rescued_autouse_fixture  # noqa: E501
        from frob.gates import _waive008_violations
        from frob.graph import (
            Digests,
            Edge,
            EdgeKind,
            SymbolId,
            SymbolRecord,
        )
        from frob.lang import SymbolKind

        src = tmp_path / "conftest.py"
        src.write_text(
            "@pytest.fixture(autouse=True)\ndef _isolate() -> None:\n    pass\n",
            encoding="utf-8",
        )
        record = SymbolRecord(
            id=SymbolId(path="conftest.py", qualname="_isolate"),
            kind=SymbolKind.FUNCTION,
            public=False,
            digests=Digests(sig="s", body="b", doc="d"),
            span=(1, 3),
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="conftest.py::_isolate",
            target="WIRE001",
            origin="conftest.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(
            root=str(tmp_path),
            symbols={"conftest.py::_isolate": record},
            edges=(waiver,),
        )
        found = _waive008_violations(snap)
        assert len(found) == 1
        assert found[0].rule == "WAIVE008"
        assert found[0].severity == Severity.WARN
        assert "conftest.py::_isolate" in found[0].message

    # frob:ticket T-1803
    def test_waive008_stays_silent_on_a_non_rescued_symbol(
        self, tmp_path: Path
    ) -> None:
        """A WIRE001 waiver on an ordinary (non-fixture, non-validator)
        symbol must not fire -- WAIVE008 only flags the specific
        structurally-guaranteed-dead shape."""
        # frob:tests \
        # tests/gates_suite/test_test_gate.py::TestTestGate.test_waive008_stays_silent_\
        # on_a_non_rescued_symbol
        from frob.gates import _waive008_violations
        from frob.graph import (
            Digests,
            Edge,
            EdgeKind,
            SymbolId,
            SymbolRecord,
        )
        from frob.lang import SymbolKind

        src = tmp_path / "a.py"
        src.write_text("def helper() -> None:\n    pass\n", encoding="utf-8")
        record = SymbolRecord(
            id=SymbolId(path="a.py", qualname="helper"),
            kind=SymbolKind.FUNCTION,
            public=False,
            digests=Digests(sig="s", body="b", doc="d"),
            span=(1, 2),
        )
        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="a.py::helper",
            target="WIRE001",
            origin="a.py:1",
            attrs={"reason": "x"},
        )
        snap = GraphSnapshot(
            root=str(tmp_path), symbols={"a.py::helper": record}, edges=(waiver,)
        )
        assert _waive008_violations(snap) == ()

    def test_waive005_expired_until_is_error(self) -> None:
        """T-0753: `frob:waive`'s optional `until="YYYY-MM-DD"` boundary
        having passed forces a hard ERROR demanding re-review, mirroring
        DEBT003/DEPR004's expiry escalation."""
        # frob:tests src/frob/gates/_waive.py::_waive005_violations
        from frob.gates import _waive005_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x", "until": "2020-01-01"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        found = _waive005_violations(snap, current_date="2026-07-22")
        assert len(found) == 1
        assert found[0].rule == "WAIVE005"
        assert found[0].severity == Severity.ERROR
        assert "2020-01-01" in found[0].message

    def test_waive005_future_until_passes(self) -> None:
        """A `frob:waive ... until=` boundary still in the future must not
        fire WAIVE005."""
        from frob.gates import _waive005_violations
        from frob.graph import Edge, EdgeKind

        waiver = Edge(
            kind=EdgeKind.WAIVE,
            src="src/a.py::helper",
            target="COV001",
            origin="src/a.py:2",
            attrs={"reason": "x", "until": "2099-01-01"},
        )
        snap = GraphSnapshot(root=".", symbols={}, edges=(waiver,))
        assert _waive005_violations(snap, current_date="2026-07-22") == ()

    def test_waive_until_bad_date_is_malformed(self, tmp_path: Path) -> None:
        """T-0753: a `frob:waive ... until="..."` that is not a
        `YYYY-MM-DD` date is rejected at parse time, mirroring
        `frob:deprecated`'s `sunset=` validation (T-0576)."""
        source = (
            "def helper(x):\n"
            '    # frob:waive COV001 reason="x" until="not-a-date"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        assert any(
            "frob:waive" in md.reason and "until" in md.reason for md in snap.malformed
        )

    def test_test004_system_below_min_e2e(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        system = SystemSpec(
            id="cli-check", entrypoint="frob check", min_e2e=2, paths=()
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (system,), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST004" for v in violations)

    def test_test004_passes_with_enough_e2e(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        test_source = (
            'def test_a():\n    # frob:tests cli-check kind="e2e"\n    assert True\n'
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        node = "tests/test_a.py::test_a"
        system = SystemSpec(
            id="cli-check", entrypoint="frob check", min_e2e=1, paths=()
        )
        tests = CollectedTests(node_ids=frozenset({node}))
        violations = run_test_gate(snap, (system,), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST004" for v in violations)

    def test_test005_unit_branch_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        coverage = CoverageData(
            source_sha="x", symbol_branch={record.symref: 40.0}, module_line={}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert any(v.rule == "TEST005" and v.file == record.id.path for v in violations)

    def test_test005_skips_test_file_symbols(self, tmp_path: Path) -> None:
        # T-0301: TEST005's per-symbol branch floor must skip test-file
        # symbols exactly like TEST001/TEST002 (_is_test_file) -- a test
        # fixture measured below the floor must not fire, matching the
        # existing skip other TEST rules already apply.
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "tests/test_a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["tests/test_a.py::helper"]
        coverage = CoverageData(
            source_sha="x", symbol_branch={record.symref: 40.0}, module_line={}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert not any(
            v.rule == "TEST005" and v.file == record.id.path for v in violations
        )

    # frob:ticket T-0557
    def test_test005_unmeasured_symbol_in_measured_file_flags_as_zero(
        self, tmp_path: Path
    ) -> None:
        """T-0557 (B4): a symbol with NO entry in `symbol_branch` -- never
        executed at all -- must still be flagged at 0% branch coverage when
        its FILE genuinely was measured (has a `module_line` entry).
        Previously `_test005_symbols` skipped any symbol absent from
        `symbol_branch`, silently clearing dead code that a test suite never
        calls into even once."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def dead(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::dead"]
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        v = next(
            (
                v
                for v in violations
                if v.rule == "TEST005" and v.symref == record.symref
            ),
            None,
        )
        assert v is not None
        assert "0.0%" in v.message

    # frob:ticket T-0557
    def test_test005_symbol_in_unmeasured_file_still_skipped(
        self, tmp_path: Path
    ) -> None:
        """T-0557 (B4) counterpart: a symbol whose FILE never appears in
        coverage.xml at all (no `module_line` entry -- excluded from
        measurement, e.g. never imported by the suite) must still be
        skipped, not flagged at 0% -- that is a measurement gap, not proof
        the symbol itself fails the floor."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def unmeasured(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::unmeasured"]
        coverage = CoverageData(source_sha="x", symbol_branch={}, module_line={})
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        assert not any(
            v.rule == "TEST005" and v.symref == record.symref for v in violations
        )

    def test_test005_module_line_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x", symbol_branch={}, module_line={"src/frob/pkg/a.py": 10.0}
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(module_line_cov=85)
        )
        assert any(
            v.rule == "TEST005" and v.file == "src/frob/pkg/a.py" for v in violations
        )

    def test_test005_system_line_floor(self, tmp_path: Path) -> None:
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x", symbol_branch={}, module_line={"src/frob/pkg/a.py": 10.0}
        )
        system = SystemSpec(
            id="sys", entrypoint="x", min_e2e=0, paths=("src/frob/pkg/*",)
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (system,), Some(coverage), tests, TestPolicy(system_line_cov=80)
        )
        assert any(v.rule == "TEST005" and "sys" in v.file for v in violations)

    # frob:ticket T-1205
    def test_test005_symbol_finding_discloses_stale_coverage(
        self, tmp_path: Path
    ) -> None:
        """T-1205 acceptance[1]: a TEST005 finding computed from a stale
        coverage.xml (`stale_by_mtime=True`) must carry the
        `[STALE COVERAGE]` disclosure prefix, not read as an unqualified
        current fact (the T-1293 incident this ticket exists to prevent:
        an agent trusted a 23-hour-stale stamp and closed a ticket having
        fixed 1 of 64 real findings)."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={record.symref: 40.0},
            module_line={},
            stale_by_mtime=True,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        v = next(
            v for v in violations if v.rule == "TEST005" and v.symref == record.symref
        )
        assert v.message.startswith("[STALE COVERAGE] TEST005:")

    # frob:ticket T-1205
    def test_test005_symbol_finding_no_disclosure_when_fresh(
        self, tmp_path: Path
    ) -> None:
        """Counterpart: a fresh (non-stale) TEST005 finding must NOT carry
        the disclosure prefix -- the marker is conditional, not universal."""
        from typani.option import Some

        from frob.gates import CoverageData

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        record = snap.symbols["src/frob/pkg/a.py::helper"]
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={record.symref: 40.0},
            module_line={},
            stale_by_mtime=False,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(unit_branch_cov=90)
        )
        v = next(
            v for v in violations if v.rule == "TEST005" and v.symref == record.symref
        )
        assert not v.message.startswith("[STALE COVERAGE]")
        assert v.message.startswith("TEST005:")

    # frob:ticket T-1205
    def test_test005_module_finding_discloses_stale_coverage(
        self, tmp_path: Path
    ) -> None:
        """Same T-1205 disclosure, for the per-module TEST005 finding path."""
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=True,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(module_line_cov=85)
        )
        v = next(
            v
            for v in violations
            if v.rule == "TEST005" and v.file == "src/frob/pkg/a.py"
        )
        assert v.message.startswith("[STALE COVERAGE] TEST005:")

    # frob:ticket T-1205
    def test_test005_system_finding_discloses_stale_coverage(
        self, tmp_path: Path
    ) -> None:
        """Same T-1205 disclosure, for the per-system TEST005 finding path."""
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=True,
        )
        system = SystemSpec(
            id="sys", entrypoint="x", min_e2e=0, paths=("src/frob/pkg/*",)
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (system,), Some(coverage), tests, TestPolicy(system_line_cov=80)
        )
        v = next(v for v in violations if v.rule == "TEST005" and "sys" in v.file)
        assert v.message.startswith("[STALE COVERAGE] TEST005:")

    def test_test008_fires_on_unjoined_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test008_unjoined_root
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"nope.py": 0.0},
            root_join_ok=False,
            attempted_roots=("wrong/root", ""),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test008 = [v for v in violations if v.rule == "TEST008"]
        assert len(test008) == 1
        assert test008[0].severity == Severity.ERROR

    def test_test008_silent_when_root_joined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test008_unjoined_root
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 100.0},
            root_join_ok=True,
            attempted_roots=("src/frob",),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Some(coverage), tests, TestPolicy(module_line_cov=0)
        )
        assert not any(v.rule == "TEST008" for v in violations)

    def test_test008_cannot_be_waived(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_waive.py::_match_waiver
        # TEST008 is unwaivable BY CONSTRUCTION (_UNWAIVABLE_RULES), not
        # just by nobody thinking to try -- a same-repo `frob:waive
        # TEST008` directive must never suppress it, since this gate's
        # entire purpose is staying loud in every sibling repo it runs in.
        source = (
            '# frob:waive TEST008 reason="pretend this is fine"\n'
            "def helper(x):\n"
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from typani.option import Some  # noqa: PLC0415

        from frob.gates import CoverageData, _apply_waivers  # noqa: PLC0415

        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            root_join_ok=False,
            attempted_roots=("wrong/root", ""),
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert any(v.rule == "TEST008" for v in violations)

        kept, waived = _apply_waivers(violations, snap)
        assert any(v.rule == "TEST008" for v in kept)
        assert not any(v.rule == "TEST008" for v in waived)

    def test_test011_fires_on_stale_mtime(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test011_freshness
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=True,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test011 = [v for v in violations if v.rule == "TEST011"]
        assert len(test011) == 1
        assert test011[0].severity == Severity.WARN
        assert "predates" in test011[0].message

    def test_test017_fires_on_low_join_fraction(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test017_deflation
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=False,
            module_join_fraction=0.1,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test011 = [v for v in violations if v.rule == "TEST011"]
        assert len(test011) == 0
        test017 = [v for v in violations if v.rule == "TEST017"]
        assert len(test017) == 1
        assert test017[0].severity == Severity.ERROR
        assert "deflated" in test017[0].message

    def test_test011_silent_when_fresh_and_fully_joined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test011_freshness
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert not any(v.rule == "TEST011" for v in violations)
        assert not any(v.rule == "TEST017" for v in violations)

    # frob:ticket T-0545
    def test_test012_missing_lock_warns(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        test012 = [v for v in violations if v.rule == "TEST012"]
        assert len(test012) == 1
        assert test012[0].severity == Severity.WARN
        assert "no committed coverage lock" in test012[0].message

    # frob:ticket T-0545
    def test_test012_drifted_module_warns(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData, write_coverage_lock

        snap = _snapshot(tmp_path)
        locked = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        write_coverage_lock(tmp_path, locked)
        live = CoverageData(
            source_sha="y",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 10.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(live), tests, TestPolicy())
        test012 = [v for v in violations if v.rule == "TEST012"]
        assert len(test012) == 1
        assert "src/frob/pkg/a.py" in test012[0].message

    # frob:ticket T-0545
    def test_test012_matching_lock_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_test012_lock
        from typani.option import Some

        from frob.gates import CoverageData, write_coverage_lock

        snap = _snapshot(tmp_path)
        coverage = CoverageData(
            source_sha="x",
            symbol_branch={},
            module_line={"src/frob/pkg/a.py": 90.0},
            stale_by_mtime=False,
            module_join_fraction=1.0,
        )
        write_coverage_lock(tmp_path, coverage)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Some(coverage), tests, TestPolicy())
        assert not any(v.rule == "TEST012" for v in violations)

    # frob:ticket T-2999
    def test_test012_abandoned_producer_fires_error(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """MUST-FIRE: a coverage lock stamped once, then real git commits
        touch its own code_glob with no re-stamp and no pin -- the exact
        shape T-2999 measured on this repo's own frob-coverage.lock.json
        (816 real commits since last stamp, at time of writing)."""
        # frob:tests src/frob/gates/__init__.py::_test012_producer_abandoned

        from frob.gates import _test012_producer_abandoned

        monkeypatch.setattr(
            "frob.gates._lock_producer.ABANDONED_CODE_COMMIT_THRESHOLD", 2
        )

        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
            )

        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        (tmp_path / "frob-coverage.lock.json").write_text('{"v": 1}')
        (tmp_path / "src" / "frob" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "pkg" / "a.py").write_text("x = 1\n")
        git("add", "-A")
        git("commit", "-q", "-m", "stamp")
        for i in range(3):
            (tmp_path / "src" / "frob" / "pkg" / "a.py").write_text(f"x = {i}\n")
            git("add", "-A")
            git("commit", "-q", "-m", f"code change {i}")
        violations = _test012_producer_abandoned(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "ABANDONED" in violations[0].message

    # frob:ticket T-2999
    def test_test012_pinned_producer_stays_quiet(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """MUST-STAY-QUIET: identical code-churn shape to the must-fire
        case above, but the lock carries a `pin` -- a deliberate freeze
        must never fire the ABANDONED-producer error."""
        # frob:tests src/frob/gates/__init__.py::_test012_producer_abandoned

        from frob.gates import _test012_producer_abandoned

        monkeypatch.setattr(
            "frob.gates._lock_producer.ABANDONED_CODE_COMMIT_THRESHOLD", 2
        )

        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
            )

        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        (tmp_path / "frob-coverage.lock.json").write_text(
            '{"v": 1, "pin": {"reason": "frozen on purpose", "ticket": "T-1"}}'
        )
        (tmp_path / "src" / "frob" / "pkg").mkdir(parents=True)
        (tmp_path / "src" / "frob" / "pkg" / "a.py").write_text("x = 1\n")
        git("add", "-A")
        git("commit", "-q", "-m", "stamp")
        for i in range(3):
            (tmp_path / "src" / "frob" / "pkg" / "a.py").write_text(f"x = {i}\n")
            git("add", "-A")
            git("commit", "-q", "-m", f"code change {i}")
        violations = _test012_producer_abandoned(tmp_path)
        assert violations == ()

    def test_ci_workflow_self_gate_does_not_swallow_errors(self) -> None:
        """T-1265 (CHK-THEME-GITIGNORED-TRUST successor): the CI self-gate
        step used to run `uv run frob check || echo "::warning..."` --
        swallowing every finding, ERROR-tier included, so a real gate
        error never failed the build. Locks that the swallow is gone.
        """
        # frob:tests .github/workflows/ci.yml
        text = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        assert 'uv run frob check || echo "::warning' not in text
        assert "run: uv run frob check\n" in text

    def test_ci_workflow_hard_fails_on_test012_drift(self) -> None:
        """T-1265: `frob-coverage.lock.json` (T-0545, the one coverage-
        derived channel that is committed and travels with the diff, not
        gitignored like `.frob/coverage-stamp`/`.frob/baseline`) must be
        checked in CI as a hard gate -- TEST012 is WARN-severity by
        design, so it never failed the self-gate step's own exit code
        even before the swallow above was removed.
        """
        # frob:tests .github/workflows/ci.yml
        text = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        assert "TEST012" in text
        assert "frob-coverage.lock.json" in text

    def test_test006_missing_stamp(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        assert any(v.rule == "TEST006" for v in violations)

    def test_test006_remedy_points_at_frob_coverage_not_make(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_test006_missing
        # T-3721: the scaffold's Makefile ships no `coverage` target (its
        # own comment says `frob coverage` is the interface), so TEST006's
        # remedy text must never tell a user to run `make coverage` --
        # it must name the frob-native verb the scaffold actually ships.
        snap = _snapshot(tmp_path)
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        (violation,) = (v for v in violations if v.rule == "TEST006")
        assert "make coverage" not in violation.message
        assert "frob coverage" in violation.message

    def test_test006_stale_stamp(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        stamp = {
            "source_sha": "x",
            "file_hashes": {"src/frob/pkg/a.py": "not-the-real-hash"},
        }
        (tmp_path / ".frob").mkdir(exist_ok=True)
        (tmp_path / ".frob" / "coverage-stamp").write_text(json.dumps(stamp))
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        assert any(v.rule == "TEST006" for v in violations)

    def test_changelog_mentions_rejects_substring_in_prose(
        self, tmp_path: Path
    ) -> None:
        """T-0403 B14: `version` appearing anywhere in the file (unrelated
        prose, a longer version number's prefix) must NOT satisfy the
        changelog check -- only a real heading entry for that exact
        version does.
        """
        from frob.gates import _changelog_mentions  # noqa: PLC0415

        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [1.2.34] - 2026-01-01\nbumped past 1.2.3 to fix a bug\n",
            encoding="utf-8",
        )
        # "1.2.3" is a substring of both the heading "1.2.34" and the prose
        # line, but there is no real heading entry for "1.2.3" itself.
        assert _changelog_mentions(tmp_path, "1.2.3") is False

    def test_changelog_mentions_accepts_real_heading_entry(
        self, tmp_path: Path
    ) -> None:
        """A genuine `## [version]` heading entry does satisfy the check."""
        from frob.gates import _changelog_mentions  # noqa: PLC0415

        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [1.2.3] - 2026-01-01\nfixed things\n",
            encoding="utf-8",
        )
        assert _changelog_mentions(tmp_path, "1.2.3") is True

    def test_test006_stale_on_new_file_not_in_stamp(self, tmp_path: Path) -> None:
        """T-0403 B15: a file added after the last stamp has no entry in
        `file_hashes` at all -- it must be reported stale, not silently
        skipped (a prior version only compared hashes for paths already
        present in the stamp, so brand-new files' coverage went unmeasured
        while TEST006 stayed green).
        """
        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg/b.py", "def other(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        # Stamp only knows about a.py -- b.py was added afterward.
        a_hash = snap.file_hashes["src/frob/pkg/a.py"]
        stamp = {
            "source_sha": "x",
            "file_hashes": {"src/frob/pkg/a.py": a_hash},
        }
        (tmp_path / ".frob").mkdir(exist_ok=True)
        (tmp_path / ".frob" / "coverage-stamp").write_text(json.dumps(stamp))
        from frob.gates import _test006  # noqa: PLC0415

        violations = _test006(snap)
        assert any(v.rule == "TEST006" for v in violations)

    def test_edge_with_uncollected_node_id_does_not_satisfy(
        self, tmp_path: Path
    ) -> None:
        from typani.option import Nothing

        source = "def helper(x):\n    return x\n"
        _write(tmp_path, "src/frob/pkg/a.py", source)
        test_source = (
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n"
        )
        _write(tmp_path, "tests/test_a.py", test_source)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset()
        )  # the test was deleted/not collected
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(v.rule == "TEST002" for v in violations)


class TestConventionUnitBinding:
    def test_test001_satisfied_by_convention_name(self, tmp_path):
        """T-0018: a public function is unit-covered by a conventionally
        named test (test_<name>) even without an explicit frob:tests edge."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def normalize(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m.py::test_normalize_handles_empty"})
        )
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert not any(v.rule == "TEST001" for v in violations)

    def test_test001_still_fires_without_matching_test(self, tmp_path):
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def normalize(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m.py::test_other_thing"})
        )
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert any(v.rule == "TEST001" for v in violations)

    def test_short_symbol_names_do_not_match_everything(self, tmp_path):
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/m.py", "def of(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_m.py::test_unrelated"}))
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert any(v.rule == "TEST001" and "::of" in v.message for v in violations)

    # frob:ticket T-1861
    def test_test001_exempts_claude_hooks_path(self, tmp_path):
        """T-1857 (T-1838's COV001/TEST001 fallout): `.claude/hooks/**`
        scripts run only under the Claude Code dispatch harness -- demanding
        pytest unit coverage of them is not real assurance and becomes a
        waived-forever tax, so TEST001 exempts this path class the same
        way `_test001_002` already exempts `*.strata` files by extension
        (see the sibling `test_test001_exempts_strata_flow_declarations`
        test immediately below)."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, ".claude/hooks/example-hook.py", "def main():\n    return 0\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert not any(
            v.rule in ("TEST001", "TEST002")
            and v.file == ".claude/hooks/example-hook.py"
            for v in violations
        )

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestConventionUnitBinding.test_test001_exemp\
    # ts_strata_flow_declarations kind="unit"
    def test_test001_exempts_strata_flow_declarations(self, tmp_path):
        """T-0168: a `flow` (or other) `.strata` declaration has no defined
        "unit test" meaning -- design conformance is proven by the sys
        gates (`frob sys audit`/self-conformance), not pytest bindings.
        TEST001 must not demand a `frob:tests` edge for it, with no
        matching test and no edge at all."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(
            snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1)
        )
        assert not any(
            v.rule in ("TEST001", "TEST002") and v.file == "design/m.strata"
            for v in violations
        )

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestConventionUnitBinding.test_test009_fires\
    # _on_unbound_design_file kind="unit"
    def test_test009_fires_on_unbound_design_file(self, tmp_path):
        """T-0225: a `.strata` design file with no `frob:tests kind="e2e"`
        edge owes TEST009 -- the e2e-binding obligation that replaces the
        TEST003 package check design files were wrongly held to."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert any(
            v.rule == "TEST009" and v.file == "design/m.strata" for v in violations
        )

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestConventionUnitBinding.test_test009_exemp\
    # ts_test_fixture_strata kind="unit"
    def test_test009_exempts_test_fixture_strata(self, tmp_path):
        """T-0225 follow-up: a `.strata` file under a tests dir (a litmus /
        parser fixture) is test DATA, not a deployable design model, so it
        does NOT owe a TEST009 e2e binding -- `_design_files` excludes it via
        `_is_test_file`, killing the ~70-warning fixture flood."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "tests/unit/strata/litmus/fixture.strata", _DESIGN_STRATA)
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(v.rule == "TEST009" for v in violations)

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestConventionUnitBinding.test_test009_satis\
    # fied_by_e2e_edge kind="unit"
    def test_test009_satisfied_by_e2e_edge(self, tmp_path):
        """T-0225: a `frob:tests ... kind="e2e"` edge bound to the design
        file's module (or one of its declared ids) and backed by a
        collected test node id satisfies TEST009."""
        from typani.option import Nothing

        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "design/m.strata", _DESIGN_STRATA)
        _write(
            tmp_path,
            "tests/test_m_e2e.py",
            '# frob:tests design/m.strata::m.f_login kind="e2e"\n'
            "def test_login_flow_e2e():\n"
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_m_e2e.py::test_login_flow_e2e"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert not any(
            v.rule == "TEST009" and v.file == "design/m.strata" for v in violations
        )


class TestTest010KindValidation:
    """T-0237: a `frob:tests` directive's `kind=` attribute is not
    gate-verified -- `frob.graph.dsl` already refuses to turn an invalid
    `kind=` into an edge at all (a `MalformedDirective`, never silently
    defaulted), but nothing surfaced that as a reported violation until
    TEST010."""

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestTest010KindValidation.test_invalid_kind_\
    # reported kind="unit"
    def test_invalid_kind_reported(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="drift"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        v = _first_rule(violations, "TEST010")
        assert v is not None
        assert v.severity == Severity.ERROR
        assert v.file == "tests/test_a.py"
        assert "drift" in v.message

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestTest010KindValidation.test_valid_kind_no\
    # t_reported kind="unit"
    def test_valid_kind_not_reported(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_a.py::test_helper"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST010" not in _rules(violations)

    # frob:tests \
    # tests/gates_suite/test_test_gate.py::TestTest010KindValidation.test_dangling_test\
    # s_endpoint_still_caught_by_drift002 kind="unit"
    def test_dangling_tests_endpoint_still_caught_by_drift002(
        self, tmp_path: Path
    ) -> None:
        """T-0237's other reported gap -- a `frob:tests` edge whose CODE-side
        endpoint no longer resolves -- turns out to already be caught by the
        existing, edge-kind-agnostic DRIFT002 mechanism (`_vanished_endpoint`
        checks every edge's `src`/`target`, not just `frob:describes`); this
        pins that down as a regression guard rather than adding a duplicate
        TESTS-specific resolver."""

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::gone kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        violations = drift_gate(snap, LockFile())
        v = _first_rule(violations, "DRIFT002")
        assert v is not None
        assert "src/frob/pkg/a.py::gone" in v.message


# frob:ticket T-0552
# frob:ticket T-0730
class TestTest013NativeUnverified:
    """T-0552 (docs/audits/gates-accounting.md B3/E3): a `frob:tests` edge
    whose ONLY credit toward TEST001-004 is the c/cpp structural (name/
    path) fallback (T-0730 retired TS from this fallback -- see
    `TestNativeTestCollectors`) -- frob runs no collector that actually
    executes it -- must be surfaced as a loud, filterable TEST013 finding,
    not stay silently indistinguishable from a real, executed test."""

    # frob:ticket T-0552
    def test_fires_on_structural_only_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest013NativeUnverified.test_fires_on_structural_only_edge  # noqa: E501
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/pkg/thing.c",
            "void some_public_func(void) {}\n\n"
            '// frob:tests src/pkg/thing.c::some_public_func kind="unit"\n'
            "void test_something(void) {}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())  # frob never ran this
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test013 = [v for v in violations if v.rule == "TEST013"]
        assert len(test013) == 1
        assert test013[0].severity == Severity.WARN
        assert "test_something" in test013[0].message
        assert "unverified" in test013[0].message

    # frob:ticket T-0552
    def test_silent_on_executed_edge(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_test_gate.py::TestTest013NativeUnverified.test_silent_\
        # on_executed_edge
        # A python edge with real collected execution evidence (pytest node
        # id) must never be mistaken for the native-unverified case -- the
        # extension check in `_edge_is_native_unverified` is what keeps
        # TEST013 scoped to languages frob genuinely cannot execute.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_helper():\n"
            '    # frob:tests src/frob/pkg/a.py::helper kind="unit"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_a.py::test_helper"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST013" not in _rules(violations)


# frob:ticket T-0730
class TestNativeTestCollectors:
    """T-0730: `_load_tests` now consumes `collect_ts_tests` (vitest) and
    `collect_cpp_tests` (ctest) node ids alongside python/rust (T-0587
    built the collectors; this wires them into `frob.gates`), and TS is
    retired from `_NATIVE_TEST_EXTENSIONS`'s structural fallback now that a
    real vitest node id can resolve a TS `frob:tests` edge exactly the way
    a pytest/cargo node id already does."""

    # frob:ticket T-0730
    def test_ts_no_longer_in_native_extensions(self) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_ts_no_longer_in_native_extensions  # noqa: E501
        import frob.gates as gates_mod

        assert ".ts" not in gates_mod._NATIVE_TEST_EXTENSIONS
        assert ".tsx" not in gates_mod._NATIVE_TEST_EXTENSIONS
        # C/C++ stays -- T-0886 made collect_cpp_tests source-accurate for
        # the common single-source-per-target case (see its docstring), but
        # only when a build was configured with
        # CMAKE_EXPORT_COMPILE_COMMANDS=ON and the target is unambiguous;
        # most C/C++ edges still have no such build directory at
        # gate-check time and still need this structural fallback.
        assert ".cpp" in gates_mod._NATIVE_TEST_EXTENSIONS

    # frob:ticket T-0730
    def test_load_tests_merges_all_four_collectors(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_load_tests_merges_all_four_collectors  # noqa: E501
        from typani import Err, Ok

        import frob.gates as gates_mod
        from frob.testing import TestingError

        monkeypatch.setattr(
            gates_mod,
            "collect_python_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"tests/test_x.py::test_a"}))
            ),
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_rust_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"crate/src/lib.rs::tests::foo"}))
            ),
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_ts_tests",
            lambda root: Ok(
                CollectedTests(node_ids=frozenset({"src/thing.test.ts::does a thing"}))
            ),
        )
        monkeypatch.setattr(
            gates_mod,
            "collect_cpp_tests",
            lambda root: Ok(CollectedTests(node_ids=frozenset({"build::MyTest"}))),
        )
        merged, python_collection_failed = gates_mod._load_tests(tmp_path)
        assert merged.node_ids == frozenset(
            {
                "tests/test_x.py::test_a",
                "crate/src/lib.rs::tests::foo",
                "src/thing.test.ts::does a thing",
                "build::MyTest",
            }
        )
        assert python_collection_failed is None

        # A broken vitest collector degrades to "no ts ids", not a crash
        # and not a wipe of the other three languages' already-collected
        # ids.
        monkeypatch.setattr(
            gates_mod,
            "collect_ts_tests",
            lambda root: Err(TestingError.CollectFailed),
        )
        merged2, python_collection_failed2 = gates_mod._load_tests(tmp_path)
        assert merged2.node_ids == frozenset(
            {
                "tests/test_x.py::test_a",
                "crate/src/lib.rs::tests::foo",
                "build::MyTest",
            }
        )
        assert python_collection_failed2 is None

    # frob:ticket T-0730
    def test_ts_directive_resolves_via_real_vitest_node_id(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_ts_directive_resolves_via_real_vitest_node_id  # noqa: E501
        """A TS `frob:tests` directive naming a real collected vitest node id
        resolves as genuine execution evidence (`_valid_edges`'s FIRST
        branch, `_symref_to_nodeid`/`_node_id_collected`) -- not the
        structural fallback, which TS no longer participates in at all."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/thing.ts",
            "export function doThing(): number {\n  return 0;\n}\n",
        )
        _write(
            tmp_path,
            "src/thing.test.ts",
            '// frob:tests src/thing.ts::doThing kind="unit"\n'
            "export function testDoesAThing(): void {\n"
            "  doThing();\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"src/thing.test.ts::testDoesAThing"})
        )
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" not in rule_ids
        assert "TEST013" not in rule_ids

    # frob:ticket T-0730
    def test_ts_structural_only_edge_no_longer_credited(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_ts_structural_only_edge_no_longer_credited  # noqa: E501
        """Acceptance (T-0730): a TS `frob:tests` edge that only LOOKS like
        test code by name/path, with NO real collected vitest evidence, no
        longer gets any TEST001-004 credit at all -- the structural
        fallback `_edge_is_native_unverified` used to grant TS (T-0552) is
        retired for `.ts`. The edge still exists (so TEST001, "no edge at
        all", stays clean), but it now counts zero cases instead of the one
        the retired fallback used to grant, so it is a genuine TEST002
        finding rather than a silent pass or a TEST013 warning."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/thing.ts",
            "export function doThing(): number {\n  return 0;\n}\n\n"
            '// frob:tests src/thing.ts::doThing kind="unit"\n'
            "export function testDoThing(): void {}\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())  # frob never ran this
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" in rule_ids
        assert "TEST013" not in rule_ids

    # frob:ticket T-1266
    def test_cpp_directive_resolves_via_real_ctest_node_id(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestNativeTestCollectors.test_cpp_directive_resolves_via_real_ctest_node_id  # noqa: E501
        """T-1266 (CHK-SUBSYS-GATES-ACCOUNTING successor): the C/C++ mirror
        of `test_ts_directive_resolves_via_real_vitest_node_id` above --
        T-0886 already made `collect_cpp_tests` source-accurate for the
        common single-source-per-target case (see `TestCppSourceAccurateCollection`
        in this file, which proves the collector itself produces
        `<source>::<name>` node ids), but nothing previously proved that a
        REAL `frob:tests` edge in the graph actually resolves against one
        of those node ids via `_edge_has_execution_evidence`'s first real-
        evidence branch (`_node_id_collected`/`_symref_to_nodeid`), rather
        than falling through to the c/cpp structural fallback
        (`_edge_is_native_unverified`) the same way `test_fires_on_
        structural_only_edge` above proves the UNRESOLVED case does. This
        closes that gap: `tests.node_ids` here holds exactly the node id
        shape `collect_cpp_tests` emits for an unambiguous single-source
        ctest test (`_cpp_node_id`, verified directly in
        `TestCppSourceAccurateCollection.
        test_single_source_target_is_source_accurate`), so a passing run
        here proves the edge takes the REAL-evidence path, not the
        disclosed-unverified one -- TEST013 must NOT fire, matching
        acceptance[0]."""
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/pkg/widget_test.cpp",
            "void widget_add(void) {}\n\n"
            '// frob:tests src/pkg/widget_test.cpp::widget_add kind="unit"\n'
            "void widget_adds(void) {}\n",
        )
        snap = _snapshot(tmp_path)
        # The exact node id collect_cpp_tests would emit (`_cpp_node_id`)
        # for a single-source ctest test named "widget_adds" compiled from
        # this file -- supplied directly here (as
        # `test_ts_directive_resolves_via_real_vitest_node_id` does for
        # vitest) rather than re-running the collector's own subprocess
        # mocking, which `TestCppSourceAccurateCollection` already covers.
        tests = CollectedTests(
            node_ids=frozenset({"src/pkg/widget_test.cpp::widget_adds"})
        )
        cfg = TestPolicy(min_unit_cases=1)
        violations = run_test_gate(snap, (), Nothing(), tests, cfg)
        rule_ids = _rules(violations)
        assert "TEST001" not in rule_ids
        assert "TEST002" not in rule_ids
        assert "TEST013" not in rule_ids


# frob:ticket T-0886
class TestCppSourceAccurateCollection:
    """T-0886: `collect_cpp_tests` cross-references each ctest test's
    executable (parsed from `CTestTestfile.cmake`) against
    `compile_commands.json` and upgrades to a real source-file node id
    whenever the target compiles from exactly one source file, instead of
    always anchoring to the build directory. `ctest`/`cmake` subprocesses
    are mocked (matching `TestCollectCppTests` in tests/test_testing.py,
    which this scope does not own) -- the underlying real-cmake/ctest
    behavior each mock encodes was verified empirically against an actual
    CMake 3.22 configure+ctest run during this ticket's investigation
    (Done report has the transcripts): `--show-only=json-v1`'s own
    `backtrace` field anchors to the CMakeLists.txt `add_test()` call
    site, never the real test source -- confirming route (a) as originally
    conceived cannot be source-accurate on its own, which is why this
    collector instead reads the executable path straight out of
    `CTestTestfile.cmake`."""

    # frob:ticket T-0886
    def _mock_ctest(self, monkeypatch, tmp_path: Path, names: list[str]) -> None:
        from typani import Ok

        import frob.testing._collect_cpp as collect_mod
        from frob.gitio import ProcResult

        monkeypatch.setattr(collect_mod.shutil, "which", lambda name: "/usr/bin/ctest")

        def fake_run_argv(argv, *, cwd=None, timeout_s=300.0):
            payload = json.dumps({"tests": [{"name": n} for n in names]})
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=payload, stderr="")
            )

        monkeypatch.setattr(collect_mod, "run_argv", fake_run_argv)

    # frob:ticket T-0886
    def test_single_source_target_is_source_accurate(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestCppSourceAccurateCollection.test_single_source_target_is_source_accurate  # noqa: E501
        from frob.testing._collect import collect_cpp_tests

        _write(tmp_path, "CMakeLists.txt", "project(widget)\n")
        _write(
            tmp_path,
            "build/CTestTestfile.cmake",
            'add_test(widget_adds "' + str(tmp_path / "build" / "widget_test") + '")\n',
        )
        _write(
            tmp_path,
            "build/compile_commands.json",
            json.dumps(
                [
                    {
                        "directory": str(tmp_path / "build"),
                        "command": (
                            "/usr/bin/c++ -o "
                            "CMakeFiles/widget_test.dir/src/widget_test.cpp.o "
                            "-c src/widget_test.cpp"
                        ),
                        "file": str(tmp_path / "src" / "widget_test.cpp"),
                    }
                ]
            ),
        )
        self._mock_ctest(monkeypatch, tmp_path, ["widget_adds"])

        result = collect_cpp_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset(
            {"src/widget_test.cpp::widget_adds"}
        )

    # frob:ticket T-0886
    def test_multi_source_target_falls_back_loudly(
        self, tmp_path: Path, monkeypatch, caplog
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestCppSourceAccurateCollection.test_multi_source_target_falls_back_loudly  # noqa: E501
        """A binary compiled from two source files cannot be attributed to
        either one without a wrong guess -- collection must fall back to
        the old build-dir anchor AND log a disclosed `FALLBACK` marker, not
        silently guess or silently stay quiet about the downgrade."""
        import logging

        from frob.testing._collect import collect_cpp_tests

        _write(tmp_path, "CMakeLists.txt", "project(widget)\n")
        _write(
            tmp_path,
            "build/CTestTestfile.cmake",
            'add_test(widget_adds "' + str(tmp_path / "build" / "widget_test") + '")\n',
        )
        entries = [
            {
                "directory": str(tmp_path / "build"),
                "command": (
                    "/usr/bin/c++ -o "
                    f"CMakeFiles/widget_test.dir/src/{stem}.cpp.o -c src/{stem}.cpp"
                ),
                "file": str(tmp_path / "src" / f"{stem}.cpp"),
            }
            for stem in ("widget_test", "helper")
        ]
        _write(tmp_path, "build/compile_commands.json", json.dumps(entries))
        self._mock_ctest(monkeypatch, tmp_path, ["widget_adds"])

        with caplog.at_level(logging.WARNING):
            result = collect_cpp_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset({"build::widget_adds"})
        assert any("FALLBACK" in rec.message for rec in caplog.records)

    # frob:ticket T-0886
    def test_no_compile_commands_falls_back_loudly(
        self, tmp_path: Path, monkeypatch, caplog
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestCppSourceAccurateCollection.test_no_compile_commands_falls_back_loudly  # noqa: E501
        """No `compile_commands.json` at all (the common case -- most
        projects never turn `CMAKE_EXPORT_COMPILE_COMMANDS` on) degrades to
        the old build-dir anchor, loudly, never a crash."""
        import logging

        from frob.testing._collect import collect_cpp_tests

        _write(tmp_path, "CMakeLists.txt", "project(widget)\n")
        _write(
            tmp_path,
            "build/CTestTestfile.cmake",
            'add_test(widget_adds "' + str(tmp_path / "build" / "widget_test") + '")\n',
        )
        self._mock_ctest(monkeypatch, tmp_path, ["widget_adds"])

        with caplog.at_level(logging.WARNING):
            result = collect_cpp_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset({"build::widget_adds"})
        assert any("FALLBACK" in rec.message for rec in caplog.records)

    # frob:ticket T-0886
    def test_gtest_discover_tests_include_and_dot_names(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestCppSourceAccurateCollection.test_gtest_discover_tests_include_and_dot_names  # noqa: E501
        """`gtest_discover_tests()` writes its per-case `add_test()` calls
        into a sibling file `CTestTestfile.cmake` only `include()`s -- one
        level of `include()` must still be followed to find them -- and a
        gtest `Suite.Case` name's dot is normalized to `::` (mirroring
        `frob.gates._symref_to_nodeid`'s own transform on the directive
        side) so a `frob:tests` directive naming `Suite::Case` can match."""
        from frob.testing._collect import collect_cpp_tests

        _write(tmp_path, "CMakeLists.txt", "project(widget)\n")
        _write(
            tmp_path,
            "build/CTestTestfile.cmake",
            'include("widget_test_tests.cmake")\n',
        )
        exe = str(tmp_path / "build" / "widget_gtest")
        _write(
            tmp_path,
            "build/widget_test_tests.cmake",
            f'add_test(WidgetSuite.AddsOne "{exe}" --gtest_filter=WidgetSuite.AddsOne)\n',
        )
        _write(
            tmp_path,
            "build/compile_commands.json",
            json.dumps(
                [
                    {
                        "directory": str(tmp_path / "build"),
                        "command": (
                            "/usr/bin/c++ -o "
                            "CMakeFiles/widget_gtest.dir/src/widget_gtest.cpp.o "
                            "-c src/widget_gtest.cpp"
                        ),
                        "file": str(tmp_path / "src" / "widget_gtest.cpp"),
                    }
                ]
            ),
        )
        self._mock_ctest(monkeypatch, tmp_path, ["WidgetSuite.AddsOne"])

        result = collect_cpp_tests(tmp_path)
        assert result.is_ok
        assert result.danger_ok.node_ids == frozenset(
            {"src/widget_gtest.cpp::WidgetSuite::AddsOne"}
        )


# frob:ticket T-0547
class TestTest014AmbiguousConventionMatch:
    """T-0547 (docs/audits/gates-accounting.md B6/E6): `_inferred_unit_cases`
    matches by snake-cased leaf name alone, no module/path binding -- two
    different public functions named the same thing in different files can
    both clear TEST001 off one test that only actually exercises one."""

    # frob:ticket T-0547
    def test_fires_on_cross_file_same_test_collision(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest014AmbiguousConventionMatch.test_fires_on_cross_file_same_test_collision  # noqa: E501
        # The audit's own repro: two `def parse()` in different modules,
        # neither carrying an explicit frob:tests edge, one `test_parse`
        # covering (by convention) both.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg_a/mod.py", "def parse(x):\n    return x\n")
        _write(tmp_path, "src/frob/pkg_b/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test014 = [v for v in violations if v.rule == "TEST014"]
        assert len(test014) == 1
        assert test014[0].severity == Severity.WARN
        assert "pkg_a/mod.py::parse" in test014[0].message
        assert "pkg_b/mod.py::parse" in test014[0].message

    # frob:ticket T-0547
    def test_silent_when_symbol_has_explicit_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest014AmbiguousConventionMatch.test_silent_when_symbol_has_explicit_edge  # noqa: E501
        # An explicit frob:tests edge on either colliding symbol removes it
        # from the ambiguous naming-convention pool entirely.
        from typani.option import Nothing

        _write(
            tmp_path,
            "src/frob/pkg_a/mod.py",
            '# frob:tests tests/test_parse.py::test_parse kind="unit"\n'
            "def parse(x):\n    return x\n",
        )
        _write(tmp_path, "src/frob/pkg_b/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST014" not in _rules(violations)

    # frob:ticket T-0547
    def test_silent_when_no_leaf_name_collision(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest014AmbiguousConventionMatch.test_silent_when_no_leaf_name_collision  # noqa: E501
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg_a/mod.py", "def parse(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_parse.py",
            "def test_parse():\n    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset({"tests/test_parse.py::test_parse"}))
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST014" not in _rules(violations)


# frob:ticket T-0548
class TestTest015VacuousCredit:
    """T-0548 (docs/audits/gates-accounting.md B1/E1): TEST001, the only
    blocking per-symbol test gate, is satisfied by a single collected test
    node id whose name matches -- nothing inspects whether it asserts
    anything. `def test_myfunc(): pass` clears TEST001 today; TEST015
    reuses T-0549's existing assertion heuristic to make that loud."""

    # frob:ticket T-0548
    def test_fires_on_no_op_test_body(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates_suite/test_test_gate.py::TestTest015VacuousCredit.test_fires_on_n\
        # o_op_test_body
        # The audit's own repro: a public function whose only covering
        # test, matched by naming convention, has an empty (no-op) body.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(tmp_path, "tests/test_helper.py", "def test_helper():\n    pass\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_helper.py::test_helper"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        test015 = [v for v in violations if v.rule == "TEST015"]
        assert len(test015) == 1
        assert test015[0].severity == Severity.WARN
        assert "src/frob/pkg/a.py::helper" in test015[0].message
        assert "test_helper" in test015[0].message

    # frob:ticket T-0548
    def test_silent_when_any_matching_test_asserts(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest015VacuousCredit.test_silent_when_any_matching_test_asserts  # noqa: E501
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        _write(
            tmp_path,
            "tests/test_helper.py",
            "def test_helper():\n    assert helper_result() == 1\n"
            "def helper_result():\n    return 1\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/test_helper.py::test_helper"})
        )
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST015" not in _rules(violations)

    # frob:ticket T-0548
    def test_silent_when_no_test_matches_at_all(self, tmp_path: Path) -> None:
        # frob:tests tests/gates_suite/test_test_gate.py::TestTest015VacuousCredit.test_silent_when_no_test_matches_at_all  # noqa: E501
        # No matching test at all is TEST001's own job (already ERROR) --
        # TEST015 only concerns credit that WAS granted, so it must stay
        # silent here rather than double-report the same gap.
        from typani.option import Nothing

        _write(tmp_path, "src/frob/pkg/a.py", "def helper(x):\n    return x\n")
        snap = _snapshot(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_test_gate(snap, (), Nothing(), tests, TestPolicy())
        assert "TEST015" not in _rules(violations)
        assert "TEST001" in _rules(violations)


class TestPairLevelIntegration:
    def _snap_with_dep(self, tmp_path):
        # consumer pkg src/app uses-contract on provider pkg src/core
        _write(tmp_path, "src/core/__init__.py", "def engine():\n    return 1\n")
        _write(
            tmp_path,
            "src/app/__init__.py",
            "# frob:uses-contract src/core/__init__.py::engine\n"
            "def handler():\n    return 2\n",
        )
        return _snapshot(tmp_path)

    def test_test007_fires_on_uncovered_boundary(self, tmp_path):
        # frob:tests src/frob/gates/__init__.py::test_gate
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        snap = self._snap_with_dep(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        pol = TestPolicy(min_unit_cases=1, pair_integration=True)
        violations = run_tg(snap, (), Nothing(), tests, pol)
        assert any(
            v.rule == "TEST007" and "src/app" in v.message and "src/core" in v.message
            for v in violations
        )

    def test_test007_off_by_default(self, tmp_path):
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        snap = self._snap_with_dep(tmp_path)
        tests = CollectedTests(node_ids=frozenset())
        violations = run_tg(snap, (), Nothing(), tests, TestPolicy(min_unit_cases=1))
        assert not any(v.rule == "TEST007" for v in violations)

    def test_test007_passes_when_boundary_tested(self, tmp_path):
        from typani.option import Nothing

        from frob.gates import test_gate as run_tg
        from frob.gates._models import TestPolicy
        from frob.testing import CollectedTests

        _write(tmp_path, "src/core/__init__.py", "def engine():\n    return 1\n")
        _write(
            tmp_path,
            "src/app/__init__.py",
            "# frob:uses-contract src/core/__init__.py::engine\n"
            "def handler():\n    return 2\n",
        )
        _write(
            tmp_path,
            "tests/app/test_boundary.py",
            "def test_app_core():\n"
            '    # frob:tests src/core/__init__.py kind="integration"\n'
            "    assert True\n",
        )
        snap = _snapshot(tmp_path)
        tests = CollectedTests(
            node_ids=frozenset({"tests/app/test_boundary.py::test_app_core"})
        )
        pol = TestPolicy(min_unit_cases=1, pair_integration=True)
        violations = run_tg(snap, (), Nothing(), tests, pol)
        assert not any(v.rule == "TEST007" for v in violations)


# frob:ticket T-0550
class TestGatesDegradeWithoutDiff:
    def test_diff_independent_gates_run_without_git(self, tmp_path):
        """A repo with no valid base (fresh, no commits) must still run the
        diff-independent gates instead of skipping the whole stage."""

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text(
            "# frob:invariant INV-001\ndef f(x):\n    return x\n"
        )
        (tmp_path / "frob.toml").write_text(
            '[fuzz]\nenforce = "invariant-anchored"\n', encoding="utf-8"
        )
        # no git repo at all -> working_diff fails -> must not error the stage
        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"fuzz"}))
        )
        assert report.is_ok, report.err
        assert any(v.rule == "FUZZ001" for v in report.danger_ok.violations)

    # frob:ticket T-0550
    # frob:ticket T-0719
    # frob:tests src/frob/gates/__init__.py::coverage_gate kind="unit"
    def test_diff_dependent_gates_block_loudly_on_failed_diff(self, tmp_path):
        """T-0550/B8 counterexample, narrowed by T-0719: a REAL git repo
        whose `working_diff` genuinely fails (here, a bad `--base` that
        cannot resolve to a merge-base) must still fire COV002 as a loud,
        diff-load-failure violation, never silently pass -- this is the
        T-0550 protection T-0719 explicitly must not weaken. `tmp_path` is
        `git init`ed with a real commit so the failure is unambiguously
        "a real repo's diff broke", not "there is no repo at all" (see
        `test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root`
        below for that other, now-distinguished, case). Kept under its
        original T-0550 name -- not renamed -- because T-0550's archived
        Done report cites this exact pytest node id as evidence
        (tickets-archive.md); this test's scenario changed (no-repo-at-all
        -> real-repo-bad-base) to stay a true positive for the assertion it
        still makes (COV002 fires loudly), but the id itself had to stay
        stable."""

        from frob.gates import GateConfig, run_gates

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def undocumented(x):\n    return x\n")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t.t", "-c", "user.name=t", "add", "-A"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t.t",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                "seed",
            ],
            cwd=tmp_path,
            check=True,
        )

        report = run_gates(
            GateConfig(
                root=str(tmp_path),
                base="does-not-resolve-to-anything",
                gates=frozenset({"coverage"}),
            )
        )
        assert report.is_ok, report.err
        cov002 = [v for v in report.danger_ok.violations if v.rule == "COV002"]
        assert cov002, "COV002 must not silently pass on a real repo's failed diff load"
        assert "failed to load" in cov002[0].message

    # frob:ticket T-0719
    # frob:tests src/frob/gates/__init__.py::coverage_gate kind="unit"
    def test_diff_dependent_gates_pass_quietly_on_a_genuinely_gitless_root(
        self, tmp_path
    ):
        """T-0719: a genuinely git-less `root` (no `.git` anywhere above it,
        e.g. a system-test fixture that never calls `git init`) is not the
        same failure shape as a real repo's broken diff -- there is
        structurally no touched set to enforce COV002 against, so it must
        be treated the same as a clean/empty diff (no violation), not the
        loud diff-load-failure violation
        `test_diff_dependent_gates_block_loudly_on_failed_diff` above pins
        for a real repo."""

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "m.py").write_text("def undocumented(x):\n    return x\n")

        report = run_gates(
            GateConfig(root=str(tmp_path), base="main", gates=frozenset({"coverage"}))
        )
        assert report.is_ok, report.err
        cov002 = [v for v in report.danger_ok.violations if v.rule == "COV002"]
        assert not cov002, (
            f"COV002 must not hard-error on a genuinely git-less root: {cov002}"
        )
