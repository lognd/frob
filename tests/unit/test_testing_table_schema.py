"""TESTINGSCHEMA001 (T-2390 epic child, T-2432):
`frob.gates._testing_schema.testing_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._testing_schema import testing_known_keys as _testing_known_keys
from frob.gates._testing_schema import testing_schema_gate as _testing_schema_gate


class TestTestingSchemaGate:
    # frob:tests src/frob/gates/_testing_schema.py::testing_known_keys kind="unit"
    def test_testing_known_keys_reads_test_policy_model_fields(self) -> None:
        """`testing_known_keys` is sourced from `TestPolicy.model_fields`
        itself -- no hand-duplicated field list to drift."""
        known = _testing_known_keys()
        assert "min_unit_cases" in known
        assert "unit_branch_cov" in known
        assert "require_branch_coverage_for_test001" in known

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("min_unit_case" for
        "min_unit_cases") alongside valid keys is reported -- the exact
        defect class this check exists to close, since `_load_test_
        config`'s own pre-filter would silently drop it before TestPolicy
        is even constructed (a bare model-validation check would never
        see it)."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [testing_schema]
                known_keys = "frob.gates._testing_schema:testing_known_keys"

                [testing]
                min_unit_case = 1
                min_integration = 1
                """
            )
        )
        violations = _testing_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "TESTINGSCHEMA001"
        assert "'min_unit_case'" in violations[0].message

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [testing] table, zero findings."""
        violations = _testing_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [testing_schema] known_keys declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text("[testing]\nmin_unit_cases = 1\n")
        violations = _testing_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [testing_schema] known_keys" in violations[0].message

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [testing_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [testing]
                min_unit_cases = 1
                """
            )
        )
        violations = _testing_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_testing_mod.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [testing_schema]
                known_keys = "fixture_testing_mod:KNOWN"

                [testing]
                min_unit_cases = 1
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = _testing_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_testing_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = _testing_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests src/frob/gates/_testing_schema.py::testing_schema_gate kind="unit"
    def test_no_testing_table_at_all_is_clean_not_error(self, tmp_path: Path) -> None:
        """No [testing] table at all (it's optional): zero findings, not
        an error."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [testing_schema]
                known_keys = "frob.gates._testing_schema:testing_known_keys"
                """
            )
        )
        violations = _testing_schema_gate(tmp_path)
        assert violations == ()
