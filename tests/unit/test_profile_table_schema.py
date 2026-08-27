"""PROFILESCHEMA001 (T-2390 epic child, T-2430):
`frob.gates._profile_schema.profile_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._profile_schema import profile_schema_gate


class TestProfileSchemaGate:
    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("overide_ratchet" for
        "override_ratchet") alongside a valid `profile` value is
        reported."""
        (tmp_path / "fixture_profile_mod.py").write_text(
            'KNOWN = frozenset({"profile", "override_ratchet"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [profile_schema]
                known_keys = "fixture_profile_mod:KNOWN"

                [profile]
                profile = "rapid"
                overide_ratchet = true
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = profile_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_profile_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "PROFILESCHEMA001"
        assert "'overide_ratchet'" in violations[0].message

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [profile] table, zero findings."""
        violations = profile_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [profile_schema] known_keys declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text('[profile]\nprofile = "standard"\n')
        violations = profile_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [profile_schema] known_keys" in violations[0].message

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [profile_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [profile]
                profile = "standard"
                """
            )
        )
        violations = profile_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_profile_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [profile_schema]
                known_keys = "fixture_profile_mod2:KNOWN"

                [profile]
                profile = "standard"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = profile_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_profile_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = profile_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests src/frob/gates/_profile_schema.py::profile_schema_gate kind="unit"
    def test_no_profile_table_at_all_is_clean_not_error(self, tmp_path: Path) -> None:
        """No [profile] table at all (it's optional): zero findings, not
        an error -- distinct from the must-now-fire/UNRESOLVED cases."""
        (tmp_path / "fixture_profile_mod3.py").write_text(
            'KNOWN = frozenset({"profile", "override_ratchet"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [profile_schema]
                known_keys = "fixture_profile_mod3:KNOWN"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = profile_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_profile_mod3", None)

        assert violations == ()
