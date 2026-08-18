"""DOCBLOCKSSCHEMA001 (T-2390 epic child, T-2434):
`frob.gates._docblocks_schema.docblocks_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.gates._docblocks_schema import docblocks_schema_gate
from frob.gates._models import Severity


class TestDocblocksSchemaGate:
    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("prser" for "parser") alongside
        valid prog/config/forwarded values is reported -- including
        T-2397's own config=/forwarded= keys as legitimate members, not
        flagged themselves."""
        (tmp_path / "fixture_docblocks_mod.py").write_text(
            'KNOWN = frozenset({"prog", "parser", "config", "forwarded"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [docblocks_schema]
                known_keys = "fixture_docblocks_mod:KNOWN"

                [[docblocks.commands]]
                prog = "frob"
                prser = "typo alongside valid keys"
                config = "frob.app.config:AppConfig"
                forwarded = "frob.app._config_external:_all_forwarded_field_names"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = docblocks_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_docblocks_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "DOCBLOCKSSCHEMA001"
        assert "'prser'" in violations[0].message

    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [[docblocks.commands]] entry (incl. T-2397's config=/forwarded=
        keys), zero findings."""
        violations = docblocks_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_no_schema_declared_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No [docblocks_schema] known_keys declared: UNRESOLVED, never a
        silently empty (falsely clean) list."""
        (tmp_path / "frob.toml").write_text(
            '[[docblocks.commands]]\nprog = "x"\nparser = "y:z"\n'
        )
        violations = docblocks_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [docblocks_schema] known_keys" in violations[0].message

    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [docblocks_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [[docblocks.commands]]
                prog = "x"
                parser = "y:z"
                """
            )
        )
        violations = docblocks_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_docblocks_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [docblocks_schema]
                known_keys = "fixture_docblocks_mod2:KNOWN"

                [[docblocks.commands]]
                prog = "x"
                parser = "y:z"
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = docblocks_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_docblocks_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_docblocks_schema.py::docblocks_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = docblocks_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
