"""NATIVESCHEMA001 (T-2390 epic child, T-2429):
`frob.gates._native_schema.native_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.gates._models import Severity
from frob.gates._native_schema import native_schema_gate


class TestNativeSchemaGate:
    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("buld_cmd" for "build_cmd") alongside
        valid name/build_cmd/language values is reported."""
        (tmp_path / "fixture_native_mod.py").write_text(
            'KNOWN = frozenset({"name", "build_cmd", "language"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [native_schema]
                known_keys = "fixture_native_mod:KNOWN"

                [[native]]
                name = "strata_core"
                build_cmd = "make core"
                buld_cmd = "typo alongside valid keys"
                language = "rust"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = native_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_native_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "NATIVESCHEMA001"
        assert "'buld_cmd'" in violations[0].message

    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml, both
        [[native]] entries, zero findings."""
        violations = native_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [native_schema] known_keys declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text('[[native]]\nname = "x"\nbuild_cmd = "y"\n')
        violations = native_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [native_schema] known_keys" in violations[0].message

    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [native_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [[native]]
                name = "x"
                build_cmd = "y"
                """
            )
        )
        violations = native_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_native_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [native_schema]
                known_keys = "fixture_native_mod2:KNOWN"

                [[native]]
                name = "x"
                build_cmd = "y"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = native_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_native_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_native_schema.py::native_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = native_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
