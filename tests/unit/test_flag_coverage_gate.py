"""FLAGCOV001 (T-2397): `frob.gates._flag_coverage.flag_coverage_gate`.

Fixture shape mirrors T-2004's own `TestFindDroppedCliFlags` (a tiny
synthetic parser/config pair, never the real 340-field `AppConfig`) plus
this repo's own real `frob.toml` declaration as the must-still-pass
control -- the same two-fixture discipline every T-2390-family child is
required to carry (a must-now-fire case AND a must-still-pass control).
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from frob.findings import Severity
from frob.gates._flag_coverage import flag_coverage_gate


def _write_fixture_project(
    tmp_path: Path,
    *,
    with_config: bool = True,
    with_forwarded: bool = True,
    forwarded_names: frozenset[str] = frozenset({"known_flag"}),
    bad_parser_dotted: bool = False,
) -> Path:
    """A minimal synthetic project: one argparse parser with two flags
    (`known_flag`, `dropped_flag`), one pydantic config model with
    matching fields, and a `frob.toml` declaring the FLAGCOV001 source
    per this test's own knobs -- isolated in `tmp_path`, never touching
    this repo's real `frob.toml`."""
    (tmp_path / "fixture_mod.py").write_text(
        textwrap.dedent(
            """
            import argparse
            from pydantic import BaseModel

            class FixtureConfig(BaseModel):
                model_config = {}
                known_flag: bool = False
                dropped_flag: bool = False

            def build_parser():
                p = argparse.ArgumentParser(prog="fixture")
                p.add_argument("--known-flag", dest="known_flag", action="store_true")
                p.add_argument(
                    "--dropped-flag", dest="dropped_flag", action="store_true"
                )
                return p

            def forwarded_fields():
                return frozenset(%r)

            def not_callable_forwarded():
                return 42
            """
            % (forwarded_names,)
        )
    )
    parser_dotted = (
        "fixture_mod:does_not_exist"
        if bad_parser_dotted
        else "fixture_mod:build_parser"
    )
    lines = [
        "[[docblocks.commands]]",
        'prog = "fixture"',
        f'parser = "{parser_dotted}"',
    ]
    if with_config:
        lines.append('config = "fixture_mod:FixtureConfig"')
    if with_forwarded:
        lines.append('forwarded = "fixture_mod:forwarded_fields"')
    (tmp_path / "frob.toml").write_text("\n".join(lines) + "\n")
    return tmp_path


@pytest.fixture(autouse=True)
def _sys_path_isolation(tmp_path, monkeypatch):
    """Every fixture project's `fixture_mod` lives at a fresh `tmp_path`,
    so put it on `sys.path` for the duration of each test and remove it
    after -- prevents one test's fixture module leaking into the next
    via `sys.modules` caching under the same module name."""
    monkeypatch.syspath_prepend(str(tmp_path))
    yield
    sys.modules.pop("fixture_mod", None)


class TestFlagCoverageGate:
    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_must_now_fire_reports_the_genuinely_dropped_flag(
        self, tmp_path: Path
    ) -> None:
        """Must-now-fire fixture (T-2390-family discipline): a flag NOT in
        the declared `forwarded` set is reported as FLAGCOV001 ERROR; the
        flag that IS in `forwarded` is not."""
        _write_fixture_project(tmp_path)
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "FLAGCOV001"
        assert v.severity == Severity.ERROR
        assert "dropped_flag" in v.message
        assert "known_flag" not in v.message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_must_still_pass_when_everything_is_forwarded(self, tmp_path: Path) -> None:
        """Must-still-pass control: declaring BOTH fields as forwarded
        reports zero findings -- a genuine MEASURED-clean state, not an
        UNRESOLVED default."""
        _write_fixture_project(
            tmp_path, forwarded_names=frozenset({"known_flag", "dropped_flag"})
        )
        violations = flag_coverage_gate(tmp_path)
        assert violations == ()

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_this_repos_own_frob_toml_reports_zero(self) -> None:
        """The real must-still-pass control this ticket exists to prove:
        this repo's OWN `frob.toml`/`AppConfig`/`_build_parser`, all real,
        zero findings -- the exact state T-2387's fix put main into."""
        violations = flag_coverage_gate(Path.cwd())
        assert violations == ()

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_no_declared_sources_is_unresolved_not_empty(self, tmp_path: Path) -> None:
        """No `[[docblocks.commands]]` at all: reported as ONE
        `Severity.UNRESOLVED` finding, never a bare empty list -- the
        fail-loudly doctrine's core claim, that an unmeasured project must
        not read the same as a clean one."""
        (tmp_path / "frob.toml").write_text('min_frob_version = "0.1.0"\n')
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no [[docblocks.commands]]" in violations[0].message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_missing_config_key_is_unresolved(self, tmp_path: Path) -> None:
        """A declared source with no `config=` key: UNRESOLVED, naming the
        missing key -- not silently skipped and not a crash."""
        _write_fixture_project(tmp_path, with_config=False)
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "no config=" in violations[0].message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_missing_forwarded_key_is_unresolved(self, tmp_path: Path) -> None:
        """A declared source with `config=` but no `forwarded=`: UNRESOLVED
        -- this is the portability-bug guard found while building this
        gate (find_dropped_cli_flags's own ambient default is frob's own
        hardcoded field set, wrong for any other project's config)."""
        _write_fixture_project(tmp_path, with_forwarded=False)
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "forwarded=" in violations[0].message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_unresolvable_parser_is_unresolved_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        """A `parser=` dotted path that fails to import/resolve: UNRESOLVED,
        never an uncaught exception out of `frob check`."""
        _write_fixture_project(tmp_path, bad_parser_dotted=True)
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "could not resolve parser=" in violations[0].message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_non_callable_non_set_forwarded_is_unresolved(self, tmp_path: Path) -> None:
        """`forwarded=` resolving to neither a set nor a callable-returning-
        one (a plain int here) is UNRESOLVED, not a crash or a silent
        misinterpretation."""
        _write_fixture_project(tmp_path)
        (tmp_path / "frob.toml").write_text(
            textwrap.dedent(
                """
                [[docblocks.commands]]
                prog = "fixture"
                parser = "fixture_mod:build_parser"
                config = "fixture_mod:FixtureConfig"
                forwarded = "fixture_mod:not_callable_forwarded"
                """
            )
        )
        violations = flag_coverage_gate(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.UNRESOLVED
        assert "not a frozenset" in violations[0].message
