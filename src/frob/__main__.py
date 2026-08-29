# frob:ticket T-3059
from __future__ import annotations

import argparse
import os
from pathlib import Path

# T-3059: parser construction lives in frob._cli_parsers._root now; these
# names are re-imported (not just `_build_parser`, the only one this module
# itself calls) so pre-existing call sites that reach into `frob.__main__`
# for them -- `from frob.__main__ import _build_parser` across ~20 test
# modules, `frob.toml`'s `parser = "frob.__main__:_build_parser"` entrypoint,
# `tests/unit/test_main_entry.py`'s `main_module._VERB_GROUP_NAMES` -- keep
# working against this module's surface unchanged.
from frob._cli_parsers import (
    _add_ack_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_agent_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_arch_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_bind_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_check_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_claude_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_clean_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_coverage_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_cycle_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_debt_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_deploy_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_deprecated_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_design_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_docs_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_doctor_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_dup_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_explore_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_exports_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_fleet_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_fmt_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_format_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_gitlog_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_graph_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_map_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_mutate_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_natives_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_ops_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_outline_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_parse_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_perf_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_pool_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_profile_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_quality_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_registry_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_release_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_scaffold_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_serve_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_stats_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_status_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_sync_skills_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_sys_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_test_parser,  # noqa: F401 -- re-exported: tests/test_gates.py
    _add_ticket_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_verify_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_vet_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_worktree_parser,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_xref_parser,  # noqa: F401 -- re-exported: prior __main__ surface
)
from frob._cli_parsers._root import (
    _VERB_GROUP_NAMES,  # noqa: F401 -- re-exported: tests/unit/test_main_entry.py
    _add_analysis_subparsers,  # noqa: F401 -- re-exported: prior __main__ surface
    _add_workflow_subparsers,  # noqa: F401 -- re-exported: prior __main__ surface
    _build_parser,
    _closest,  # noqa: F401 -- re-exported: prior __main__ surface
    _collect_option_strings,  # noqa: F401 -- re-exported: prior __main__ surface
    _did_you_mean,  # noqa: F401 -- re-exported: prior __main__ surface
    _frob_version,  # noqa: F401 -- re-exported: prior __main__ surface
    _GroupedHelpFormatter,  # noqa: F401 -- re-exported: prior __main__ surface
    _SuggestingArgumentParser,  # noqa: F401 -- re-exported: prior __main__ surface
)
from frob.app import App, AppConfig
from frob.app._version_guard import binary_fingerprint_warning
from frob.app.config import stale_binary_warning, stale_install_warning
from frob.doctor import native_degrade_warning
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#entry-point
# frob:ticket T-0355
# frob:ticket T-0358
# frob:ticket T-2443
# frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_keyboard_interrupt_prints_clean_message_and_exits_130  # noqa: E501
# frob:tests \
# tests/unit/test_main_entry.py::TestMainSigint.test_normal_dispatch_is_unaffected
# frob:tests tests/unit/test_main_entry.py::TestMainInstallsSigtermReaper.test_main_installs_the_reaper_before_dispatch  # noqa: E501
def main() -> None:
    """CLI entry point: parses argv and dispatches to `App`, or straight to
    `frob bind` (T-0355: SIGINT during a long-running command -- e.g. a
    synchronous pre-work sweep on a slow mount -- used to fall through to a
    bare `KeyboardInterrupt` traceback; that's noise for a deliberate Ctrl-C,
    not a crash, so it is caught here and reported as a clean one-line
    message with the conventional 128+SIGINT exit code instead).

    T-2443: `install_sigterm_reaper` runs FIRST, before any dispatch --
    every real invocation of this CLI is a fresh process, so this is the
    one place that reliably runs once per invocation regardless of which
    subcommand follows. See `frob.process._reap`'s module docstring for the
    leaked-forkserver defect this closes (a `frob check` killed by this
    fleet's routine `timeout 540 ...` wrapper used to leave its process-pool
    workers, and therefore the forkserver helper they keep alive, running
    forever reparented to init)."""
    import sys as _sys

    from frob.process import install_sigterm_reaper

    _apply_verbose_env_override(_sys.argv[1:])
    install_sigterm_reaper()
    try:
        _dispatch(_sys.argv[1:])
    except KeyboardInterrupt:
        print("frob: interrupted", file=_sys.stderr)
        _sys.exit(130)
    except Exception as exc:  # noqa: BLE001 -- top-level CLI boundary must not crash raw
        _log.error("main: unhandled exception during dispatch: %s", exc, exc_info=True)
        print(f"frob: {exc}", file=_sys.stderr)
        _sys.exit(1)


# frob:ticket T-1567
def _is_quality_bind(argv: list[str]) -> bool:
    """`True` for `frob quality bind ...` (T-1567) -- split out of
    `_dispatch` purely to keep that function under the ARCH001 line
    threshold; `bind_runner.run` takes raw argv, so this argv shape is
    dispatched directly rather than through `quality_runner.run`."""
    return bool(argv) and argv[0] == "quality" and len(argv) > 1 and argv[1] == "bind"


# frob:ticket T-2242
def _is_release_publish(argv: list[str]) -> bool:
    """`True` for `frob release publish ...` (T-2242) -- mirrors
    `_is_quality_bind` above; `frob.release._cli.run_release_publish_
    command` takes a parsed `argparse.Namespace` from its OWN dedicated
    parser (same shape as `refactor`'s special case below), not
    `frob.app.release_runner`'s existing `AppConfig`-routed `stamp`/
    `check`/`sync` dispatch -- see `frob.release._cli`'s own module
    docstring for why."""
    return (
        bool(argv) and argv[0] == "release" and len(argv) > 1 and argv[1] == "publish"
    )


# frob:ticket T-0574
def _dispatch_bind(argv: list[str]) -> None:
    """`frob bind ...` (and, via `_dispatch_quality_bind` below, `frob
    quality bind ...`): `bind_runner.run` takes raw argv, not an
    `AppConfig`, so it is dispatched directly rather than through
    `quality_runner.run`. Split out of `_dispatch` (T-2452/ARCH001) so the
    routing table itself stays a pure list of one-line calls."""
    from frob.app.bind_runner import run as _bind_run

    _bind_run(argv)


# frob:ticket T-1567
def _dispatch_quality_bind(argv: list[str]) -> None:
    """`frob quality bind ...` (T-1567) -- mirrors top-level `frob bind`'s
    own dispatch (`_dispatch_bind`) with the leading `quality` token
    stripped before forwarding to the same `bind_runner.run`."""
    _dispatch_bind(argv[1:])


# frob:ticket T-0574
def _dispatch_agent(argv: list[str]) -> None:
    """`frob agent ...` (T-0574) -- dispatched directly, mirroring `frob
    bind` -- see `frob.app.agent_runner`'s module docstring for why."""
    from frob.app.agent_runner import run as _agent_run

    _agent_run(argv)


# frob:ticket T-0836
def _dispatch_worktree(argv: list[str]) -> None:
    """`frob worktree ...` (T-0836) -- dispatched directly, mirroring
    `frob bind`/`agent` -- see `frob.app.worktree_runner`'s module
    docstring for why."""
    from frob.app.worktree_runner import run as _worktree_run

    _worktree_run(argv)


# frob:ticket T-2241
def _dispatch_sync_skills(argv: list[str]) -> None:
    """`frob sync-skills ...` (T-2241) -- dispatched directly, mirroring
    `frob bind`/`agent`/`worktree` -- see
    `frob.scaffold._skills_sync.run`'s own docstring for why."""
    from frob.scaffold._skills_sync import run as _sync_skills_run

    _sync_skills_run(argv)


# frob:ticket T-2242
def _dispatch_release_publish(argv: list[str]) -> None:
    """`frob release publish ...` (T-2242) -- dispatched directly,
    mirroring `_dispatch_refactor` below -- own dedicated parser,
    `argparse.Namespace` in, exit code out. See `frob.release._cli`'s own
    module docstring for why this bypasses `release_runner.py`'s existing
    `stamp`/`check`/`sync` dispatch."""
    import sys as _sys

    from frob.release._cli import (
        add_release_publish_parser,
        run_release_publish_command,
    )

    release_parser = argparse.ArgumentParser(prog="frob")
    release_sub = release_parser.add_subparsers(dest="subcommand")
    add_release_publish_parser(release_sub)
    release_args = release_parser.parse_args(argv)
    _sys.exit(run_release_publish_command(release_args))


# frob:ticket T-1483
# frob:tests \
# tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_subcommand_dispatch\
# es_to_run_refactor_command kind="unit"  # noqa: E501
# frob:tests \
# tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_exit_code_propagate\
# s kind="unit"  # noqa: E501
def _dispatch_refactor(argv: list[str]) -> None:
    """`frob refactor ...` (T-1483) -- dispatched directly, mirroring
    `frob bind`/`agent`/`worktree` -- `frob.refactor._cli.
    run_refactor_command` takes a parsed `argparse.Namespace` and returns
    an exit code directly (T-1197's own shape, matching every other
    `_add_*_parser` builder for a later single-line wire-in), not the
    uniform `run(AppConfig)` entry point every subcommand in
    `_SUBCOMMAND_RUNNER_NAMES` (`frob.app.app`) shares -- so this
    subcommand is routed the same way as the other direct-dispatch verbs
    rather than added to that dict."""
    import sys as _sys

    from frob.refactor._cli import add_refactor_parser, run_refactor_command

    refactor_parser = argparse.ArgumentParser(prog="frob")
    refactor_sub = refactor_parser.add_subparsers(dest="subcommand")
    add_refactor_parser(refactor_sub)
    refactor_args = refactor_parser.parse_args(argv)
    _sys.exit(run_refactor_command(refactor_args))


# frob:ticket T-2993
# frob:waive DUP001 reason="deliberate structural duplicate of _dispatch_refactor \
# immediately above -- both are the same direct-dispatch-verb shape this file already \
# repeats 4 times (bind/agent/worktree/refactor) for a runner returning a raw exit \
# code instead of run(AppConfig); extracting a shared helper here would require \
# editing _dispatch_refactor's own body, which is refactor/'s live work area this \
# drive, not this ticket's scope"
def _dispatch_narrative(argv: list[str]) -> None:
    """`frob narrative ...` (T-2993) -- dispatched directly, mirroring
    `_dispatch_refactor` immediately above: `frob.narrative._cli.
    run_narrative_command` takes a parsed `argparse.Namespace` and returns
    an exit code directly, the same non-uniform shape `run_refactor_
    command` uses, for the same reason -- see that function's docstring.
    Author-invoked only; never called from `land` (T-2994's own doctrine:
    land may CHECK, never REWRITE)."""
    import sys as _sys

    # frob:waive SYS003 reason="mirrors the identical cli -> refactor import two \
    # functions above (_dispatch_refactor) -- frob.narrative has no strata \
    # component/node of its own yet (unlike frob.refactor's node + cli->refactor \
    # flow), so declaring this import needs a new node/flow, not a one-line fix; \
    # tracked by the same follow-up as the SELFAUDIT001 waiver on \
    # frob.gates._narrative_blocks" follow_up="T-3020"
    from frob.narrative._cli import add_narrative_parser, run_narrative_command

    narrative_parser = argparse.ArgumentParser(prog="frob")
    narrative_sub = narrative_parser.add_subparsers(dest="subcommand")
    add_narrative_parser(narrative_sub)
    narrative_args = narrative_parser.parse_args(argv)
    _sys.exit(run_narrative_command(narrative_args))


# frob:ticket T-2443
def _dispatch_default(argv: list[str]) -> None:
    """Every subcommand NOT special-cased ahead of `_build_parser` in
    `_dispatch`: builds the full argparse tree, parses `argv` against it,
    and routes into `App` via `AppConfig.from_external` -- the normal,
    uniform path every `Subcommand`-mapped runner shares. Split out of
    `_dispatch` (T-2452/ARCH001) so the routing table itself stays a pure
    list of one-line calls."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    pyproject = Path("pyproject.toml")
    _print_startup_warnings(pyproject.parent.resolve())
    if argv and argv[0] == "check":
        _reap_orphaned_forkservers_best_effort()
        # T-2484: `--json` makes stdout the machine-readable payload, so
        # this advisory must land on stderr ONLY in that mode -- see
        # `_report_concurrent_check_advisory_best_effort`'s own docstring
        # for why routing this through the normal INFO/WARNING level
        # split is not enough on its own.
        _report_concurrent_check_advisory_best_effort(
            force_stderr=getattr(args, "check_json", False)
        )
    cfg = AppConfig.from_external(args, pyproject)
    App(cfg)()


# frob:ticket T-2979
# frob:doc docs/modules/logging.md#public-api
# frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_v_sets_debug_env_var  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_dash_verbose_sets_debug_env_var  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_no_verbose_flag_leaves_env_var_untouched  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_existing_explicit_frob_log_level_is_not_clobbered  # noqa: E501
def _apply_verbose_env_override(argv: list[str]) -> None:
    """Set `FROB_VERBOSE=1` when `-v`/`--verbose` is present in `argv`
    (T-2979). Runs by RAW ARGV SCAN, before `_build_parser`/`_dispatch`,
    so it takes effect uniformly for every subcommand -- including the
    direct-dispatch verbs (`bind`/`agent`/`worktree`/`sync-skills`/
    `refactor`) that bypass the main argparse tree entirely and would
    otherwise never see this flag. `FROB_VERBOSE` (not a new env var) is
    reused deliberately -- see `frob.logging.logger`'s module docstring
    comment for why. Never overrides an already-set `FROB_VERBOSE`/
    `FROB_LOG_LEVEL` (an explicit env var from the caller wins)."""
    # frob:waive SEC110 reason="FROB_VERBOSE/FROB_LOG_LEVEL are boolean/ level logging \
    # flags, not secrets"
    if "FROB_VERBOSE" in os.environ or "FROB_LOG_LEVEL" in os.environ:
        return
    if "-v" in argv or "--verbose" in argv:
        os.environ["FROB_VERBOSE"] = "1"


# frob:ticket T-0355
# frob:ticket T-1218
# frob:ticket T-1483
# frob:ticket T-1567
# frob:ticket T-1808
# frob:ticket T-2443
# frob:ticket T-2452
def _dispatch(argv: list[str]) -> None:
    """`main`'s actual argv-to-`App` dispatch, split out so `main` can wrap
    only this in the `KeyboardInterrupt` handler (T-0355) without also
    catching interrupts raised by argument parsing itself. T-2452: the
    body itself is now a pure argv-routing table -- each special case's
    real work lives in its own `_dispatch_*` helper (ARCH001)."""
    if argv and argv[0] == "bind":
        _dispatch_bind(argv[1:])
    elif _is_quality_bind(argv):
        _dispatch_quality_bind(argv[1:])
    elif argv and argv[0] == "agent":
        _dispatch_agent(argv[1:])
    elif argv and argv[0] == "worktree":
        _dispatch_worktree(argv[1:])
    elif argv and argv[0] == "sync-skills":
        _dispatch_sync_skills(argv[1:])
    elif _is_release_publish(argv):
        _dispatch_release_publish(argv)
    elif argv and argv[0] == "refactor":
        _dispatch_refactor(argv)
    elif argv and argv[0] == "narrative":
        _dispatch_narrative(argv)
    else:
        _dispatch_default(argv)


# frob:ticket T-2443
def _reap_orphaned_forkservers_best_effort() -> None:
    """`frob check` startup call into `reap_orphaned_forkservers` -- best-
    effort and NEVER fatal to the real command that follows: an exception
    here (an unreadable `/proc` entry the function's own defenses did not
    anticipate, e.g.) is logged and swallowed rather than allowed to crash
    a `frob check` invocation that has nothing to do with this cleanup.
    Split out of `_dispatch` so that function's own body stays the pure
    argv-routing table its docstring claims (ARCH001 precedent, same
    reasoning as `_print_startup_warnings`'s own split)."""
    from frob.process import reap_orphaned_forkservers

    try:
        reap_orphaned_forkservers()
    except Exception as exc:  # noqa: BLE001 -- best-effort cleanup, never fatal
        _log.debug("_reap_orphaned_forkservers_best_effort: %s", exc, exc_info=True)


# frob:ticket T-2473
# frob:ticket T-2484
def _report_concurrent_check_advisory_best_effort(
    *, force_stderr: bool = False
) -> None:
    """`frob check` startup advisory (T-2473): logs how many OTHER `frob
    check` processes are already running on this host, plus available
    memory, so an agent/coordinator watching logs can see fleet-wide
    check pressure without deriving it by hand from `ps` (T-2473's own
    filed measurement: 12 concurrent checks, 7.8GB swap, throughput DOWN
    as agent count went up). ADVISORY ONLY -- never blocks, queues, or
    refuses this check; the coordinator's own chosen direction over an
    enforced concurrency limit (a busy fleet risks becoming a queue of
    stalled agents if the limit is chosen badly). Best-effort and NEVER
    fatal to the real check that follows, same posture as `_reap_
    orphaned_forkservers_best_effort` immediately above -- an unreadable
    `/proc` entry here must never crash a `frob check` invocation that
    has nothing to do with this reporting. Logged at INFO when other
    checks ARE running (the actionable case) so it surfaces in a normal
    log-level run without needing `-v`, WARNING when 4 or more are
    running (this host's own measured degradation point), and skipped
    silently (not even at DEBUG) when the count is 0 -- an idle machine's
    check gets no extra log noise, matching the must-not-stall
    acceptance's spirit even though this function itself never adds
    latency.

    T-2484: `force_stderr=True` (passed by `_dispatch` exactly when
    `--json` was requested) bypasses the logger entirely and `print`s
    straight to `sys.stderr` instead. The INFO/WARNING split above is a
    LOG LEVEL, and `frob.logging.config.toml`'s `below_warning` filter
    routes INFO to the STDOUT handler by default -- under `--json`,
    stdout is the machine-readable `CheckResult` payload, so an INFO-
    level advisory landing ahead of it corrupts every parser that does
    not know to strip a prefix (this was T-2484 itself: `scripts/check_
    summary.py` and the land-path's `_parse_check_json` both broke this
    way). Raising the stdout handler's level for the call (`frob.logging.
    quiet.quiet_stdout_logs`) was the first fix attempted here and is
    WRONG: it also silences the WARNING-vs-INFO threshold check itself
    only for records at/above the raised level, but for an INFO record
    specifically it makes the advisory vanish from BOTH streams --
    stdout because the handler is quieted, stderr because INFO never
    routed there in the first place (`config.toml`'s stderr handler is
    `level = "WARNING"`). A direct `print(..., file=sys.stderr)`, mirroring
    `_print_startup_warnings`'s own established idiom in this same file,
    is the only way to guarantee the message reaches stderr regardless of
    which of the two severities fired -- so the non-`--json` path keeps
    the existing level-based logger call (preserving `caplog`-based
    introspection and the INFO/WARNING split for normal log-watching
    tooling) while `--json` switches to the guaranteed-stderr print."""
    from frob.process._reap import count_running_checks

    try:
        others = count_running_checks()
    except Exception as exc:  # noqa: BLE001 -- best-effort, never fatal
        _log.debug(
            "_report_concurrent_check_advisory_best_effort: %s", exc, exc_info=True
        )
        return
    if not others:
        return
    message = (
        "frob check: %d other check(s) already running on this host -- "
        "see `scripts/fleet_status.py` for swap/load before dispatching "
        "more (T-2473, advisory only -- this check is not deferred)"
    )
    if force_stderr:
        import sys as _sys

        print(message % others, file=_sys.stderr)
        return
    level = _log.warning if others >= 4 else _log.info
    level(message, others)


# frob:ticket T-1808
# frob:ticket T-3011
def _print_startup_warnings(repo_root: Path) -> None:
    """Every loud, best-effort, read-only stderr warning `_dispatch` prints
    ahead of a real subcommand run -- stale global/floor binary skew
    (`stale_install_warning`/`stale_binary_warning`), plus (T-1808) Claude-
    config drift (`frob.app.claude_runner.drift_warning`): detection only,
    surfaced where an operator already looks, never a write. Split out of
    `_dispatch` (ARCH001) so that dispatch function stays the pure argv
    routing table its own docstring claims to be."""
    import sys as _sys

    warning = stale_install_warning(repo_root)
    if warning is not None:
        print(warning, file=_sys.stderr)
    # T-1218: floor check, distinct from the exact-match check above --
    # applies to any repo declaring frob.toml's min_frob_version, not
    # just frob's own checkout.
    floor_warning = stale_binary_warning(repo_root)
    if floor_warning is not None:
        print(floor_warning, file=_sys.stderr)
    # T-3129: version-string equality (both checks above) cannot detect a
    # stale build whose declared version never moved past its last bump --
    # a git-content fingerprint check, distinct from both.
    fingerprint_warning = binary_fingerprint_warning(repo_root)
    if fingerprint_warning is not None:
        print(fingerprint_warning, file=_sys.stderr)
    # T-1808: surfaced automatically on every invocation, where an
    # operator already looks -- detection only, never a write (the write
    # stays the explicit `frob claude sync` call).
    from frob.app.claude_runner import drift_warning

    claude_warning = drift_warning(repo_root)
    if claude_warning is not None:
        print(claude_warning, file=_sys.stderr)
    # T-3011: PLATFORM001 applied to distribution -- degrade LOUDLY and BY
    # NAME, never silently; see native_degrade_warning's own docstring.
    native_warning = native_degrade_warning(repo_root)
    if native_warning is not None:
        print(native_warning, file=_sys.stderr)


if __name__ == "__main__":
    main()
