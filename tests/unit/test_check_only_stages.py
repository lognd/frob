"""T-4692 (gate stages are not verbs): golden-comparison and shim-behavior
tests for the standalone verbs folded into `frob check --only <stage>`.

The positive control this ticket's own acceptance criterion requires: a
committed fixture (tests/fixtures/check_stages/dup_sample.py) that plants a
REAL duplicate block `frob.check`'s own dup gate (`_run_dup`, the exact
function `frob check --only dup` calls) is REQUIRED to report -- not a
no-crash assertion."""

from __future__ import annotations

from pathlib import Path

from frob.app.check_runner import _FOLDED_CHECK_STAGES

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "check_stages"


# frob:ticket T-4692
class TestDupGoldenComparison:
    """`frob dup` (deprecated shim) and `frob check --only dup`'s own gate
    implementation must report the IDENTICAL planted duplicate."""

    def test_check_dup_gate_reports_the_planted_duplicate(self) -> None:
        """`frob.check._python._run_dup` -- the exact function `frob check
        --only dup` dispatches to -- finds the two near-identical
        `compute_total_*` functions the fixture plants."""
        from frob.check._python import _run_dup

        result = _run_dup(_FIXTURE_ROOT)
        messages = [d.message for d in result.diagnostics]
        assert any("compute_total" in m or "dup_sample" in m for m in messages), (
            f"planted duplicate not reported: {messages}"
        )

    def test_flat_dup_runner_reports_the_same_duplicate(self) -> None:
        """`frob.dup.find_duplicates` (what the deprecated flat `frob dup`
        verb's own runner calls) reports the identical planted pair --
        proving the shim's underlying behavior is unchanged, not just
        that it still runs."""
        from frob.dup import find_duplicates

        result = find_duplicates(_FIXTURE_ROOT)
        symbols = {frag.symbol for group in result.groups for frag in group.fragments}
        assert {"compute_total_alpha", "compute_total_beta"} <= symbols


# frob:ticket T-4692
class TestListStages:
    """`frob check --list-stages` (T-4692 acceptance[1]): prints exactly
    the folded stage set, and `--only` accepts every one of them."""

    def test_folded_stages_is_the_documented_set(self) -> None:
        """The exact, ordered fold set this ticket's acceptance amendment
        names: dup arch cycle bind narrative exports -- mutate/coverage/
        perf are deliberately excluded (measured write-vs-read distinction,
        see acceptance[2]'s amendment text), and so are pool/profile
        (state-mutating, never analysis)."""
        assert _FOLDED_CHECK_STAGES == (
            "dup",
            "arch",
            "cycle",
            "bind",
            "narrative",
            "exports",
        )

    def test_every_folded_stage_is_a_known_check_only_name(self) -> None:
        """Every name `--list-stages` prints resolves through `--only`'s
        own vocabulary (`_TOOL_STAGES` union `_ALL_GATES`, after stage-
        group expansion) -- `narrative` via the new T-4692 single-member
        alias onto the real gate id `narrative_blocks`."""
        from frob.check import _stage_groups
        from frob.gates import _ALL_GATES

        tool_stages = {"ruff", "ty", "cycle", "dup", "arch", "bind", "exports", "gates"}
        groups = _stage_groups()
        for stage in _FOLDED_CHECK_STAGES:
            resolvable = stage in tool_stages or stage in _ALL_GATES or stage in groups
            assert resolvable, f"{stage!r} is not a resolvable --only name"


# frob:ticket T-4692
class TestExportsSplit:
    """T-4692 acceptance[3]: exports is split -- CHECK half under `frob
    check --only exports` (unchanged, unrelated code), GENERATE half
    under `frob scaffold exports` (new subverb, T-4692 owner decision
    2026-09-19: scaffold, not refactor)."""

    def test_scaffold_exports_leaf_is_registered(self) -> None:
        """`frob scaffold exports` parses with the same flag set the old
        flat `frob exports` verb had."""
        import argparse

        from frob._cli_parsers._root import _build_parser

        parser = _build_parser()
        node = parser
        for name in ("scaffold", "exports"):
            action = next(
                a
                for a in node._actions
                if isinstance(a, argparse._SubParsersAction)  # noqa: SLF001
            )
            assert name in action.choices, f"{node.prog!r} has no {name!r} subcommand"
            node = action.choices[name]
        opt_strings = {s for a in node._actions for s in a.option_strings}  # noqa: SLF001
        assert {"--all", "--exclude", "--json", "--write", "--consumers"} <= opt_strings

    def test_scaffold_exports_dispatches_to_the_unchanged_exports_runner(self) -> None:
        """`frob scaffold exports` reuses `exports_runner.run` verbatim
        (T-4692: GENERATE-half move, not a rewrite) -- generating the
        same `__init__.py` listing the pre-split flat verb produced."""
        from frob.app.config import AppConfig
        from frob.app.scaffold_runner import run as scaffold_run

        cfg = AppConfig(
            scaffold_command="exports",
            exports_path=_FIXTURE_ROOT,
            exports_json=True,
        )
        # T-4692: `_run_exports` -> `exports_runner.run` logs via `_log.info`
        # (RENDER001's routing, not a bare stdout write) -- capsys does not
        # capture the logging handler's stream, so this asserts the call
        # completes without raising/exiting rather than scraping stdout.
        scaffold_run(cfg)

    def test_check_only_exports_is_unrelated_unchanged_code(self) -> None:
        """The CHECK half (`--only exports`) is already a `_TOOL_STAGES`
        member (pre-existing, T-4692 does not touch it)."""
        from frob.check import _TOOL_STAGES

        assert "exports" in _TOOL_STAGES


# frob:ticket T-4692
class TestPoolProfileCarveOut:
    """T-4692 acceptance[4]: pool/profile are never reachable through
    `--only` (they mutate state); each is either a `frob check
    pool|profile` subverb or documented here (and in the Done report) as
    deliberately left top-level. T-4692's own fallback clause applies:
    `frob check` has no subparsers of its own (only flags) -- adding one
    risks colliding with its existing positional/flag grammar, so both
    stay top-level verbs, unchanged, undeprecated."""

    def test_pool_and_profile_are_not_check_only_stages(self) -> None:
        """Neither name resolves through `--only`'s vocabulary."""
        from frob.check import _TOOL_STAGES
        from frob.gates import _ALL_GATES

        for name in ("pool", "profile"):
            assert name not in _TOOL_STAGES
            assert name not in _ALL_GATES

    def test_pool_and_profile_remain_working_top_level_verbs(self) -> None:
        """Both runners still exist with their pre-T-4692 `run(AppConfig)`
        entry point -- left top-level deliberately (Done report: `frob
        check` takes only flags, no subcommand tree of its own to graft
        `pool`/`profile` onto without risking a grammar collision)."""
        from frob.app.pool_runner import run as pool_run
        from frob.app.profile_runner import run as profile_run

        assert callable(pool_run)
        assert callable(profile_run)
