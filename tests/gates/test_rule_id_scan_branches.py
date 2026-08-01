"""T-1279 TEST005 burn-down: `frob.gates._rule_id_scan` branches not
exercised by the existing tests/test_gates.py::TestKnownGateRuleIds
suite -- the comment-skip line, a scanned base directory that does not
exist under the given repo_root, and a `rule=CONST_NAME` reference whose
constant is never assigned anywhere in the scanned tree (left
unresolved, not raised)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._rule_id_scan import generated_gate_rule_ids, scan_emitted_rule_ids


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
