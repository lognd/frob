"""ARCHSCHEMA001 (T-2390 epic child, T-2433):
`frob.gates._arch_schema.arch_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.gates._arch_schema import (
    arch_known_keys as _arch_known_keys,
)
from frob.gates._arch_schema import (
    arch_schema_gate as _arch_schema_gate,
)
from frob.gates._models import Severity


class TestArchSchemaGate:
    # frob:tests src/frob/gates/_arch_schema.py::arch_known_keys kind="unit"
    def test_arch_known_keys_matches_load_arch_configs_own_defaults(self) -> None:
        """`arch_known_keys` names exactly the 10 keys
        `frob.repo_meta.load_arch_config` reads."""
        known = _arch_known_keys()
        assert known == {
            "max_function_lines",
            "max_class_methods",
            "max_local_imports",
            "max_nesting_depth",
            "max_file_lines",
            "lcom4_min_methods",
            "lcom4_min_field_using_methods",
            "god_module_min_exports",
            "god_module_min_clusters",
            "mixed_concern_min_decision_points",
        }

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """The epic's own filing-time example: a "max_fuction_lines"
        typo alongside a valid max_class_methods key is reported."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [arch_schema]
                known_keys = "frob.gates._arch_schema:arch_known_keys"

                [arch]
                max_fuction_lines = 60
                max_class_methods = 12
                """
            )
        )
        violations = _arch_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "ARCHSCHEMA001"
        assert "'max_fuction_lines'" in violations[0].message

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [arch] table (5 of the 10 known keys set, plus the genuinely
        different [arch.layering] sub-table) -- zero findings."""
        violations = _arch_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_nested_layering_subtable_is_never_flagged(self, tmp_path: Path) -> None:
        """`[arch.layering]` (T-0620's DIP layering contract) is a
        genuinely different, deliberately inert sub-table -- a dict-
        valued key inside [arch] is excluded from this check entirely,
        never flagged as an undeclared leaf value."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [arch_schema]
                known_keys = "frob.gates._arch_schema:arch_known_keys"

                [arch]
                max_function_lines = 60

                [arch.layering.layers]
                app = ["src/app"]

                [arch.layering.allow]
                app = []
                """
            )
        )
        violations = _arch_schema_gate(tmp_path)
        assert violations == ()

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [arch_schema] known_keys declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text("[arch]\nmax_function_lines = 60\n")
        violations = _arch_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [arch_schema] known_keys" in violations[0].message

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [arch_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [arch]
                max_function_lines = 60
                """
            )
        )
        violations = _arch_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_arch_mod.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [arch_schema]
                known_keys = "fixture_arch_mod:KNOWN"

                [arch]
                max_function_lines = 60
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = _arch_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_arch_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = _arch_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests src/frob/gates/_arch_schema.py::arch_schema_gate kind="unit"
    def test_no_arch_table_at_all_is_clean_not_error(self, tmp_path: Path) -> None:
        """No [arch] table at all (it's optional): zero findings, not an
        error."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [arch_schema]
                known_keys = "frob.gates._arch_schema:arch_known_keys"
                """
            )
        )
        violations = _arch_schema_gate(tmp_path)
        assert violations == ()
