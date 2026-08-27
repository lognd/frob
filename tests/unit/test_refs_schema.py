"""REFSCHEMA001 (T-2390 epic child, T-2428):
`frob.gates._refs_schema.refs_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._refs_schema import refs_schema_gate


class TestRefsSchemaGate:
    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("ptah" for "path") alongside valid
        path/reason values is reported -- the exact defect class this
        check exists to close (a malformed-only check would miss it,
        since path/reason are both still present and valid)."""
        (tmp_path / "fixture_mod.py").write_text(
            'KNOWN = frozenset({"path", "reason"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [refs]
                entrypoint_schema = "fixture_mod:KNOWN"

                [[refs.entrypoint]]
                path = "README.md"
                ptah = "typo alongside valid keys"
                reason = "read by humans"
                """
            )
        )
        import sys

        sys.path.insert(0, str(tmp_path))
        try:
            violations = refs_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "REFSCHEMA001"
        assert "'ptah'" in violations[0].message

    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml, all 29
        [[refs.entrypoint]] entries, zero findings -- the real proof this
        check was not calibrated by weakening it."""
        violations = refs_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [refs] entrypoint_schema declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text(
            '[[refs.entrypoint]]\npath = "x"\nreason = "y"\n'
        )
        violations = refs_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [refs] entrypoint_schema" in violations[0].message

    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A entrypoint_schema dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [refs]
                entrypoint_schema = "does_not_exist_mod:NOPE"

                [[refs.entrypoint]]
                path = "x"
                reason = "y"
                """
            )
        )
        violations = refs_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve entrypoint_schema=" in violations[0].message

    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """entrypoint_schema resolving to neither a set nor a callable
        returning one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [refs]
                entrypoint_schema = "fixture_mod2:KNOWN"

                [[refs.entrypoint]]
                path = "x"
                reason = "y"
                """
            )
        )
        import sys

        sys.path.insert(0, str(tmp_path))
        try:
            violations = refs_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_refs_schema.py::refs_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = refs_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
