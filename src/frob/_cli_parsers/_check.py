"""CLI parser builders: `frob check`'s stage-skip/scope/selection/delta
argument groups and the top-level check subparser itself.

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

# frob:ticket T-5134
from __future__ import annotations

import argparse

#: T-4524: the stage vocabulary every legacy `--skip-<stage>` flag and the
#: unified `--skip STAGE[,STAGE]` flag both resolve to, mapping each
#: hyphenated stage name onto the exact `AppConfig.check_skip_*` namespace
#: attribute the pre-existing per-flag `dest=` already used -- so setting
#: that attribute from the new flag reaches every downstream reader
#: (`check_runner.py`'s `cfg.check_skip_*` field reads) unchanged. Mirrors
#: `--only`'s own stage vocabulary (`frob.check._TOOL_STAGES` plus gate
#: names) for the eight Python-toolchain stages it shares, plus the
#: multi-language tool stages `--only` does not name (T-4524's ticket body:
#: "same vocabulary as --only ... --only already defines the stage
#: vocabulary; --skip is its mirror").
_SKIP_STAGE_FIELDS: dict[str, str] = {
    "ruff": "check_skip_ruff",
    "ruff-check": "check_skip_ruff_check",
    "ruff-format": "check_skip_ruff_format",
    "ty": "check_skip_ty",
    "arch": "check_skip_arch",
    "cycle": "check_skip_cycle",
    "dup": "check_skip_dup",
    "bind": "check_skip_bind",
    "exports": "check_skip_exports",
    "gates": "check_skip_gates",
    "tests": "check_skip_tests",
    "build": "check_skip_build",
    "clang-tidy": "check_skip_clang_tidy",
    "clang-format": "check_skip_clang_format",
    "cargo-check": "check_skip_cargo_check",
    "clippy": "check_skip_clippy",
    "fmt": "check_skip_fmt",
    "tsc": "check_skip_tsc",
    "eslint": "check_skip_eslint",
    "prettier": "check_skip_prettier",
}

#: DEPRECATED-help-string marker `_HideDeprecatedFormatter` below matches
#: on -- kept as one constant so the tag and the formatter that reads it
#: cannot silently drift apart.
_DEPRECATED_TAG = "DEPRECATED"


def _deprecated_skip_help(stage: str) -> str:
    """One-line help string for a legacy `--skip-<stage>` flag (T-4524):
    starts with `_DEPRECATED_TAG` (matched by `_HideDeprecatedFormatter` to
    drop it from the rendered `--help` block) and names the replacement."""
    return f"{_DEPRECATED_TAG}: use --skip {stage} instead"


class _HideDeprecatedFormatter(argparse.HelpFormatter):
    """`frob check --help`'s formatter (T-4524): renders every action
    exactly like the stock formatter EXCEPT one whose help string starts
    with `_DEPRECATED_TAG` -- those are omitted from the printed block
    entirely (the 20 legacy `--skip-<stage>` flags), while staying fully
    registered, parseable, and still carrying their real (DEPRECATED-
    prefixed) help string on `check_p._actions` for anything that
    introspects the parser directly instead of rendering it."""

    def add_argument(self, action) -> None:
        """Skip rendering `action` when its help text is DEPRECATED-tagged."""
        help_text = getattr(action, "help", None)
        if isinstance(help_text, str) and help_text.startswith(_DEPRECATED_TAG):
            return
        super().add_argument(action)

    def add_usage(self, usage, actions, groups, prefix=None) -> None:
        """Drop DEPRECATED-tagged actions from the `usage:` line too --
        `add_argument` above only governs the options body, and argparse
        builds the usage summary from the raw action list independently."""
        visible = [
            a
            for a in actions
            if not (
                isinstance(getattr(a, "help", None), str)
                and a.help.startswith(_DEPRECATED_TAG)
            )
        ]
        super().add_usage(usage, visible, groups, prefix)


class _SkipStageAction(argparse.Action):
    """argparse action for the unified `--skip STAGE[,STAGE...]` flag
    (repeatable, comma-splittable, T-4524): splits `values` on commas and,
    for each stage, sets the SAME `check_skip_<stage>` namespace attribute
    the matching legacy `--skip-<stage>` flag already sets -- so nothing
    downstream (`check_runner.py`'s existing `cfg.check_skip_*` reads)
    changes. Refuses an unrecognized stage name via `parser.error` (exit
    2, the argparse-standard usage-error code), naming the bad stage and
    the full known vocabulary."""

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        """Apply one `--skip` occurrence's comma-split stage list."""
        stages: list[str] = list(getattr(namespace, self.dest, None) or [])
        for raw in str(values).split(","):
            stage = raw.strip()
            if not stage:
                continue
            field = _SKIP_STAGE_FIELDS.get(stage)
            if field is None:
                parser.error(
                    f"--skip: unknown stage {stage!r} (known stages: "
                    f"{', '.join(sorted(_SKIP_STAGE_FIELDS))})"
                )
                return
            setattr(namespace, field, True)
            stages.append(stage)
        setattr(namespace, self.dest, stages)


def _add_check_skip_args_python(check_p) -> None:
    """Register `frob check`'s Python-toolchain stage-skip flags.

    T-2320: `--skip-ruff` used to bundle ruff-check and ruff-format under
    one flag with no way to skip them independently. It stays as a
    back-compat alias (skips both, unchanged); `--skip-ruff-check`/
    `--skip-ruff-format` are the new split flags for skipping just one.

    T-4524: every flag here is now a DEPRECATED alias for `--skip
    <stage>` (kept working for one release, hidden from the main --help
    block by `_HideDeprecatedFormatter`) -- see `_add_check_skip_unified_
    arg` for the replacement."""
    check_p.add_argument(
        "--skip-ruff",
        dest="check_skip_ruff",
        action="store_true",
        help=_deprecated_skip_help("ruff"),
    )
    check_p.add_argument(
        "--skip-ruff-check",
        dest="check_skip_ruff_check",
        action="store_true",
        help=_deprecated_skip_help("ruff-check"),
    )
    check_p.add_argument(
        "--skip-ruff-format",
        dest="check_skip_ruff_format",
        action="store_true",
        help=_deprecated_skip_help("ruff-format"),
    )
    check_p.add_argument(
        "--skip-ty",
        dest="check_skip_ty",
        action="store_true",
        help=_deprecated_skip_help("ty"),
    )
    check_p.add_argument(
        "--skip-arch",
        dest="check_skip_arch",
        action="store_true",
        help=_deprecated_skip_help("arch"),
    )
    check_p.add_argument(
        "--skip-cycle",
        dest="check_skip_cycle",
        action="store_true",
        help=_deprecated_skip_help("cycle"),
    )
    check_p.add_argument(
        "--skip-dup",
        dest="check_skip_dup",
        action="store_true",
        help=_deprecated_skip_help("dup"),
    )
    check_p.add_argument(
        "--skip-bind",
        dest="check_skip_bind",
        action="store_true",
        help=_deprecated_skip_help("bind"),
    )
    check_p.add_argument(
        "--skip-exports",
        dest="check_skip_exports",
        action="store_true",
        help=_deprecated_skip_help("exports"),
    )
    check_p.add_argument(
        "--skip-gates",
        dest="check_skip_gates",
        action="store_true",
        help=_deprecated_skip_help("gates"),
    )


def _add_check_skip_args_cpp(check_p) -> None:
    """Register `frob check`'s C++-toolchain stage-skip flags (the three
    `--skip-*` ones are DEPRECATED aliases for `--skip <stage>`, T-4524)."""
    check_p.add_argument("--build-dir", dest="check_build_dir", metavar="DIR")
    check_p.add_argument(
        "--skip-build",
        dest="check_skip_build",
        action="store_true",
        help=_deprecated_skip_help("build"),
    )
    check_p.add_argument(
        "--skip-clang-tidy",
        dest="check_skip_clang_tidy",
        action="store_true",
        help=_deprecated_skip_help("clang-tidy"),
    )
    check_p.add_argument(
        "--skip-clang-format",
        dest="check_skip_clang_format",
        action="store_true",
        help=_deprecated_skip_help("clang-format"),
    )


def _add_check_skip_args_rust_ts(check_p) -> None:
    """Register `frob check`'s Rust- and TypeScript-toolchain stage-skip
    flags (all DEPRECATED aliases for `--skip <stage>`, T-4524)."""
    check_p.add_argument(
        "--skip-cargo-check",
        dest="check_skip_cargo_check",
        action="store_true",
        help=_deprecated_skip_help("cargo-check"),
    )
    check_p.add_argument(
        "--skip-clippy",
        dest="check_skip_clippy",
        action="store_true",
        help=_deprecated_skip_help("clippy"),
    )
    check_p.add_argument(
        "--skip-fmt",
        dest="check_skip_fmt",
        action="store_true",
        help=_deprecated_skip_help("fmt"),
    )
    check_p.add_argument(
        "--skip-tsc",
        dest="check_skip_tsc",
        action="store_true",
        help=_deprecated_skip_help("tsc"),
    )
    check_p.add_argument(
        "--skip-eslint",
        dest="check_skip_eslint",
        action="store_true",
        help=_deprecated_skip_help("eslint"),
    )
    check_p.add_argument(
        "--skip-prettier",
        dest="check_skip_prettier",
        action="store_true",
        help=_deprecated_skip_help("prettier"),
    )


# frob:ticket T-0030
def _add_check_skip_args(check_p) -> None:
    """Register `frob check`'s per-language stage-skip flags (T-4524:
    every one of these is now a DEPRECATED alias; see
    `_add_check_skip_unified_arg` for the current `--skip STAGE` flag)."""
    _add_check_skip_args_python(check_p)
    _add_check_skip_args_cpp(check_p)
    _add_check_skip_args_rust_ts(check_p)


# frob:ticket T-4524
def _add_check_skip_unified_arg(check_p) -> None:
    """Register `frob check`'s unified `--skip STAGE[,STAGE]` flag
    (T-4524): repeatable and comma-splittable, mirroring `--only`
    (`_add_check_selection_args` below), and mapped onto the exact same
    `check_skip_<stage>` attributes the 20 legacy per-stage flags already
    set (`_SkipStageAction`) -- so it is a pure CLI-surface reduction,
    nothing downstream changes."""
    check_p.add_argument(
        "--skip",
        dest="check_skip_stages",
        metavar="STAGE",
        action=_SkipStageAction,
        default=[],
        help=(
            "skip a check stage (repeatable; comma-splittable, e.g. "
            "`--skip ruff,ty`) -- same stage vocabulary as --only, plus "
            "the multi-language tool stages --only does not name "
            "(build/clang-tidy/clang-format/cargo-check/clippy/fmt/tsc/"
            "eslint/prettier/tests); `--skip ruff` skips both the "
            "ruff-check and ruff-format stages, same as the old bundled "
            "ruff-skip flag did (replaces the 20 per-stage flags)"
        ),
    )


def _add_check_scope_args(check_p) -> None:
    """Register `frob check`'s path/type/valgrind/skip-tests scoping args."""
    check_p.add_argument("check_path", metavar="path", nargs="?", default=".")
    check_p.add_argument(
        "--type",
        dest="check_type",
        choices=["python", "cpp", "rust", "typescript"],
        help="project type (default: auto-detect)",
    )
    check_p.add_argument(
        "--valgrind",
        dest="check_valgrind",
        action="store_true",
        help="run valgrind memcheck on test binary",
    )
    check_p.add_argument(
        "--skip-tests",
        dest="check_skip_tests",
        action="store_true",
        help=_deprecated_skip_help("tests"),
    )


# frob:ticket T-3995
def _add_check_selection_args(check_p) -> None:
    """Register `frob check`'s ticket/base/only/stamp-coverage/baseline/delta args."""
    check_p.add_argument("--json", dest="check_json", action="store_true")
    check_p.add_argument("--ticket", dest="check_ticket", metavar="ID")
    check_p.add_argument("--base", dest="check_base", metavar="REF")
    # frob:ticket T-1260
    check_p.add_argument(
        "--fix",
        dest="check_fix",
        action="store_true",
        help=(
            "apply every registered Tier-A deterministic auto-fix "
            "(frob.gates._fix_engine.apply_tier_a_fixes) then re-run the "
            "union of affected gates once in this same invocation, "
            "reporting fixed/rolled-back/fix-its; never writes a waiver, "
            "never touches frob.toml or ratchet state (design, "
            "docs/design/check-fix-engine.md)"
        ),
    )
    # frob:ticket T-3326
    check_p.add_argument(
        "--fix-all",
        dest="check_fix_all",
        action="store_true",
        help=(
            "required alongside a bare `--fix` (no --ticket) to apply "
            "Tier-A fixes repo-wide -- without it, an unscoped `--fix` "
            "REFUSES rather than silently rewriting every file its "
            "handlers find (a killed unscoped --fix once touched "
            "~15 unrelated files before an agent noticed and reverted by "
            "hand). `--ticket <id> --fix` never needs this: it is already "
            "scoped to that ticket's declared files and always "
            "runs. A no-op when --ticket is also given."
        ),
    )
    # frob:ticket T-2320
    check_p.add_argument(
        "--fix-ruff",
        dest="check_ruff_fix",
        action="store_true",
        help=(
            "run a genuine `ruff check --fix` + `ruff format` WRITE pass "
            "(src/frob/check/_python.py::run_ruff_autofix) and exit -- "
            "distinct from --fix's narrow Tier-A/B/C deterministic "
            "fixers, which never run a general ruff autofix"
        ),
    )
    check_p.add_argument(
        "--only",
        dest="check_only",
        metavar="STAGE",
        action="append",
        default=[],
        help=(
            "run only these stages (repeatable); includes 'gates'. "
            "also excludes the three opt-in tail checks that otherwise run "
            "unconditionally on every full check -- deploy-drift, "
            "deploy-conformance, claude-config-drift -- since none of them "
            "has a --only name of its own"
        ),
    )
    # frob:ticket T-4413
    # frob:ticket T-4692
    check_p.add_argument(
        "--list-stages",
        dest="check_list_stages",
        action="store_true",
        help=(
            "print every folded check stage (dup arch cycle bind narrative "
            "exports), one per line, and exit -- each name is accepted by "
            "--only; distinct from --only list, which prints stage-GROUP "
            "aliases (lint/static/...) instead"
        ),
    )
    check_p.add_argument(
        "--files",
        dest="check_files",
        metavar="PATH",
        action="append",
        default=None,
        help=(
            "scope check compute to these files/dirs (repeatable) instead "
            "of the whole tree -- ruff/ty receive this list directly; "
            "arch/cycle/dup/exports and repo-wide gates (ledger, milestone, "
            "release, cross-ticket leakage, sys/selfaudit) still run "
            "unscoped (REPO_WIDE_STAGES/REPO_WIDE_GATES). Omit "
            "(default None) for today's unscoped behavior, byte-for-byte."
        ),
    )
    check_p.add_argument(
        "--stamp-coverage",
        dest="check_stamp_coverage",
        action="store_true",
        help="record coverage.xml as the current coverage stamp and exit",
    )
    # frob:ticket T-1535
    check_p.add_argument(
        "--land-parity",
        dest="check_land_parity",
        action="store_true",
        help=(
            "run the exact unscoped, cache-bypassed error evaluation "
            "`frob ticket land`'s pre-commit/post-land sweeps run, against "
            "the current tree, and exit -- converge in the worktree before "
            "the coordinator ever lands"
        ),
    )
    # frob:ticket T-1764
    check_p.add_argument(
        "--census",
        dest="check_census",
        action="store_true",
        help=(
            "print the per-rule waive-rate table (fired, waived, "
            "waive-rate, dead-waiver count) from a full unscoped gate run "
            "and exit -- classifies each rule corpus-wide vs diff-scoped "
            "first (frob.gates._waive._WAIVE004_STRUCTURALLY_UNVERIFIABLE_"
            "RULES) and reports no rate at all for a diff-scoped rule, "
            "rather than a misleading clean-tree one"
        ),
    )
    _add_check_delta_and_verbose_args(check_p)


def _add_check_delta_and_verbose_args(check_p) -> None:
    """Register `frob check`'s `--stamp-baseline`/`--delta`/`--budget`/`-v` args."""
    check_p.add_argument(
        "--stamp-baseline",
        dest="check_stamp_baseline",
        action="store_true",
        help="record the current gate violations as the delta baseline and exit",
    )
    # frob:ticket T-1004
    check_p.add_argument(
        "--budget",
        dest="check_budget",
        type=int,
        metavar="SECONDS",
        help=(
            "self-select and run as many --only stage groups as fit in "
            "SECONDS (measured timings, persisted resume state for the "
            "remainder) instead of hand-running the chunked --only loop"
        ),
    )
    check_p.add_argument(
        "--delta",
        dest="check_delta",
        action="store_true",
        help=(
            "gates stage reports only violations new since the stamped "
            "baseline (see --stamp-baseline); a missing/stale baseline "
            "degrades to the full set with a warning"
        ),
    )
    # frob:ticket T-1445
    check_p.add_argument(
        "--no-cache",
        dest="check_no_cache",
        action="store_true",
        help=(
            "bypass the gate-result cache (.frob/gate-cache.db) and force "
            "every cacheable gate to recompute in full, same as the "
            "FROB_NO_GATE_CACHE=1 env var"
        ),
    )
    check_p.add_argument(
        "-v",
        "--verbose",
        dest="check_verbose",
        action="count",
        default=0,
        help=(
            "-v restores per-file/per-stage INFO log lines; -vv adds "
            "per-symbol DEBUG detail (default is summary+violations "
            "only)"
        ),
    )


# frob:ticket T-0030
def _add_check_parser(sub) -> None:
    """Register the `frob check` subcommand and its arguments.

    T-4524: `formatter_class=_HideDeprecatedFormatter` drops the 20 legacy
    `--skip-<stage>` flags from the rendered `--help` block while they
    stay fully registered and working."""
    # -- check ---------------------------------------------------------------
    check_p = sub.add_parser(
        "check",
        help=(
            "aggregate quality gate: ruff, ty, frob cycle/dup/arch/bind/exports; "
            "errors first, easy to hand to subagents"
        ),
        formatter_class=_HideDeprecatedFormatter,
    )
    _add_check_scope_args(check_p)
    _add_check_skip_args(check_p)
    _add_check_skip_unified_arg(check_p)
    _add_check_selection_args(check_p)
