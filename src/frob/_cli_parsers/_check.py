# frob:waive INV006 reason="T-1076 split of __main__.py's original T-0585 waiver: \
# this module's help/docstring text carries incidental exclusivity-flavored wording \
# (argparse help strings, scope-cut prose) inherited verbatim from __main__.py, not a \
# new normative contract -- disposed as the same calibration batch, not claim-by-claim"
"""CLI parser builders: `frob check`'s stage-skip/scope/selection/delta
argument groups and the top-level check subparser itself.

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations


def _add_check_skip_args_python(check_p) -> None:
    """Register `frob check`'s Python-toolchain stage-skip flags."""
    check_p.add_argument("--skip-ruff", dest="check_skip_ruff", action="store_true")
    check_p.add_argument("--skip-ty", dest="check_skip_ty", action="store_true")
    check_p.add_argument("--skip-arch", dest="check_skip_arch", action="store_true")
    check_p.add_argument("--skip-cycle", dest="check_skip_cycle", action="store_true")
    check_p.add_argument("--skip-dup", dest="check_skip_dup", action="store_true")
    check_p.add_argument("--skip-bind", dest="check_skip_bind", action="store_true")
    check_p.add_argument(
        "--skip-exports", dest="check_skip_exports", action="store_true"
    )
    check_p.add_argument("--skip-gates", dest="check_skip_gates", action="store_true")


def _add_check_skip_args_cpp(check_p) -> None:
    """Register `frob check`'s C++-toolchain stage-skip flags."""
    check_p.add_argument("--build-dir", dest="check_build_dir", metavar="DIR")
    check_p.add_argument("--skip-build", dest="check_skip_build", action="store_true")
    check_p.add_argument(
        "--skip-clang-tidy", dest="check_skip_clang_tidy", action="store_true"
    )
    check_p.add_argument(
        "--skip-clang-format", dest="check_skip_clang_format", action="store_true"
    )


def _add_check_skip_args_rust_ts(check_p) -> None:
    """Register `frob check`'s Rust- and TypeScript-toolchain stage-skip flags."""
    check_p.add_argument(
        "--skip-cargo-check", dest="check_skip_cargo_check", action="store_true"
    )
    check_p.add_argument("--skip-clippy", dest="check_skip_clippy", action="store_true")
    check_p.add_argument("--skip-fmt", dest="check_skip_fmt", action="store_true")
    check_p.add_argument("--skip-tsc", dest="check_skip_tsc", action="store_true")
    check_p.add_argument("--skip-eslint", dest="check_skip_eslint", action="store_true")
    check_p.add_argument(
        "--skip-prettier", dest="check_skip_prettier", action="store_true"
    )


# frob:ticket T-0030
def _add_check_skip_args(check_p) -> None:
    """Register `frob check`'s per-language stage-skip flags."""
    _add_check_skip_args_python(check_p)
    _add_check_skip_args_cpp(check_p)
    _add_check_skip_args_rust_ts(check_p)


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
    check_p.add_argument("--skip-tests", dest="check_skip_tests", action="store_true")


def _add_check_selection_args(check_p) -> None:
    """Register `frob check`'s ticket/base/only/stamp-coverage/baseline/delta args."""
    check_p.add_argument("--json", dest="check_json", action="store_true")
    check_p.add_argument("--ticket", dest="check_ticket", metavar="ID")
    check_p.add_argument("--base", dest="check_base", metavar="REF")
    check_p.add_argument(
        "--only",
        dest="check_only",
        metavar="STAGE",
        action="append",
        default=[],
        help="run only these stages (repeatable); includes 'gates'",
    )
    check_p.add_argument(
        "--stamp-coverage",
        dest="check_stamp_coverage",
        action="store_true",
        help="record coverage.xml as the current coverage stamp and exit",
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
    check_p.add_argument(
        "-v",
        "--verbose",
        dest="check_verbose",
        action="count",
        default=0,
        help=(
            "-v restores per-file/per-stage INFO log lines; -vv adds "
            "per-symbol DEBUG detail (T-0202; default is summary+violations "
            "only)"
        ),
    )


# frob:ticket T-0030
def _add_check_parser(sub) -> None:
    """Register the `frob check` subcommand and its arguments."""
    # -- check ---------------------------------------------------------------
    check_p = sub.add_parser(
        "check",
        help=(
            "aggregate quality gate: ruff, ty, frob cycle/dup/arch/bind/exports; "
            "errors first, easy to hand to subagents"
        ),
    )
    _add_check_scope_args(check_p)
    _add_check_skip_args(check_p)
    _add_check_selection_args(check_p)
