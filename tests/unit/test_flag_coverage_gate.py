"""FLAGCOV001 (T-2397): `frob.gates._flag_coverage.flag_coverage_gate`.

Fixture shape mirrors T-2004's own `TestFindDroppedCliFlags` (a tiny
synthetic parser/config pair, never the real 340-field `AppConfig`) plus
this repo's own real `frob.toml` declaration as the must-still-pass
control -- the same two-fixture discipline every T-2390-family child is
required to carry (a must-now-fire case AND a must-still-pass control).

T-4171: the gate's own resolver spawn is the IMPORTING kind
(`project_import_argv`) and must never sync/mutate the checked
project's environment itself (T-4163's dirty-tree doctrine, extended to
importing spawns). So every fixture here plays the role T-4163 assigns
to the operator/CI: it runs `uv sync --project <tmp_path>` itself, as an
explicit step, BEFORE invoking `flag_coverage_gate` -- exactly the
real-world precondition ("a project that genuinely needs a fresh sync
should run `uv sync` itself") rather than relying on the gate to sync a
throwaway `tmp_path` on its own.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from frob.findings import Severity
from frob.gates._flag_coverage import flag_coverage_gate


# frob:waive WIRE001 follow_up="T-4151" reason="a private per-file fixture helper used \
# only by this file's own tests -- same shape as _write_fixture_project immediately \
# below it, never called from production code by design (T-4171)"
def _sync_fixture_project(root: Path) -> None:
    """Explicit `uv sync --project <root>` step (T-4171): the fixture's
    own precondition for `flag_coverage_gate`'s no-mutate resolver spawn
    to find an already-present environment to import from, mirroring
    what a real operator/CI must do before running `frob check` against
    a cold checkout."""
    subprocess.run(
        ["uv", "sync", "--project", str(root)],
        check=True,
        capture_output=True,
        text=True,
    )


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
    # T-4147: the resolver now runs `uv run --project tmp_path python -c
    # ...` in a real project environment, so tmp_path needs a real
    # pyproject.toml (package=false: a virtual, buildless project -- this
    # fixture has no installable package of its own, just a loose module
    # on the project root importable via uv's default rootdir-on-sys.path
    # behavior) declaring `pydantic` so `fixture_mod`'s own import resolves.
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "flagcov-fixture"
            version = "0.0.1"
            requires-python = ">=3.11"
            dependencies = ["pydantic"]

            [tool.uv]
            package = false
            """
        )
    )
    # T-4171: `flag_coverage_gate`'s resolver spawn is the IMPORTING kind
    # and never syncs/mutates `root`'s environment itself -- sync it here,
    # explicitly, as the fixture's own precondition (the role T-4163's
    # doctrine assigns to the operator/CI, not the gate).
    _sync_fixture_project(tmp_path)
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
        assert "parser=" in violations[0].message
        assert (
            "failed to resolve in its own project environment" in violations[0].message
        )

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
        assert "forwarded=" in violations[0].message
        assert "not a set" in violations[0].message

    # frob:tests src/frob/gates/_flag_coverage.py::flag_coverage_gate kind="unit"
    def test_project_dependency_not_in_frobs_own_interpreter_still_resolves(
        self, tmp_path: Path
    ) -> None:
        """T-3887's own off-repo doctrine, applied directly: `fixture_mod`
        here imports `cattrs` at module scope -- a real package NOT
        installed in frob's own interpreter (verified in this same test,
        not assumed) but declared as this fixture project's own
        dependency. Pre-T-4147, `resolve_dotted_symbol`'s plain
        `importlib.import_module` ran in frob's interpreter and this would
        have failed with ImportError, reporting UNRESOLVED forever. Post-
        T-4147, the resolver spawns inside the fixture project's own `uv
        run --project` environment, where `cattrs` genuinely is installed
        -- a MEASURED, clean pass proves the fix, not merely that some
        `pytest` in this repo's own env still exercises the code path."""
        import importlib.util

        assert importlib.util.find_spec("cattrs") is None, (
            "cattrs must NOT be importable from frob's own interpreter for "
            "this test to prove anything -- if this fails, frob's own "
            "dependency set changed and this fixture needs a different "
            "marker package"
        )
        _write_fixture_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent(
                """
                [project]
                name = "flagcov-fixture"
                version = "0.0.1"
                requires-python = ">=3.11"
                dependencies = ["pydantic", "cattrs"]

                [tool.uv]
                package = false
                """
            )
        )
        (tmp_path / "fixture_mod.py").write_text(
            textwrap.dedent(
                """
                import argparse
                import cattrs  # noqa: F401 -- proves this module resolved in ITS OWN env
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
                    return frozenset({"known_flag", "dropped_flag"})
                """
            )
        )
        # T-4171: the rewritten pyproject.toml above adds `cattrs` to the
        # dependency set -- re-sync so the already-present environment
        # this gate's no-mutate resolver spawn relies on actually has it.
        _sync_fixture_project(tmp_path)
        violations = flag_coverage_gate(tmp_path)
        assert violations == ()
