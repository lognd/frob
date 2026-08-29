"""TESTRUNNERSCHEMA001 (T-2390 epic child, T-2436):
`frob.gates._test_runner_schema.test_runner_schema_gate`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control), plus this repo's own real frob.toml
as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._test_runner_schema import (
    test_runner_schema_gate as _test_runner_schema_gate,
)


class TestTestRunnerSchemaGate:
    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("al_command" for "all_command")
        alongside otherwise-valid values is reported."""
        (tmp_path / "fixture_runner_mod.py").write_text(
            'KNOWN = frozenset({"language", "command", "all_command", '
            '"cwd", "collector", "timeout_s"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [test_runner_schema]
                known_keys = "fixture_runner_mod:KNOWN"

                [[test.runner]]
                language = "python"
                command = ["pytest", "{ids}"]
                al_command = ["pytest"]
                cwd = "."
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = _test_runner_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_runner_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "TESTRUNNERSCHEMA001"
        assert "'al_command'" in violations[0].message

    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml, all 4
        [[test.runner]] entries, zero findings."""
        violations = _test_runner_schema_gate(Path.cwd())
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_no_schema_declared_defaults_to_frobs_own_keys_must_fire(
        self, tmp_path: Path
    ) -> None:
        """T-3273 MUST-FIRE: no [test_runner_schema] known_keys declared
        defaults to frob's own TEST_RUNNER_KNOWN_KEYS -- MEASURED, never
        UNRESOLVED."""
        (tmp_path / "frob.toml").write_text(
            '[[test.runner]]\nlanguage = "python"\ncommand = ["x"]\n'
            'all_command = ["y"]\n'
        )
        violations = _test_runner_schema_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_no_schema_declared_default_still_flags_unknown_keys(
        self, tmp_path: Path
    ) -> None:
        """T-3273: the default still flags a genuinely unknown key."""
        (tmp_path / "frob.toml").write_text(
            '[[test.runner]]\nlanguage = "python"\nnot_a_real_key = "x"\n'
        )
        violations = _test_runner_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity != Severity.UNRESOLVED

    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_unresolvable_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [test_runner_schema]
                known_keys = "does_not_exist_mod:NOPE"

                [[test.runner]]
                language = "python"
                command = ["x"]
                all_command = ["y"]
                """
            )
        )
        violations = _test_runner_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_non_set_non_callable_schema_value_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """known_keys resolving to neither a set nor a callable returning
        one: UNRESOLVED, not a crash or silent misuse."""
        (tmp_path / "fixture_runner_mod2.py").write_text("KNOWN = 42\n")
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [test_runner_schema]
                known_keys = "fixture_runner_mod2:KNOWN"

                [[test.runner]]
                language = "python"
                command = ["x"]
                all_command = ["y"]
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = _test_runner_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_runner_mod2", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message

    # frob:tests src/frob/gates/_test_runner_schema.py::test_runner_schema_gate \
    # kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = _test_runner_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
