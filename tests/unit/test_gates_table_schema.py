"""GATESSCHEMA001 (T-2390 epic child, T-2435):
`frob.gates._gates_schema.gates_schema_gate`.

Two genuinely different validation shapes -- see the module's own
docstring. Same two-fixture discipline every T-2390 child carries (a
must-now-fire case AND a must-still-pass control per shape), plus this
repo's own real frob.toml as the concrete proof the fix actually applies
here."""

from __future__ import annotations

import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._gates_schema import gates_schema_gate


class TestGatesSchemaGate:
    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_must_now_fire_reports_the_undeclared_ratchet_key(
        self, tmp_path: Path
    ) -> None:
        """A plausibly misspelled key ("rulez" for "rules") in
        [gates.ratchet] is reported."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [gates_schema]
                ratchet_known_keys = "frob.gates._gates_schema:GATES_RATCHET_KNOWN_KEYS"

                [gates.ratchet]
                rulez = []
                """
            )
        )
        violations = gates_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "GATESSCHEMA001"
        assert "'rulez'" in violations[0].message

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_must_now_fire_reports_the_unregistered_severity_rule_id(
        self, tmp_path: Path
    ) -> None:
        """A misspelled rule id ("COV0011") as a [gates.severity] key is
        reported against the live _KNOWN_GATE_RULES registry -- the
        existing reader's own graceful bad-VALUE handling never catches
        a bad KEY, which is exactly the gap this half of the check
        closes."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [gates_schema]
                ratchet_known_keys = "frob.gates._gates_schema:GATES_RATCHET_KNOWN_KEYS"

                [gates.severity]
                COV0011 = "error"
                """
            )
        )
        violations = gates_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "GATESSCHEMA001"
        assert "COV0011" in violations[0].message

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [gates.ratchet] (rules=[]) and [gates.severity] (18 real,
        registered rule ids) -- zero findings."""
        violations = gates_schema_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_no_ratchet_schema_declared_is_unresolved_not_empty(
        self, tmp_path: Path
    ) -> None:
        """No [gates_schema] ratchet_known_keys declared: the
        [gates.ratchet] half is UNRESOLVED, never a silently empty
        (falsely clean) list."""
        (tmp_path / "frob.toml").write_text("[gates.ratchet]\nrules = []\n")
        violations = gates_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [gates_schema] ratchet_known_keys" in violations[0].message

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_unresolvable_ratchet_schema_dotted_path_is_unresolved(
        self, tmp_path: Path
    ) -> None:
        """A ratchet_known_keys dotted path that fails to import/resolve:
        UNRESOLVED, never a crash."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [gates_schema]
                ratchet_known_keys = "does_not_exist_mod:NOPE"

                [gates.ratchet]
                rules = []
                """
            )
        )
        violations = gates_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve ratchet_known_keys=" in violations[0].message

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = gates_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests src/frob/gates/_gates_schema.py::gates_schema_gate kind="unit"
    def test_no_gates_table_at_all_is_clean_not_error(self, tmp_path: Path) -> None:
        """No [gates.ratchet]/[gates.severity] at all (both optional):
        zero findings, not an error, once the ratchet schema is
        declared."""
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [gates_schema]
                ratchet_known_keys = "frob.gates._gates_schema:GATES_RATCHET_KNOWN_KEYS"
                """
            )
        )
        violations = gates_schema_gate(tmp_path)
        assert violations == ()
