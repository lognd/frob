"""CLI parser builders: remaining workflow subcommands (test, vet, perf,
release, mutate, stats, doctor, clean, fmt, natives, serve, sys, deploy).

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations

import argparse
from pathlib import Path


# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_test_parser(sub) -> None:
    """Register the `frob test` subcommand and its arguments."""
    # -- test ----------------------------------------------------------------
    test_p = sub.add_parser(
        "test", help="select and run tests for the touched set (or --all)"
    )
    _populate_test_args(test_p)


# frob:ticket T-1567
def _populate_test_args(test_p) -> None:
    """Add `frob test`'s arguments onto `test_p` -- shared by the
    standalone top-level parser and `frob quality test` (T-1567) so
    neither duplicates the flag list."""
    test_p.add_argument("test_path", metavar="path", nargs="?", default=".")
    test_p.add_argument("--all", dest="test_all", action="store_true")
    test_p.add_argument(
        "--fuzz",
        dest="test_fuzz",
        action="store_true",
        help="property-test fuzz-obligated pydantic models and stamp (T-0002)",
    )
    test_p.add_argument(
        "--collect",
        dest="test_collect",
        action="store_true",
        help="drop and rebuild the pytest collection cache, then exit (T-0333)",
    )
    # frob:ticket T-0322
    test_p.add_argument(
        "--wait-coverage",
        dest="test_wait_coverage",
        action="store_true",
        help=(
            "block in the foreground until the coverage stamp is fresh "
            "(single-flight across concurrent callers), then exit -- the "
            "definitive-result alternative to backgrounding `make coverage` "
            "and stalling on a notification that never arrives (T-0322)"
        ),
    )
    test_p.add_argument("--base", dest="test_base", metavar="REF")
    test_p.add_argument(
        "--lang", dest="test_lang", action="append", default=[], metavar="L"
    )
    test_p.add_argument(
        "--fallback",
        dest="test_fallback",
        choices=["package", "suite", "warn"],
    )
    test_p.add_argument("--json", dest="test_json", action="store_true")


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_vet_parser(sub) -> None:
    """Register the `frob vet` subcommand and its arguments."""
    # -- vet -----------------------------------------------------------------
    vet_p = sub.add_parser(
        "vet",
        help="dependency-vetting: lockfile allow conformance, quarantine, "
        "typosquat, lifecycle scripts, osv advisories",
    )
    vet_p.add_argument("vet_path", metavar="path", nargs="?", default=".")
    vet_p.add_argument(
        "--hook",
        dest="vet_hook",
        metavar="COMMAND",
        help="check an install-shaped shell command before it runs "
        "(Claude Code PreToolUse hook mode)",
    )
    vet_p.add_argument("--json", dest="vet_json", action="store_true")
    vet_p.add_argument(
        "--cve-mirror",
        dest="vet_cve_mirror",
        metavar="DIR",
        help="local cvelistV5 mirror root to match dependencies against "
        "(overrides [tool.frob].vet_cve_mirror in pyproject.toml, T-0147)",
    )
    vet_p.add_argument(
        "--timeout",
        dest="vet_timeout",
        type=float,
        metavar="SECONDS",
        help="per-package scan timeout in seconds; on expiry that package "
        "gets a VET-TIMEOUT verdict instead of hanging (T-0208, T-0251)",
    )
    vet_p.add_argument(
        "--jobs",
        dest="vet_jobs",
        type=int,
        metavar="N",
        help="scan packages concurrently with N workers (default 1); "
        "jobs>1 is best-effort against the shared verdict/registry caches, "
        "see docs/modules/vet.md (T-0208, T-0251)",
    )


def _add_perf_profile_parser(perf_sub) -> None:
    """Register `frob perf profile`, which runs a command/test suite under cProfile."""
    perf_profile_p = perf_sub.add_parser(
        "profile", help="run a command under cProfile, storing an artifact"
    )
    perf_profile_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_profile_p.add_argument(
        "--tests",
        dest="perf_tests",
        action="store_true",
        help="profile the [[test.runner]] python entry instead of an argv",
    )
    perf_profile_p.add_argument(
        "perf_argv",
        metavar="argv",
        nargs=argparse.REMAINDER,
        help="command to run under cProfile, after --",
    )


def _add_perf_heat_parser(perf_sub) -> None:
    """Register `frob perf heat`, which renders the stored profile as a heat-map."""
    perf_heat_p = perf_sub.add_parser(
        "heat", help="render the profiled heat-map, ranked by cumulative time"
    )
    perf_heat_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_heat_p.add_argument("--ref", dest="perf_ref", metavar="SHA")
    perf_heat_p.add_argument("--json", dest="perf_json", action="store_true")
    perf_heat_p.add_argument(
        "--smells",
        dest="perf_smells",
        action="store_true",
        help="rank hot symbols that also carry PERF findings first",
    )
    perf_heat_p.add_argument("--top", dest="perf_top", type=int, metavar="N")
    perf_heat_p.add_argument(
        "--annotate",
        dest="perf_annotate",
        metavar="FILE",
        help="print FILE with per-line hit/time gutters",
    )


# frob:ticket T-0765
def _add_perf_collect_parser(perf_sub) -> None:
    """Register `frob perf collect`, which resolves a hot-graph collector
    profile (perf script / V8 .cpuprofile / JFR print, or the T-0710
    python sampler) through `resolve_stream` and prints per-language
    deciles."""
    perf_collect_p = perf_sub.add_parser(
        "collect",
        help="resolve a perf/V8/JFR profile (or the python sampler) into "
        "per-language hot-graph deciles",
    )
    perf_collect_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_collect_p.add_argument(
        "--file",
        dest="perf_file",
        metavar="PATH",
        help="recorded profile artifact (perf script text, .cpuprofile, "
        "or a jfr print transcript)",
    )
    perf_collect_p.add_argument(
        "--format",
        dest="perf_format",
        choices=("perf-script", "v8-cpuprofile", "jfr-print"),
        help="collector format for --file (default: autodetected)",
    )
    perf_collect_p.add_argument(
        "--sampler",
        dest="perf_sampler",
        action="store_true",
        help="run the in-process python StackSampler over the test suite "
        "instead of reading --file",
    )
    perf_collect_p.add_argument(
        "--interval-s", dest="perf_interval_s", type=float, metavar="SECONDS"
    )
    perf_collect_p.add_argument(
        "--max-depth", dest="perf_max_depth", type=int, metavar="N"
    )
    perf_collect_p.add_argument("--top", dest="perf_top", type=int, metavar="N")
    perf_collect_p.add_argument("--json", dest="perf_json", action="store_true")
    perf_collect_p.add_argument(
        "perf_argv",
        metavar="argv",
        nargs=argparse.REMAINDER,
        help="pytest args for --sampler, after -- (default: -q, the whole suite)",
    )


# frob:ticket T-0712
def _add_perf_hot_parser(perf_sub) -> None:
    """Register `frob perf hot`, which renders T-0711's persisted
    sketch store, ranked by `--by`."""
    perf_hot_p = perf_sub.add_parser(
        "hot",
        help="query the hot-graph sketch store (T-0711) for the hottest sections",
    )
    perf_hot_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_hot_p.add_argument("--top", dest="perf_top", type=int, metavar="N")
    perf_hot_p.add_argument(
        "--by",
        dest="perf_by",
        choices=("p90", "p50xcount"),
        default="p50xcount",
        help="ranking key (default: p50xcount)",
    )
    perf_hot_p.add_argument("--json", dest="perf_json", action="store_true")


# frob:ticket T-0030
# frob:ticket T-0765
# frob:ticket T-0712
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_perf_parser(sub) -> None:
    """Register the `frob perf` subcommand and its arguments."""
    # -- perf ------------------------------------------------------------------
    perf_p = sub.add_parser(
        "perf", help="profile a command/test suite and inspect its heat-map"
    )
    perf_sub = perf_p.add_subparsers(dest="perf_command")
    _add_perf_profile_parser(perf_sub)
    _add_perf_heat_parser(perf_sub)
    _add_perf_collect_parser(perf_sub)
    _add_perf_hot_parser(perf_sub)


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_release_parser(sub) -> None:
    """Register the `frob release` subcommand and its arguments."""
    # -- release -------------------------------------------------------------
    release_p = sub.add_parser(
        "release", help="mechanical semver from the public-API graph (REL001)"
    )
    release_sub = release_p.add_subparsers(dest="release_command")
    _populate_release_actions(release_sub)


# frob:ticket T-1569
def _populate_release_actions(release_sub) -> None:
    """Add `frob release`'s `stamp`/`check`/`sync` actions onto
    `release_sub` -- shared by the standalone top-level parser and `frob
    ops release` (T-1569) so neither duplicates the flag list."""
    release_stamp_p = release_sub.add_parser(
        "stamp", help="record the current public API + version to .frob-release.json"
    )
    release_stamp_p.add_argument(
        "--path", dest="release_path", metavar="DIR", default="."
    )
    # frob:ticket T-1381
    release_stamp_p.add_argument(
        "--allow-unbumped",
        dest="release_allow_unbumped",
        action="store_true",
        help=(
            "T-1381 escape hatch: stamp even though the public API changed "
            "without a matching version bump. Stamping rebaselines the "
            "recorded API at the CURRENT version, so this silences REL001 "
            "while the release never happens -- use only with a reason. "
            "T-1768: requires --reason/--reason-file whenever it actually "
            "bypasses a real shortfall, recorded in force-overrides.jsonl."
        ),
    )
    # frob:ticket T-1768
    release_stamp_p.add_argument(
        "--reason", dest="release_allow_unbumped_reason", metavar="TEXT", default=None
    )
    release_stamp_p.add_argument(
        "--reason-file",
        dest="release_allow_unbumped_reason_file",
        metavar="PATH",
        type=Path,
    )
    release_check_p = release_sub.add_parser(
        "check", help="verify the version bump covers the public-API change"
    )
    release_check_p.add_argument(
        "--path", dest="release_path", metavar="DIR", default="."
    )
    # frob:ticket T-1009
    release_sync_p = release_sub.add_parser(
        "sync",
        help=(
            ".frob-release.json is the single version authority; regenerate "
            "pyproject.toml's version, uv.lock, and the CHANGELOG.md skeleton "
            "entry from it (REL002)"
        ),
    )
    release_sync_p.add_argument(
        "--path", dest="release_path", metavar="DIR", default="."
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_mutate_parser(sub) -> None:
    """Register the `frob mutate` subcommand and its arguments."""
    # -- mutate --------------------------------------------------------------
    mutate_p = sub.add_parser(
        "mutate", help="mutation testing: perturb a file, see which mutants survive"
    )
    _populate_mutate_args(mutate_p)


# frob:ticket T-1567
def _populate_mutate_args(mutate_p) -> None:
    """Add `frob mutate`'s arguments onto `mutate_p` -- shared by the
    standalone top-level parser and `frob quality mutate` (T-1567) so
    neither duplicates the flag list."""
    mutate_p.add_argument("mutate_file", metavar="file")
    mutate_p.add_argument("--path", dest="mutate_path", metavar="DIR", default=".")
    mutate_p.add_argument("--json", dest="mutate_json", action="store_true")
    mutate_p.add_argument(
        "mutate_argv",
        metavar="-- test-cmd",
        nargs=argparse.REMAINDER,
        help="test command to run per mutant (after --); default: uv run pytest -q",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_stats_parser(sub) -> None:
    """Register the `frob stats` subcommand and its arguments."""
    # -- stats ---------------------------------------------------------------
    stats_p = sub.add_parser(
        "stats", help="delivery measurement: queue health + commit cadence"
    )
    _populate_stats_args(stats_p)


# frob:ticket T-1569
def _populate_stats_args(stats_p) -> None:
    """Add `frob stats`'s arguments onto `stats_p` -- shared by the
    standalone top-level parser and `frob ops stats` (T-1569) so neither
    duplicates the flag list."""
    stats_p.add_argument("--path", dest="stats_path", metavar="DIR", default=".")
    stats_p.add_argument(
        "--days", dest="stats_days", type=int, metavar="N", help="commit window (30)"
    )
    stats_p.add_argument("--json", dest="stats_json", action="store_true")


# frob:ticket T-0319
def _add_doctor_parser(sub) -> None:
    """Register the `frob doctor` subcommand: verify+remediate missing
    native extensions (`frob_core`, `strata_core`)."""
    # -- doctor ----------------------------------------------------------------
    doctor_p = sub.add_parser(
        "doctor",
        help="verify native extensions (frob_core, strata_core) are installed",
    )
    _populate_doctor_args(doctor_p)


# frob:ticket T-1569
def _populate_doctor_args(doctor_p) -> None:
    """Add `frob doctor`'s arguments onto `doctor_p` -- shared by the
    standalone top-level parser and `frob ops doctor` (T-1569) so neither
    duplicates the flag list."""
    doctor_p.add_argument("--json", dest="doctor_json", action="store_true")
    # frob:ticket T-1360
    doctor_p.add_argument(
        "--usage",
        dest="doctor_usage",
        action="store_true",
        help="report top time sinks and footguns from the local telemetry corpus",
    )


# frob:ticket T-0457
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_clean_parser(sub) -> None:
    """Register the `frob clean` subcommand: tiered, artifact-only workspace
    cleanup (`--all`/`--deep` widen the tier, `-y`/`--yes` executes -- the
    default is a dry-run preview)."""
    # -- clean -----------------------------------------------------------------
    clean_p = sub.add_parser(
        "clean",
        help="remove build/test/cache artifacts (tiered, dry-run by default)",
    )
    _populate_clean_args(clean_p)


# frob:ticket T-1569
def _populate_clean_args(clean_p) -> None:
    """Add `frob clean`'s arguments onto `clean_p` -- shared by the
    standalone top-level parser and `frob ops clean` (T-1569) so neither
    duplicates the flag list."""
    clean_p.add_argument("clean_path", metavar="path", nargs="?", default=".")
    clean_p.add_argument(
        "--all",
        dest="clean_all",
        action="store_true",
        help="tier 2: also remove rebuildable build/test/lint artifacts",
    )
    clean_p.add_argument(
        "--deep",
        dest="clean_deep",
        action="store_true",
        help="tier 3: also remove frob's own .frob/ caches and FROBLEMS.md",
    )
    clean_p.add_argument(
        "-y",
        "--yes",
        dest="clean_yes",
        action="store_true",
        help="execute the removal (default is a dry-run preview)",
    )
    clean_p.add_argument("--json", dest="clean_json", action="store_true")


# frob:ticket T-0441
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_fmt_parser(sub) -> None:
    """Register the `frob fmt` subcommand: canonical-form wrap/unwrap of
    `frob:` directive comment lines (`--check` previews without writing)."""
    # -- fmt ---------------------------------------------------------------
    fmt_p = sub.add_parser(
        "fmt",
        help="canonicalize frob: directive comment line-wrapping (T-0441)",
    )
    fmt_p.add_argument("fmt_path", metavar="path", nargs="?", default=".")
    fmt_p.add_argument(
        "--check",
        dest="fmt_check",
        action="store_true",
        help="report non-canonical files without rewriting them",
    )
    fmt_p.add_argument("--json", dest="fmt_json", action="store_true")


# frob:ticket T-1808
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_claude_parser(sub) -> None:
    """Register the `frob claude sync [--check]` subcommand (T-1808):
    materialize this repo's git-tracked `.claude/hooks/sync-claude-
    config.py`-managed files out to `~/.claude/`, or (`--check`) report
    drift without writing."""
    # -- claude --------------------------------------------------------
    claude_p = sub.add_parser(
        "claude",
        help="sync this repo's tracked Claude config to ~/.claude/ (T-1808)",
    )
    claude_sub = claude_p.add_subparsers(dest="claude_command")
    sync_p = claude_sub.add_parser(
        "sync",
        help="materialize managed files to ~/.claude/, or --check for drift",
    )
    sync_p.add_argument(
        "--check",
        dest="claude_check",
        action="store_true",
        help="report drift without writing; exit 1 if anything differs",
    )


# frob:ticket T-0864
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_natives_parser(sub) -> None:
    """Register the `frob natives` subcommand and its `build` action
    (T-0864): frob-owned `maturin develop` per declared `[[native]]` rust
    crate, sharing one git-common-dir-keyed `CARGO_TARGET_DIR`."""
    # -- natives -----------------------------------------------------------
    natives_p = sub.add_parser(
        "natives",
        help="build declared [[native]] crates (T-0864: frob-owned "
        "maturin develop, shared CARGO_TARGET_DIR)",
    )
    natives_sub = natives_p.add_subparsers(dest="natives_command")
    _populate_natives_actions(natives_sub)


# frob:ticket T-1569
def _populate_natives_actions(natives_sub) -> None:
    """Add `frob natives`'s `build` action onto `natives_sub` -- shared by
    the standalone top-level parser and `frob ops natives` (T-1569) so
    neither duplicates the flag list."""
    natives_build_p = natives_sub.add_parser(
        "build",
        help="maturin develop --release per declared rust [[native]] crate",
    )
    natives_build_p.add_argument(
        "--path", dest="natives_path", metavar="DIR", default="."
    )


# frob:ticket T-1525
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_coverage_parser(sub) -> None:
    """Register the `frob coverage` subcommand (T-1525): user-facing CLI
    entrypoint over `frob.testing._coverage_refresh.native_coverage_refresh`
    (T-1516) -- the frob-native, cross-platform touched-set coverage
    refresh orchestration, previously only reachable as a library call
    with no verb of its own. `--full` forces a whole-suite run instead of
    the default touched-set incremental refresh."""
    # -- coverage ------------------------------------------------------
    coverage_p = sub.add_parser(
        "coverage",
        help="refresh coverage.xml / the coverage stamp via native_coverage_refresh "
        "(T-1516/T-1525) -- touched-set incremental by default",
    )
    coverage_p.add_argument("coverage_path", metavar="path", nargs="?", default=".")
    coverage_p.add_argument(
        "--full",
        dest="coverage_full",
        action="store_true",
        help="run the whole suite under coverage instead of the touched-set "
        "incremental refresh",
    )
    # frob:ticket T-1572
    coverage_p.add_argument(
        "--base",
        dest="coverage_base",
        metavar="REF",
        default=None,
        help="git ref the touched-set incremental refresh diffs against "
        "(default: HEAD) -- the old make coverage-fast BASE=<ref> shell "
        "recipe's equivalent; has no effect with --full, which always "
        "runs the whole suite regardless of any touched-set base",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_serve_parser(sub) -> None:
    """Register the `frob serve` subcommand and its arguments."""
    # -- serve ---------------------------------------------------------------
    serve_p = sub.add_parser(
        "serve",
        help="MCP stdio adapter exposing frob's enforcement queries as tools",
    )
    serve_p.add_argument("serve_path", metavar="path", nargs="?", default=".")


# frob:ticket T-0084
# frob:ticket T-0085
# frob:ticket T-0086
# frob:ticket T-1870
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_sys_parser(sub) -> None:
    """Register the `frob sys` subcommand group: `plan` (T-0084), `doc`
    (T-0085), `export` (T-0086), `trace` (T-1480), and `threats` (T-1925)
    today; `capacity` (docs/strata/roadmap.md "CLI surface (target)") is a
    later roadmap-phase-5 sibling -- extend this parser with one more
    `sys_sub.add_parser` per verb as they land, never replace it. `audit`
    (T-0115) is the checking counterpart to `doc`; `check` was deliberately
    dropped from the target list (T-1926) as a duplicate of `audit`."""
    # -- sys -------------------------------------------------------------------
    # frob:ticket T-0167
    # frob:ticket T-1925
    sys_p = sub.add_parser(
        "sys",
        help="strata design-model applications (plan, doc, export, ...)",
        epilog=_SYS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sys_sub = sys_p.add_subparsers(dest="sys_command")
    _add_sys_plan_and_export_parsers(sys_sub)
    _add_sys_doc_and_audit_parsers(sys_sub)
    _add_sys_trace_parser(sys_sub)
    _add_sys_threats_parser(sys_sub)


_SYS_EPILOG = (
    "examples:\n"
    "  frob sys plan                    plan a ticket tree (dry-run)\n"
    "  frob sys plan --apply             write the planned tickets\n"
    "  frob sys plan /path/to/repo      plan a different repo root\n"
    "  frob sys doc                     render the threat-catalog audit matrix\n"
    "  frob sys audit                   check per-family exhaustiveness\n"
    "  frob sys export --format seccomp design/frob.strata\n"
    "\n"
    "convention: for plan/doc/audit, <path> (default '.') is the REPO\n"
    "ROOT -- the command appends the configured design dir itself\n"
    "(default 'design/', or [strata].design_dir in frob.toml) and reads\n"
    "every *.strata file under it. export is the exception: it takes a\n"
    "path to ONE *.strata file (default 'design/frob.strata'), not a\n"
    "root or a directory."
)


def _add_sys_plan_and_export_parsers(sys_sub) -> None:
    """Register `frob sys plan` and `frob sys export`."""
    sys_plan_p = sys_sub.add_parser(
        "plan",
        help="compile the obligation frontier into a ticket tree (idempotent)",
    )
    sys_plan_p.add_argument("sys_path", metavar="path", nargs="?", default=".")
    sys_plan_p.add_argument(
        "--apply",
        dest="sys_apply",
        action="store_true",
        help="write the planned tickets (default: dry-run, print the tree)",
    )
    sys_export_p = sys_sub.add_parser(
        "export", help="render a k8s/seccomp/iam config skeleton from a design"
    )
    sys_export_p.add_argument(
        "--format",
        dest="sys_export_format",
        choices=["k8s", "seccomp", "iam"],
        required=True,
    )
    sys_export_p.add_argument(
        "sys_export_path",
        metavar="design.strata",
        nargs="?",
        help="path to a .strata design file (default: design/frob.strata)",
    )


def _add_sys_doc_and_audit_parsers(sys_sub) -> None:
    """Register `frob sys doc` and `frob sys audit`."""
    sys_doc_p = sys_sub.add_parser(
        "doc",
        help="render the per-family threat-catalog audit matrix (T-0085)",
    )
    sys_doc_p.add_argument("sys_path", metavar="path", nargs="?", default=".")
    sys_doc_p.add_argument(
        "--view",
        dest="sys_view",
        default="owasp-top-10",
        help="baseline view to render the matrix for (default: owasp-top-10)",
    )

    sys_audit_p = sys_sub.add_parser(
        "audit",
        help="check the full per-family exhaustiveness conjunction; "
        "nonzero exit + named gaps on any failure (T-0115)",
    )
    sys_audit_p.add_argument("sys_path", metavar="path", nargs="?", default=".")


# frob:ticket T-1480
def _add_sys_trace_parser(sys_sub) -> None:
    """Register `frob sys trace <from> [to]` (T-1480): the influence-closure
    witness-path CLI wrapper over `frob.strata.FactBase.reachable`, the
    roadmap-phase-5 `trace` verb (docs/strata/roadmap.md "CLI surface
    (target)")."""
    sys_trace_p = sys_sub.add_parser(
        "trace",
        help="print the influence-closure witness path from one node "
        "(T-1480)",
    )
    sys_trace_p.add_argument("sys_path", metavar="path", nargs="?", default=".")
    sys_trace_p.add_argument("sys_trace_from", metavar="from")
    sys_trace_p.add_argument("sys_trace_to", metavar="to", nargs="?", default=None)
    sys_trace_p.add_argument(
        "--through-barriers",
        dest="sys_trace_through_barriers",
        action="store_true",
        help="ignore declared trust/label boundaries (positive reach claims; "
        "default: stop taint at a boundary, the endorsement semantics)",
    )


# frob:ticket T-1925
def _add_sys_threats_parser(sys_sub) -> None:
    """Register `frob sys threats [boundary]` (T-1925): the roadmap-phase-5
    `threats` verb, a thin wrapper over `frob.strata._threat.
    threat_violations_for_boundary` -- with no `boundary` positional it
    prints the full unfiltered `evaluate_threats` violation set (same
    THREAT001-005 conjunction `sys audit` runs), matching `sys trace`'s
    own "no destination = whole closure" default shape."""
    sys_threats_p = sys_sub.add_parser(
        "threats",
        help="print THREAT001-005 violations, optionally scoped to one "
        "boundary's protected zone (T-1925)",
    )
    sys_threats_p.add_argument("sys_path", metavar="path", nargs="?", default=".")
    sys_threats_p.add_argument(
        "sys_threats_boundary", metavar="boundary", nargs="?", default=None
    )


# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_deploy_parser(sub) -> None:
    """Register the `frob deploy` subcommand group: `generate` (T-0257)
    and `audit` (T-0259) -- extend with one more `deploy_sub.add_parser`
    per verb as later deploy-epoch (T-0254) tickets add them, never
    replace this dispatch."""
    # -- deploy ------------------------------------------------------------
    deploy_p = sub.add_parser(
        "deploy",
        help="compile std.host manifests into install/status/uninstall bash",
        epilog=_DEPLOY_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    deploy_sub = deploy_p.add_subparsers(dest="deploy_command")
    _add_deploy_generate_parser(deploy_sub)
    _add_deploy_audit_parser(deploy_sub)


_DEPLOY_EPILOG = (
    "examples:\n"
    "  frob deploy generate                 write deploy/*.sh from the design\n"
    "  frob deploy generate --check          verify committed scripts are current\n"
    "  frob deploy generate /path/to/repo   generate for a different repo root\n"
    "  frob deploy audit --vm my-vm --ssh-host 10.0.2.15 --ssh-key ~/.ssh/id_rsa\n"
    "                                        empirically prove artifact-free\n"
    "                                        install/uninstall against a live\n"
    "                                        VirtualBox guest (NOT run by\n"
    "                                        `frob check`; needs VBoxManage)\n"
    "\n"
    "convention: <path> (default '.') is the REPO ROOT -- the command\n"
    "appends the configured design dir itself (default 'design/', or\n"
    "[strata].design_dir in frob.toml) and reads every *.strata file\n"
    "under it, compiling std.host HostManifest facts (T-0255) into\n"
    "deploy/install.sh, deploy/status.sh, deploy/uninstall.sh."
)


def _add_deploy_generate_parser(deploy_sub) -> None:
    """Register `frob deploy generate`."""
    deploy_generate_p = deploy_sub.add_parser(
        "generate",
        help="write deploy/install.sh, deploy/status.sh, deploy/uninstall.sh",
    )
    deploy_generate_p.add_argument(
        "deploy_path", metavar="path", nargs="?", default="."
    )
    deploy_generate_p.add_argument(
        "--out-dir",
        dest="deploy_out_dir",
        default=None,
        help="directory to write the generated scripts into (default: deploy/)",
    )
    deploy_generate_p.add_argument(
        "--check",
        dest="deploy_check",
        action="store_true",
        help="verify committed scripts already match regeneration; no writes, "
        "exit 1 on any mismatch",
    )


def _add_deploy_audit_parser(deploy_sub) -> None:
    """Register `frob deploy audit`."""
    deploy_audit_p = deploy_sub.add_parser(
        "audit",
        help="VirtualBox snapshot-diff harness proving artifact-free "
        "install/uninstall (T-0259, expensive -- NOT run by `frob check`)",
    )
    deploy_audit_p.add_argument("deploy_path", metavar="path", nargs="?", default=".")
    deploy_audit_p.add_argument(
        "--vm", dest="deploy_vm", required=True, help="VirtualBox guest name"
    )
    _add_deploy_audit_ssh_and_output_args(deploy_audit_p)


def _add_deploy_audit_ssh_and_output_args(deploy_audit_p) -> None:
    """Register `frob deploy audit`'s ssh/snapshot/output args."""
    deploy_audit_p.add_argument(
        "--ssh-host", dest="deploy_ssh_host", required=True, help="guest ssh host"
    )
    deploy_audit_p.add_argument(
        "--ssh-user",
        dest="deploy_ssh_user",
        default="root",
        help="guest ssh user (default: root)",
    )
    deploy_audit_p.add_argument(
        "--ssh-key", dest="deploy_ssh_key", required=True, help="ssh private key path"
    )
    deploy_audit_p.add_argument(
        "--base-snapshot",
        dest="deploy_base_snapshot",
        default="base",
        help="snapshot to restore before CHECK C0 (default: base)",
    )
    deploy_audit_p.add_argument(
        "--output",
        dest="deploy_audit_output",
        default=None,
        help="attestation JSON output path (default: deploy-audit-attestation.json)",
    )
