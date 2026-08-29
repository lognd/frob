"""DUPSCHEMA001/GRAPHSCHEMA001 (T-2390 epic child, T-2437):
`frob.gates._dup_graph_schema.{dup_schema_gate,graph_schema_gate}`.

Same two-fixture discipline every T-2390 child carries (a must-now-fire
case AND a must-still-pass control PER TABLE, since these are two
genuinely disjoint checks sharing one child), plus this repo's own real
frob.toml as the concrete proof the fix actually applies here."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

from frob.findings import Severity
from frob.gates._dup_graph_schema import dup_schema_gate, graph_schema_gate


class TestDupGraphSchemaGate:
    # frob:tests src/frob/gates/_dup_graph_schema.py::dup_schema_gate kind="unit"
    def test_dup_must_now_fire_reports_the_undeclared_key(self, tmp_path: Path) -> None:
        """A plausibly misspelled key ("enfore" for "enforce") is
        reported."""
        (tmp_path / "fixture_dup_mod.py").write_text(
            'KNOWN = frozenset({"enforce", "threshold", "region_kernel", '
            '"native_rungs"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [dup_schema]
                known_keys = "fixture_dup_mod:KNOWN"

                [dup]
                enfore = true
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = dup_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_dup_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "DUPSCHEMA001"
        assert "'enfore'" in violations[0].message

    # frob:tests src/frob/gates/_dup_graph_schema.py::dup_schema_gate kind="unit"
    def test_dup_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [dup] table, zero findings."""
        violations = dup_schema_gate(Path.cwd())
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_dup_graph_schema.py::dup_schema_gate kind="unit"
    def test_dup_no_schema_declared_defaults_to_frobs_own_keys_must_fire(
        self, tmp_path: Path
    ) -> None:
        """T-3273 MUST-FIRE: no [dup_schema] known_keys declared defaults
        to frob's own DUP_KNOWN_KEYS -- MEASURED, never UNRESOLVED."""
        (tmp_path / "frob.toml").write_text("[dup]\nenforce = true\n")
        violations = dup_schema_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_dup_graph_schema.py::dup_schema_gate kind="unit"
    def test_dup_no_schema_declared_default_still_flags_unknown_keys(
        self, tmp_path: Path
    ) -> None:
        """T-3273: the default still flags a genuinely unknown key."""
        (tmp_path / "frob.toml").write_text("[dup]\nnot_a_real_key = 1\n")
        violations = dup_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity != Severity.UNRESOLVED

    # frob:tests src/frob/gates/_dup_graph_schema.py::dup_schema_gate kind="unit"
    def test_dup_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = dup_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED

    # frob:tests src/frob/gates/_dup_graph_schema.py::graph_schema_gate kind="unit"
    def test_graph_must_now_fire_reports_the_undeclared_key(
        self, tmp_path: Path
    ) -> None:
        """A plausibly misspelled key ("excludes" for "exclude") is
        reported."""
        (tmp_path / "fixture_graph_mod.py").write_text(
            'KNOWN = frozenset({"exclude"})\n'
        )
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [graph_schema]
                known_keys = "fixture_graph_mod:KNOWN"

                [graph]
                excludes = ["x/**"]
                """
            )
        )
        sys.path.insert(0, str(tmp_path))
        try:
            violations = graph_schema_gate(tmp_path)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("fixture_graph_mod", None)

        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert violations[0].rule == "GRAPHSCHEMA001"
        assert "'excludes'" in violations[0].message

    # frob:tests src/frob/gates/_dup_graph_schema.py::graph_schema_gate kind="unit"
    def test_graph_must_still_pass_this_repos_own_frob_toml(self) -> None:
        """Must-still-pass control: this repo's OWN frob.toml's real
        [graph] table, zero findings."""
        violations = graph_schema_gate(Path.cwd())
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_dup_graph_schema.py::graph_schema_gate kind="unit"
    def test_graph_no_schema_declared_defaults_to_frobs_own_keys_must_fire(
        self, tmp_path: Path
    ) -> None:
        """T-3273 MUST-FIRE: no [graph_schema] known_keys declared
        defaults to frob's own GRAPH_KNOWN_KEYS -- MEASURED, never
        UNRESOLVED."""
        (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["x/**"]\n')
        violations = graph_schema_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-3273
    # frob:tests src/frob/gates/_dup_graph_schema.py::graph_schema_gate kind="unit"
    def test_graph_no_schema_declared_default_still_flags_unknown_keys(
        self, tmp_path: Path
    ) -> None:
        """T-3273: the default still flags a genuinely unknown key."""
        (tmp_path / "frob.toml").write_text('[graph]\nexcludes = ["x/**"]\n')
        violations = graph_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity != Severity.UNRESOLVED

    # frob:tests src/frob/gates/_dup_graph_schema.py::graph_schema_gate kind="unit"
    def test_graph_no_frob_toml_is_unresolved(self, tmp_path: Path) -> None:
        """No frob.toml at all: UNRESOLVED, never a silent zero."""
        violations = graph_schema_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
