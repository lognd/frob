"""T-1279 TEST005 burn-down: `frob.gates._rule_id_scan` branches not
exercised by the existing tests/test_gates.py::TestKnownGateRuleIds
suite -- the comment-skip line, a scanned base directory that does not
exist under the given repo_root, and a `rule=CONST_NAME` reference whose
constant is never assigned anywhere in the scanned tree (left
unresolved, not raised).

T-1937 added `TestScanCandidateRuleIdLiterals`/`TestFindUnregisteredRuleIds`
below: the broader, shape-agnostic completeness net (`scan_candidate_
rule_id_literals`/`find_unregistered_rule_ids`) that catches a bare
positional argument, a `code=` kwarg, and a typed const assignment -- the
exact three construction shapes that let SYS109/BUDGET001 and friends/
CVEFP001 respectively bypass `scan_emitted_rule_ids` above and stay
invisible to the `_KNOWN_GATE_RULES` registry (and therefore to the
T-0756 acceptance preflight that scrapes it) until this ticket."""

from __future__ import annotations

from pathlib import Path

from frob.gates._rule_id_scan import (
    RETIRED_RULE_IDS,
    find_unregistered_rule_ids,
    generated_gate_rule_ids,
    scan_candidate_rule_id_literals,
    scan_emitted_rule_ids,
)
from frob.gates._waive import known_gate_rule_ids


class TestScanEmittedRuleIdsBranches:
    def test_commented_out_rule_literal_is_skipped(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_commented_out_rule_literal_is_skipped  # noqa: E501
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            '# rule="ZZZTEST010" -- commented out, must not be picked up\n'
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST011")\n'
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert "ZZZTEST010" not in found
        assert "ZZZTEST011" in found

    def test_missing_scanned_base_directory_is_skipped_not_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_missing_scanned_base_directory_is_skipped_not_an_error  # noqa: E501
        # Neither `src/frob/gates` nor `src/frob/strata` exists under
        # this empty tmp_path -- `scan_emitted_rule_ids` must degrade to
        # an empty result rather than raising on the missing dirs.
        found = scan_emitted_rule_ids(tmp_path)
        assert found == {}

    def test_unresolved_const_ref_is_left_out(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_unresolved_const_ref_is_left_out  # noqa: E501
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        # ZZZ_UNRESOLVED is referenced via `rule=ZZZ_UNRESOLVED` but never
        # assigned anywhere in the scanned tree -- the resolve loop must
        # leave it out of `found` rather than raising a KeyError.
        (gates_dir / "_synthetic.py").write_text(
            "def synthetic_gate():\n    return Violation(rule=ZZZ_UNRESOLVED)\n"
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert found == {}

    def test_const_ref_resolves_against_assignment_in_another_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches.test_const_ref_resolves_against_assignment_in_another_file  # noqa: E501
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_constants.py").write_text('ZZZ_CONST = "ZZZTEST012"\n')
        (gates_dir / "_synthetic.py").write_text(
            "def synthetic_gate():\n    return Violation(rule=ZZZ_CONST)\n"
        )

        found = scan_emitted_rule_ids(tmp_path)

        assert found.get("ZZZTEST012") == "src/frob/gates/_synthetic.py:2"


class TestGeneratedGateRuleIdsRetiredOverride:
    def test_default_retired_set_is_module_constant(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_rule_id_scan_branches.py::TestGeneratedGateRuleIdsRetiredOverride.test_default_retired_set_is_module_constant  # noqa: E501
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n    return Violation(rule="ZZZTEST013")\n'
        )

        # No `retired=` passed: falls back to the module-level
        # `RETIRED_RULE_IDS` default (empty in this repo today), so the
        # freshly scanned id is NOT excluded.
        generated = generated_gate_rule_ids(tmp_path)

        assert "ZZZTEST013" in generated


class TestScanCandidateRuleIdLiterals:
    """T-1937: the shape-agnostic broad scan -- matches any quoted,
    rule-id-SHAPED string literal anywhere under `src/`, independent of
    `SCANNED_BASES` and independent of the `rule=`/`code=` keyword (if
    any) introducing it."""

    def test_finds_bare_positional_argument(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.te\
        # st_finds_bare_positional_argument
        # The exact SYS109 shape: a rule-id-shaped string passed as a bare
        # positional argument, no `rule=`/`code=` keyword at all -- the
        # shape `scan_emitted_rule_ids` structurally cannot detect.
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            "def synthetic_gate():\n"
            '    return _selfaudit_violation("ZZZTEST020", node, detail)\n'
        )

        found = scan_candidate_rule_id_literals(tmp_path)

        assert found.get("ZZZTEST020") == "src/frob/gates/_synthetic.py:2"

    def test_finds_typed_const_assignment(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.te\
        # st_finds_typed_const_assignment
        # The exact CVEFP001 shape: a type-annotated pydantic field
        # default, `rule: str = "..."` -- `_LITERAL_PATTERN` does not
        # tolerate the `: str` annotation between the keyword and `=`.
        strata_dir = tmp_path / "src" / "frob" / "strata"
        strata_dir.mkdir(parents=True)
        (strata_dir / "_synthetic.py").write_text(
            "class SyntheticViolation(BaseModel):\n"
            '    rule: str = "ZZZTEST021"\n'
        )

        found = scan_candidate_rule_id_literals(tmp_path)

        assert found.get("ZZZTEST021") == "src/frob/strata/_synthetic.py:2"

    def test_finds_code_kwarg_outside_scanned_bases(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.te\
        # st_finds_code_kwarg_outside_scanned_bases
        # The BUDGET001/CHECK001/DEPLOY00x/DERIVED001 shape: a `code=`
        # kwarg (sibling to `rule=`) in a package outside `SCANNED_BASES`
        # entirely (here `src/frob/app`, matching the real BUDGET001/
        # CHECK001 home package).
        app_dir = tmp_path / "src" / "frob" / "app"
        app_dir.mkdir(parents=True)
        (app_dir / "_synthetic.py").write_text(
            "def synthetic_check():\n"
            '    return Diagnostic(severity="error", code="ZZZTEST022")\n'
        )

        found = scan_candidate_rule_id_literals(tmp_path)

        assert found.get("ZZZTEST022") == "src/frob/app/_synthetic.py:2"

    def test_inline_comment_example_not_picked_up(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.te\
        # st_inline_comment_example_not_picked_up
        # The real false-positive this scan's own dev process hit: an
        # inline trailing comment's prose example (`# e.g. "F401"`) is
        # code-line-adjacent, not a whole-line comment, so it must be
        # stripped separately from the bare `stripped.startswith("#")`
        # whole-line check.
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'code: str | None = None  # e.g. "ZZZTEST023", "ZZZTEST024"\n'
        )

        found = scan_candidate_rule_id_literals(tmp_path)

        assert "ZZZTEST023" not in found
        assert "ZZZTEST024" not in found

    def test_whole_line_comment_not_picked_up(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals.te\
        # st_whole_line_comment_not_picked_up
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            '# see "ZZZTEST025" -- commented out, must not be picked up\n'
        )

        found = scan_candidate_rule_id_literals(tmp_path)

        assert "ZZZTEST025" not in found


class TestFindUnregisteredRuleIds:
    """T-1937: `find_unregistered_rule_ids` is the completeness check
    `_KNOWN_GATE_RULES` must return empty against, repo-wide -- the
    acceptance shape this ticket exists to guarantee."""

    def test_empty_when_every_candidate_is_known_or_retired(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_e\
        # mpty_when_every_candidate_is_known_or_retired
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'def synthetic_gate():\n'
            '    return _selfaudit_violation("ZZZTEST026", node, detail)\n'
        )

        missing = find_unregistered_rule_ids(
            tmp_path, known=frozenset({"ZZZTEST026"})
        )

        assert missing == {}

    def test_reports_a_candidate_missing_from_both_known_and_retired(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_r\
        # eports_a_candidate_missing_from_both_known_and_retired
        # Also proves the "non-gates package" acceptance shape: the
        # synthetic rule lives under src/frob/perf, well outside
        # SCANNED_BASES ("src/frob/gates", "src/frob/strata"), and is
        # still caught.
        perf_dir = tmp_path / "src" / "frob" / "perf"
        perf_dir.mkdir(parents=True)
        (perf_dir / "_synthetic.py").write_text(
            "def synthetic_perf_check():\n"
            '    return Diagnostic(code="ZZZTEST027")\n'
        )

        missing = find_unregistered_rule_ids(tmp_path, known=frozenset())

        assert missing.get("ZZZTEST027") == "src/frob/perf/_synthetic.py:2"

    def test_retired_id_is_excluded_even_when_shape_matches(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_r\
        # etired_id_is_excluded_even_when_shape_matches
        # Mirrors the real TIERBDEMO001 case: a candidate that IS a
        # construction site, deliberately excluded via `retired=` rather
        # than absent from `known` by accident.
        gates_dir = tmp_path / "src" / "frob" / "gates"
        gates_dir.mkdir(parents=True)
        (gates_dir / "_synthetic.py").write_text(
            'RULE = "ZZZTEST028"\n'
        )

        missing = find_unregistered_rule_ids(
            tmp_path, known=frozenset(), retired=frozenset({"ZZZTEST028"})
        )

        assert missing == {}

    def test_real_repo_registry_is_complete(self) -> None:
        # frob:tests \
        # tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds.test_r\
        # eal_repo_registry_is_complete
        # T-1937's own drift-lock: every rule-id-shaped literal anywhere
        # under this repo's real src/ tree (not just SCANNED_BASES) must
        # be a member of `known_gate_rule_ids()` or `RETIRED_RULE_IDS`.
        # Before this ticket's fix this failed on 8 real ids (BUDGET001/
        # CHECK001/CVEFP001/DEPLOY001/DEPLOY002/DEPLOY003/DERIVED001/
        # SYS109) -- TIERBDEMO001 was always correctly excluded via
        # RETIRED_RULE_IDS, and SYS104 has zero live construction sites
        # (see frob.gates._rule_id_scan's module docstring for the full
        # diagnosis of each).
        repo_root = Path(__file__).resolve().parents[2]
        missing = find_unregistered_rule_ids(
            repo_root, known=known_gate_rule_ids(), retired=RETIRED_RULE_IDS
        )
        assert not missing, (
            "rule id(s) shaped like a live gate rule found anywhere under "
            "src/ but missing from both _KNOWN_GATE_RULES and "
            f"RETIRED_RULE_IDS: {missing}"
        )
