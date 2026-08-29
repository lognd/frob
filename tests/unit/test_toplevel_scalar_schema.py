"""TOPSCALARSCHEMA001 (T-2390 epic child, T-2431):
`frob.gates._toplevel_scalar_schema.toplevel_scalar_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._toplevel_scalar_schema import toplevel_scalar_schema_gate


class TestTopLevelScalarSchemaGate:
    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled top-level scalar key
        ("min_frob_verison" typo alongside a valid check_base) is
        reported -- table headers (dicts) are never flagged, only bare
        scalar keys."""
        (tmp_path / "fixture_top_mod.py").write_text(
            'KNOWN = frozenset({"min_frob_version", "check_base"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                min_frob_verison = "0.1.0"
                check_base = "main"

                [toplevel_scalar_schema]
                known_keys = "fixture_top_mod:KNOWN"

                [arch]
                max_file_lines = 800
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = toplevel_scalar_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_top_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "TOPSCALARSCHEMA001"
        assert "'min_frob_verison'" in violations[0].message

    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml, both real
        top-level scalars (min_frob_version, check_base) plus every real
        [table] header -- zero findings."""
        violations = toplevel_scalar_schema_gate(Path.cwd())
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_no_schema_declared_defaults_to_frobs_own_keys_must_fire(
        self, tmp_path: Path
    ) -> None:
        """T-3273 MUST-FIRE: no [toplevel_scalar_schema] known_keys
        declared defaults to frob's own TOPLEVEL_SCALAR_KNOWN_KEYS --
        MEASURED, never UNRESOLVED."""
        (tmp_path / "frob.toml").write_text('check_base = "main"\n')
        violations = toplevel_scalar_schema_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_no_schema_declared_default_still_flags_unknown_keys(
        self, tmp_path: Path
    ) -> None:
        """T-3273: the default still flags a genuinely unknown key."""
        (tmp_path / "frob.toml").write_text(
            'check_base = "main"\nnot_a_real_key = "x"\n'
        )
        violations = toplevel_scalar_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity != Severity.UNRESOLVED

    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                check_base = "main"

                [toplevel_scalar_schema]
                known_keys = "does_not_exist_mod:NOPE"
                """
            )
        )
        violations = toplevel_scalar_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_top_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                check_base = "main"

                [toplevel_scalar_schema]
                known_keys = "fixture_top_mod2:KNOWN"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = toplevel_scalar_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_top_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = toplevel_scalar_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests \
    # src/frob/gates/_toplevel_scalar_schema.py::toplevel_scalar_schema_gate kind="unit"
    def test_table_headers_are_never_flagged(self, tmp_path: Path) -> None:
        """A [table] name that happens not to be in known_keys is NEVER
        flagged -- this check only concerns bare scalar keys, table
        headers (parsed as dicts) are excluded entirely."""
        (tmp_path / "fixture_top_mod3.py").write_text(
            'KNOWN = frozenset({"check_base"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                check_base = "main"

                [toplevel_scalar_schema]
                known_keys = "fixture_top_mod3:KNOWN"

                [some_unrelated_table]
                key = "value"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = toplevel_scalar_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_top_mod3", None)

        assert violations == ()
