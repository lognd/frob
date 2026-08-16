from __future__ import annotations

import contextlib
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

from frob.app._check_chunking import _run_budgeted_check, _run_stamp_baseline
from frob.app._style import style_fail, style_warn
from frob.app.config import AppConfig
from frob.check import (
    CheckResult,
    detect_project_type,
    run_check,
    run_check_cpp,
    run_check_rust,
    run_check_ts,
)
from frob.logging import get_logger, quiet_stdout_logs, stdout_log_level
from frob.logging.color import should_color
from frob.process.parsers.common import Diagnostic, ToolResult
from frob.render import Progress, Renderer

#: DEPLOY001/DEPLOY002/DEPLOY003's severity literal, matching
#: `Diagnostic.severity`'s type (`frob.process.parsers.common.Severity`)
#: without importing it just for this one string -- the same pragmatic
#: inline-literal precedent `_skip_note_result` below already uses for
#: its own diagnostic.
_DEPLOY001_SEVERITY = "error"
_DEPLOY_CONFORM_SEVERITY = "error"

_log = get_logger(__name__)


def _verbosity_to_level(count: int) -> int:
    """Map `frob check`'s `-v` count to a stdout log level (T-0202).

    0 (default) = WARNING only, so the printed summary/violations table is
    the whole story; 1 (`-v`) = INFO, restoring the per-file/per-stage
    firehose that used to be the unconditional default; 2+ (`-vv`) = DEBUG,
    adding per-symbol digest/dispatch detail.
    """
    if count <= 0:
        return logging.WARNING
    if count == 1:
        return logging.INFO
    return logging.DEBUG


def _toml_top_level_updates(cfg: AppConfig, data: dict) -> dict:
    """`check_base`/`check_type` defaults from `frob.toml`'s top level."""
    updates: dict = {}
    if cfg.check_base is None and isinstance(data.get("check_base"), str):
        updates["check_base"] = data["check_base"]
    if cfg.check_type is None and isinstance(data.get("check_type"), str):
        updates["check_type"] = data["check_type"]
    return updates


# frob:ticket T-1038
def _toml_check_section_updates(cfg: AppConfig, section: dict) -> dict:
    """`check_only`/`check_skip_*` defaults from `frob.toml`'s `[check]` table."""
    updates: dict = {}
    if not cfg.check_only and isinstance(section.get("only"), list):
        updates["check_only"] = [str(s) for s in section["only"]]
    raw_skip = section.get("skip")
    skip_list: list = raw_skip if isinstance(raw_skip, list) else []
    # frob:waive OPAQUE001 reason="T-1038: field ranges over frob.toml's own \
    # [check].skip list (the repo owner's own config, not attacker/external input); \
    # hasattr() gates the lookup to real AppConfig fields, so an unknown stage name is \
    # a silent no-op, never an arbitrary-attribute write"
    for stage in skip_list:
        field = f"check_skip_{str(stage).replace('-', '_')}"
        if hasattr(cfg, field) and not getattr(cfg, field):
            updates[field] = True
    # frob:ticket T-0421
    if not cfg.check_skip_unchanged and section.get("skip_unchanged") is True:
        updates["check_skip_unchanged"] = True
    return updates


def _apply_frob_toml_defaults(cfg: AppConfig, root: Path) -> AppConfig:
    """Fill check defaults from frob.toml so ONE file configures a repo.

    CLI flags win; frob.toml supplies repo defaults: top-level `check_base`
    and `check_type`, plus `[check] skip = [...]` / `only = [...]` (the
    polyglot-monorepo dial, T-0022 -- pyproject [tool.frob] previously held
    these alone, which two adoption passes independently tripped over).
    """
    import tomllib

    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return cfg
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("frob.toml unreadable for check defaults: %s", exc)
        return cfg

    updates = _toml_top_level_updates(cfg, data)
    updates |= _toml_check_section_updates(cfg, data.get("check", {}))
    if updates:
        _log_applied_defaults(updates)
        return cfg.model_copy(update=updates)
    return cfg


def _log_applied_defaults(updates: dict) -> None:
    """Debug-log which frob.toml check defaults were applied, in sorted order."""
    _log.debug("check defaults from frob.toml: %s", sorted(updates))


def _detected_types(root: Path) -> list[str]:
    """Every language stage whose marker file is present under `root`.

    Order is stable (rust, cpp, python, typescript) and independent of
    `detect_project_type`'s single-winner priority -- that function picks
    ONE type for legacy single-language callers; this one enumerates ALL of
    them so a polyglot repo can run every applicable stage instead of
    silently running only the first match (T-0229).
    """
    sentinels = {
        "rust": (root / "Cargo.toml").exists(),
        "cpp": (root / "CMakeLists.txt").exists(),
        "python": (root / "pyproject.toml").exists() or (root / "setup.py").exists(),
        "typescript": (root / "package.json").exists(),
    }
    return [lang for lang in ("rust", "cpp", "python", "typescript") if sentinels[lang]]


# frob:ticket T-0421
#: File suffixes (and repo-root marker files) that count as a change to a
#: language's own tooling surface -- the set `_language_unchanged` diffs
#: against, so a Rust-only edit never marks Python SKIPPED-unchanged and
#: vice versa.
_LANGUAGE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "rust": (".rs", "Cargo.toml", "Cargo.lock"),
    "cpp": (".c", ".h", ".cc", ".cpp", ".hpp", ".hh", "CMakeLists.txt"),
    "python": (".py", "pyproject.toml"),
    "typescript": (".ts", ".tsx", ".js", ".jsx", "package.json"),
}


# frob:ticket T-0421
def _language_unchanged(root: Path, base: str, project_type: str) -> bool:
    """Whether NO file matching `project_type`'s suffixes changed against
    `base` (T-0421): reuses `frob.gitio.working_diff`'s merge-base hunk
    listing, the same change surface `--delta`/scoped gates already diff
    against, rather than a second bespoke git invocation. Defaults to
    `False` (never silently skip) on any git failure (no repo, no `base`
    ref, detached/shallow clone) -- an honest "could not determine
    unchanged" always falls back to running the stage.
    """
    from frob.gitio import working_diff

    result = working_diff(root, base)
    if result.is_err:
        return False
    suffixes = _LANGUAGE_SUFFIXES.get(project_type, ())
    return not any(hunk.file.endswith(suffixes) for hunk in result.danger_ok.hunks)


# frob:ticket T-0421
def _unchanged_skip_result(project_type: str) -> ToolResult:
    """A `SKIPPED (unchanged)` `ToolResult` for `project_type` (T-0421): the
    language IS present in the project but nothing under its own suffixes
    changed since `base`, so its tooling did not re-run this time -- honest
    and visible, distinct from `_skip_note_result`'s "pinned away" case and
    from a language that is simply absent (which shows no line at all,
    `_detected_types` never naming it)."""
    summary = f"SKIPPED: {project_type} (unchanged since base)"
    return ToolResult(
        tool=f"skipped:{project_type}",
        exit_code=0,
        summary=summary,
        diagnostics=[Diagnostic(severity="note", message=summary)],
    )


def _skip_note_result(skipped: str, chosen: str) -> ToolResult:
    """A synthetic `ToolResult` recording that `skipped`'s stage did NOT run.

    Pinning `check_type` (CLI `--type` or `frob.toml`'s top-level
    `check_type`) is a deliberate, honest way to run only one language's
    stage in a polyglot repo -- but the pin must never look like a silent
    clean pass for the language it excludes (T-0229: a lithos `frob check`
    warned about a skipped stage and then printed `[PASS] 0 errors 0
    warnings`, contradicting its own warning). This turns the exclusion
    into a visible `SKIPPED: <lang>` line in both the text and JSON report,
    with exit_code 0 (a deliberate pin) so it never contributes a false
    error/warning count.
    """
    summary = f"SKIPPED: {skipped} (pinned to {chosen} via check_type)"
    return ToolResult(
        tool=f"skipped:{skipped}",
        exit_code=0,
        summary=summary,
        diagnostics=[Diagnostic(severity="note", message=summary)],
    )


def _warn_if_polyglot(root: Path, chosen: str, others: list[str]) -> None:
    """Loudly name the language stages a `check_type` pin is excluding.

    Cargo.toml beats pyproject.toml in detect_project_type, so a mixed repo
    could silently run ONE language's checks -- gates included -- and look
    clean (found during the feldspar adoption, T-0022). Auto-detection now
    runs every detected stage by default (see `_run_all_detected`); this
    warning only fires for the deliberate opt-out (`check_type` pinned in
    frob.toml or `--type` on the CLI), where the summary also carries a
    `SKIPPED: ...` line per excluded language (`_skip_note_result`).
    """
    if others:
        _log.warning(
            "check_type pinned to %s: %s checks (gates included) are NOT "
            "running -- this is a deliberate opt-out; unpin check_type to "
            "run every detected stage",
            chosen,
            "/".join(sorted(others)),
        )


# frob:ticket T-1445
def _dispatch_check_cpp(cfg: AppConfig, root: Path):
    """Run `run_check_cpp` with `cfg`'s C++-toolchain skip flags and gate selectors.

    T-0608: `check_skip_gates`/`check_ticket`/`check_base`/`check_delta` were
    silently dropped here (only `_dispatch_check_python` threaded them),
    so CLI-level `--ticket`/`--base`/`--delta`/`--skip-gates` scoping was
    ignored for C++ repos even though `run_check_cpp` (T-0554) accepts them.
    """
    return run_check_cpp(
        root,
        build_dir=cfg.check_build_dir,
        skip_build=cfg.check_skip_build,
        skip_clang_tidy=cfg.check_skip_clang_tidy,
        skip_clang_format=cfg.check_skip_clang_format,
        skip_tests=cfg.check_skip_tests,
        skip_gates=cfg.check_skip_gates,
        valgrind=cfg.check_valgrind,
        ticket=cfg.check_ticket,
        base=cfg.check_base,
        delta=cfg.check_delta,
        no_cache=cfg.check_no_cache,
    )


# frob:ticket T-1445
def _dispatch_check_rust(cfg: AppConfig, root: Path):
    """Run `run_check_rust` with `cfg`'s Rust-toolchain skip flags and gate selectors.

    T-0608: see `_dispatch_check_cpp`'s docstring -- the same gap applied
    here for Rust repos.
    """
    return run_check_rust(
        root,
        skip_check=cfg.check_skip_cargo_check,
        skip_clippy=cfg.check_skip_clippy,
        skip_fmt=cfg.check_skip_fmt,
        skip_tests=cfg.check_skip_tests,
        skip_gates=cfg.check_skip_gates,
        valgrind=cfg.check_valgrind,
        ticket=cfg.check_ticket,
        base=cfg.check_base,
        delta=cfg.check_delta,
        no_cache=cfg.check_no_cache,
    )


# frob:ticket T-1445
def _dispatch_check_ts(cfg: AppConfig, root: Path):
    """Run `run_check_ts` with `cfg`'s TypeScript-toolchain skip flags and
    gate selectors.

    T-0608: see `_dispatch_check_cpp`'s docstring -- the same gap applied
    here for TypeScript repos.
    """
    return run_check_ts(
        root,
        skip_tsc=cfg.check_skip_tsc,
        skip_eslint=cfg.check_skip_eslint,
        skip_prettier=cfg.check_skip_prettier,
        skip_tests=cfg.check_skip_tests,
        skip_gates=cfg.check_skip_gates,
        ticket=cfg.check_ticket,
        base=cfg.check_base,
        delta=cfg.check_delta,
        no_cache=cfg.check_no_cache,
    )


# frob:ticket T-1445
def _dispatch_check_python(cfg: AppConfig, root: Path):
    """Run `run_check` with `cfg`'s Python-toolchain skip flags and gate selectors."""
    return run_check(
        root,
        skip_ruff=cfg.check_skip_ruff,
        skip_ty=cfg.check_skip_ty,
        skip_arch=cfg.check_skip_arch,
        skip_cycle=cfg.check_skip_cycle,
        skip_dup=cfg.check_skip_dup,
        skip_bind=cfg.check_skip_bind,
        skip_exports=cfg.check_skip_exports,
        skip_gates=cfg.check_skip_gates,
        only=frozenset(cfg.check_only) if cfg.check_only else None,
        ticket=cfg.check_ticket,
        base=cfg.check_base,
        delta=cfg.check_delta,
        no_cache=cfg.check_no_cache,
    )


_DISPATCH_BY_TYPE = {
    "cpp": _dispatch_check_cpp,
    "rust": _dispatch_check_rust,
    "typescript": _dispatch_check_ts,
    "python": _dispatch_check_python,
}


# frob:ticket T-0546
def _unknown_project_type_result(root: Path, project_type: str) -> CheckResult:
    """A loud CHECK001 error `CheckResult` for an unrecognized `project_type`
    (T-0404 finding 6).

    `detect_project_type`/`_detected_types` return `"unknown"` (or, in
    principle, any type string with no entry in `_DISPATCH_BY_TYPE`) when no
    language sentinel file is found. `_dispatch_check` used to fall back to
    `_dispatch_check_python` for any unmapped type
    (`_DISPATCH_BY_TYPE.get(project_type, _dispatch_check_python)`), so a
    repo with no recognized marker file silently ran ruff/ty over a
    non-Python tree and reported whatever noise that produced, instead of a
    clear "could not determine project type" failure. This returns one
    ERROR-severity `unknown-project-type` `ToolResult` instead, so `frob
    check` fails loudly and unambiguously rather than silently substituting
    the wrong toolchain.
    """
    summary = f"unknown project type: {project_type!r} (no dispatchable language stage)"
    result = ToolResult(
        tool="unknown-project-type",
        exit_code=1,
        summary=summary,
        diagnostics=[Diagnostic(severity="error", code="CHECK001", message=summary)],
    )
    return CheckResult(path=str(root), results=[result])


# frob:ticket T-0546
# frob:tests \
# tests/integration/test_interfaces.py::TestInterfaces.test_main_cli_dispatches
def _dispatch_check(cfg: AppConfig, root: Path, project_type: str) -> CheckResult:
    """Run the language-appropriate check stack for `project_type`, or a
    loud CHECK001 error `CheckResult` when `project_type` has no
    dispatchable stage (T-0404 finding 6) -- never a silent Python
    fallback."""
    dispatch = _DISPATCH_BY_TYPE.get(project_type)
    if dispatch is None:
        return _unknown_project_type_result(root, project_type)
    return dispatch(cfg, root)


# frob:ticket T-0229
# frob:ticket T-0419
# frob:ticket T-0421
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage.test_unchanged_python_reports_skipped_not_silent  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage.test_changed_python_still_runs  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage.test_absent_language_never_shown  # noqa: E501
def _run_all_detected(
    cfg: AppConfig,
    root: Path,
    types: list[str],
    *,
    progress: Progress | None = None,
    total: int = 0,
) -> CheckResult:
    """Run every detected language stage and merge their results into one report.

    T-0229: a polyglot repo used to auto-detect and run exactly ONE
    language's stage (whichever `detect_project_type` picked first), gates
    included, and report a clean PASS with every other language's checks
    never having run. Auto-detection now runs ALL detected stages by
    default -- the only way to run a single stage deliberately is pinning
    `check_type` (CLI `--type` or `frob.toml`), which stays fast and now
    also reports a `SKIPPED: ...` line per excluded language
    (`_skip_note_result`). `total_errors`/`total_warnings` sum naturally
    across the merged `results` list, so a failure in ANY detected stage
    fails the overall run.

    T-0419: `progress` (a no-op off a TTY) is updated once per language
    stage as it completes, against `total`'s overall stage count -- the
    live task-list contract lives entirely in `Progress`; this just feeds
    it labels/counts as the orchestrator's existing stage loop advances.

    T-0421: when `cfg.check_skip_unchanged` is set (frob.toml opt-in
    only), a language whose own suffixes show no change against
    `cfg.check_base` (`_language_unchanged`) reports a visible
    `SKIPPED: <lang> (unchanged since base)` line instead of re-running
    its full stage -- honest and distinct from a language that is simply
    absent (never named at all, see `_detected_types`).
    """
    results: list[ToolResult] = []
    for i, project_type in enumerate(types):
        if progress is not None:
            progress.update(f"check: {project_type}", i, total)
        if cfg.check_skip_unchanged and _language_unchanged(
            root, cfg.check_base or "main", project_type
        ):
            results.append(_unchanged_skip_result(project_type))
        else:
            results.extend(_dispatch_check(cfg, root, project_type).results)
        if progress is not None:
            progress.update(f"check: {project_type}", i + 1, total)
    return CheckResult(path=str(root), results=results)


# frob:ticket T-1124
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_deploy_stages_appended_when_deploy_dir_present kind="unit"  # noqa: E501
def _opt_in_deploy_stage_result(
    root: Path,
    violations_fn: Callable[[Path], object],
    wrap_fn: Callable[[object], ToolResult],
) -> ToolResult | None:
    """Shared `(Path) -> ToolResult | None` shape both deploy-epic stages
    use (T-1124: extracted from `_deploy_drift_result`/
    `_deploy_conformance_result`, which were identical bar which
    violations-function/wrap-function pair they called): opt-in on
    `deploy/` existing, `None` (no stage at all) when it is absent, else
    `violations_fn(root)` wrapped via `wrap_fn`."""
    if not (root / "deploy").is_dir():
        return None
    violations = violations_fn(root)
    return wrap_fn(violations)


# frob:ticket T-1809
# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
# frob:tests \
# tests/test_check_runner.py::TestClaudeConfigDriftStage.test_reports_drift_when_manage\
# d_copy_absent
# frob:tests \
# tests/test_check_runner.py::TestClaudeConfigDriftStage.test_clean_when_in_sync
# frob:tests \
# tests/test_check_runner.py::TestClaudeConfigDriftStage.test_no_stage_when_repo_has_no\
# _managed_config
def _claude_config_drift_result(root: Path) -> ToolResult | None:
    """CLAUDE001 (T-1809, T-1719 item 2): fails `frob check` when a
    `.claude/hooks/sync-claude-config.py`-managed file (T-1808's `MANAGED`
    manifest) differs from its materialized `~/.claude/` copy, or a
    managed source is missing entirely.

    Not wired into `frob.gates`'s pluggable job table (`src/frob/gates/**`
    sat under another ticket's live cross-worktree lease for the whole of
    this ticket's dispatch window) -- instead this is one more opt-in
    extra stage `run()` folds into `CheckResult`, the identical shape
    `_deploy_drift_result`/`_deploy_conformance_result` above already use
    for the same reason (their own docstrings note `src/frob/gates/**`
    was out of THEIR ticket's scope too). Opt-in on `.claude/hooks/sync-
    claude-config.py` existing (`frob.app.claude_runner.drift_report`'s own
    `None`-when-absent convention) -- a repo that does not own this repo's
    managed Claude config sees no `claude-config-drift` line at all, same
    posture as `deploy-drift` on a repo with no `deploy/`.

    Detection only, never a write -- the WRITE stays `frob claude sync`
    (T-1808), run by hand or from CI; this stage is what makes silent
    drift a `frob check` failure instead of something only discovered the
    next time a hook mysteriously does not fire."""
    from frob.app.claude_runner import drift_report

    report = drift_report(root)
    if report is None:
        return None
    drifted, missing = report
    diagnostics = [
        Diagnostic(
            file=str(root / ".claude" / "hooks" / "sync-claude-config.py"),
            severity="error",
            code="CLAUDE001",
            message=f"managed file drifted from ~/.claude/: {entry} -- "
            "reconcile with `frob claude sync`",
        )
        for entry in drifted
    ]
    diagnostics.extend(
        Diagnostic(
            file=str(root / ".claude" / "hooks" / "sync-claude-config.py"),
            severity="error",
            code="CLAUDE001",
            message=f"managed source missing: {source_rel}",
        )
        for source_rel in missing
    )
    n_bad = len(diagnostics)
    summary = (
        f"{n_bad} managed Claude-config file(s) drifted or missing"
        if n_bad
        else "Claude config in sync with ~/.claude/"
    )
    return ToolResult(
        tool="claude-config-drift",
        exit_code=1 if n_bad else 0,
        diagnostics=diagnostics,
        summary=summary,
    )


def _deploy_drift_result(root: Path) -> ToolResult | None:
    """DEPLOY001: `deploy/{install,status,uninstall}.sh` vs. regeneration
    from the current design model (`frob.deploy.deploy_drift_violations`,
    T-0257). Not wired into `frob.gates`'s pluggable job table (that
    module is out of this ticket's `scope`) -- instead this runs as one
    more extra stage `run()` folds into `CheckResult`, the same shape
    ruff/ty/arch/cycle/dup/bind/exports already use in
    `_dispatch_check_python`. Opt-in on `deploy/` existing (module
    docstring's posture); returns `None` (no stage at all, not merely a
    clean one) when `deploy/` is absent, so a repo that has never opted
    into the deploy epic sees no `deploy-drift` line at all."""
    from frob.deploy import deploy_drift_violations

    return _opt_in_deploy_stage_result(
        root, deploy_drift_violations, _deploy_drift_tool_result
    )


def _deploy_drift_tool_result(violations) -> ToolResult:  # noqa: ANN001
    """Wrap DEPLOY001 `violations` (possibly empty) as the `deploy-drift`
    stage's `ToolResult`."""
    diagnostics = [
        Diagnostic(
            file=v.file,
            severity=_DEPLOY001_SEVERITY,
            code="DEPLOY001",
            message=v.message,
        )
        for v in violations
    ]
    summary = (
        f"{len(violations)} deploy script(s) out of date"
        if violations
        else "deploy scripts current"
    )
    return ToolResult(
        tool="deploy-drift",
        exit_code=1 if violations else 0,
        diagnostics=diagnostics,
        summary=summary,
    )


def _deploy_conformance_result(root: Path) -> ToolResult | None:
    """DEPLOY002/DEPLOY003: committed `deploy/install.sh`/`uninstall.sh`
    mutation surface vs. the current design model's `HostManifest` set
    (`frob.deploy.deploy_conformance_violations`, T-0258). Same "extra
    stage beyond `frob.gates`'s job table" shape `_deploy_drift_result`
    already uses (`src/frob/gates/**` stays out of this ticket's `scope`
    too), via the shared `_opt_in_deploy_stage_result` (T-1124). Opt-in on
    `deploy/` existing; returns `None` (no stage) when the directory is
    absent."""
    from frob.deploy import deploy_conformance_violations

    return _opt_in_deploy_stage_result(
        root, deploy_conformance_violations, _deploy_conformance_tool_result
    )


def _deploy_conformance_tool_result(violations) -> ToolResult:  # noqa: ANN001
    """Wrap DEPLOY002/DEPLOY003 `violations` (possibly empty) as the
    `deploy-conformance` stage's `ToolResult`."""
    diagnostics = [
        Diagnostic(
            file=v.file,
            severity=_DEPLOY_CONFORM_SEVERITY,
            code=v.code,
            message=v.message,
        )
        for v in violations
    ]
    summary = (
        f"{len(violations)} deploy conformance violation(s)"
        if violations
        else "deploy scripts conform to HostManifest"
    )
    return ToolResult(
        tool="deploy-conformance",
        exit_code=1 if violations else 0,
        diagnostics=diagnostics,
        summary=summary,
    )


# frob:ticket T-0586
# frob:ticket T-1419
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_mode_passes_loaded_snapshot kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_mode_calls_stamp_and_returns kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_failure_exits_1 kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_lock_source_sha_mismatch_exits_1 kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_lock_source_sha_match_succeeds kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_no_snapshot_skips_durability_check kind="unit"  # noqa: E501
def _run_stamp_coverage(root: Path) -> None:
    """`frob check --stamp-coverage`: record coverage.xml as the current stamp,
    and refresh the committed `frob-coverage.lock.json` summary.

    T-0586: `stamp_coverage` only refreshes the lock (`write_coverage_lock`)
    when handed a `GraphSnapshot` -- without one it still writes the stamp
    file but silently skips the lock refresh. Loads the same on-disk graph
    cache `frob.app.sys_runner._load_snapshot` uses (building it if stale)
    so this CLI entry point keeps the lock current without any new flag.
    A snapshot load failure degrades to the pre-T-0586 stamp-only behavior
    (still stamps, just without the lock refresh) rather than failing the
    whole command -- the lock refresh is a bonus this call provides, not a
    hard requirement of stamping.

    T-1419: a real incident found the committed `frob-coverage.lock.json`
    still asserting a stale `source_sha`/percentage for a module coverage.xml
    measured at genuine zero, even though `stamp_coverage` had logged a
    successful write for the run in question -- the CALL reported success,
    but the on-disk committed lock never durably reflected it. `stamp_
    coverage` writes `.frob/coverage-stamp` and `frob-coverage.lock.json`
    from the SAME `coverage.xml` source sha in one call, so immediately
    after a call that attempted a lock refresh (`snapshot` was available),
    this re-reads both artifacts back from disk and refuses loudly (exit 1)
    if their `source_sha` values disagree -- that disagreement is exactly
    the observable symptom of a write that reported success but did not
    durably persist, whether the cause is a silent write no-op or some
    other process's write racing/overwriting this one. No snapshot means no
    lock refresh was ever attempted (the pre-existing, intentional T-0586
    skip), so there is nothing to durability-check in that case.
    """
    from frob.gates import stamp_coverage
    from frob.graph import build_graph, load_graph

    cache = root / ".frob" / "cache.db"
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info(
            "stamp-coverage: graph cache stale/missing, building: %s",
            loaded.danger_err,
        )
        loaded = build_graph(root, cache)
    snapshot = None
    if loaded.is_err:
        _log.warning(
            "stamp-coverage: graph unavailable, lock refresh will be skipped: %s",
            loaded.danger_err,
        )
    else:
        snapshot = loaded.danger_ok

    result = stamp_coverage(root, snapshot)
    if result.is_err:
        _log.error("stamp-coverage failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("coverage stamp written")

    if snapshot is not None and not _lock_matches_stamp(root):
        _log.error(
            "stamp-coverage: %s reports a different source_sha than the "
            "coverage stamp that was just written -- the lock refresh did "
            "not durably persist this run's data (T-1419); re-run `frob "
            "check --stamp-coverage`, and if this repeats, something "
            "outside this call is overwriting frob-coverage.lock.json "
            "after the write",
            root / "frob-coverage.lock.json",
        )
        sys.exit(1)


# frob:ticket T-1419
def _lock_matches_stamp(root: Path) -> bool:
    """True when the committed `frob-coverage.lock.json` just written by
    `stamp_coverage` carries the SAME `source_sha` as `.frob/coverage-stamp`
    from that same call (T-1419).

    Both artifacts are written from one `coverage.xml` inside a single
    `stamp_coverage` invocation, so under a durable write they can never
    disagree -- a mismatch here is the read-after-write proof that the
    lock's on-disk content is not what this run just produced, regardless
    of whether the write silently no-opped or something else clobbered it
    afterward. Missing/unreadable data on either side reads as `False`
    (cannot confirm durability, so do not claim it)."""
    from frob.gates import load_coverage_lock, load_stamp

    lock = load_coverage_lock(root)
    stamp = load_stamp(root)
    if lock is None or stamp is None:
        return False
    return lock.get("source_sha") == stamp.get("source_sha")


# frob:ticket T-0563
# frob:ticket T-1260
# frob:ticket T-2235
def _report_check_result(  # noqa: ANN001
    cfg: AppConfig,
    result,
    fix_report: dict | None = None,
    budget_report: dict | None = None,
) -> None:
    """Emit `result` as JSON or colorized text per `cfg`, then exit 1 on errors.

    T-0563: routed through `frob.render`/`_log.info` instead of a bare
    `print`, matching every other runner (RENDER001 forbids bare stdout
    writes everywhere, including the `--json` escape hatch). `_report_
    check_result` runs after `_run_all_stages`'s `_stdout_log_ctx` has
    already restored the stdout handler to its pre-stage level (T-0202),
    so this is not gated by `-v`/`--json`-forced-quiet the way per-stage
    diagnostics are -- the summary/violations table always appears.

    T-1260: `fix_report` is `None` for every non-`--fix` call (the default,
    and the ONLY path a plain `frob check` ever takes -- byte-identical
    output to before this ticket, acceptance criterion 2). When `--fix` was
    passed, `fix_report` additionally carries a `"fix"` JSON key (fixed/
    rolled_back/fixits, always present -- never a missing key, even when
    nothing was fixed, acceptance criterion 1) or an extra text section.

    T-2235: `budget_report` is `None` for every non-`--budget` call (the
    unbudgeted default and any other early-exit mode -- byte-identical
    `results`/`path`/exit-code output to before this ticket, acceptance
    criterion 3). `_run_budgeted_check` is the only caller that ever passes
    one: a `{"requested_seconds", "executed_groups", "skipped_groups",
    "complete"}` dict spliced in as a top-level `"budget"` JSON key so a
    consumer can tell "nothing skipped" (empty `skipped_groups` list) from
    "this build does not report skips" (the key absent entirely, on any
    non-budgeted call) without parsing anything else in the payload.
    """
    if cfg.check_json:
        _log.info(_result_as_json_with_fix(result, fix_report, budget_report))
    else:
        from frob.logging.color import should_color

        renderer = Renderer.for_stream(sys.stdout)
        text = result.as_text(color=should_color(sys.stdout))
        if fix_report is not None:
            text = f"{text}\n\n{_fix_report_text(fix_report)}"
        if budget_report is not None:
            text = f"{text}\n\n{_budget_report_text(budget_report)}"
        renderer.line(text)

    if result.total_errors > 0:
        sys.exit(1)


def _result_as_json_with_fix(
    result,  # noqa: ANN001
    fix_report: dict | None,
    budget_report: dict | None = None,
) -> str:
    """`result.as_json()`, with additional top-level `"fix"`/`"budget"` keys
    spliced in when `fix_report`/`budget_report` are not `None` (T-1260,
    T-2235). `CheckResult` itself (`frob.check.__init__`) is out of this
    ticket's scope, so both keys are added HERE, at the JSON-string layer,
    rather than as new `CheckResult` fields -- `--fix`/`--budget` are
    strictly additive to `frob check`'s existing `--json` shape, never a
    reshape of it (this is also why an unbudgeted/non-`--fix` call's JSON
    stays byte-identical: neither key is ever added unless its report is
    not `None`)."""
    if fix_report is None and budget_report is None:
        return result.as_json()
    import json

    payload = json.loads(result.as_json())
    if fix_report is not None:
        payload["fix"] = fix_report
    if budget_report is not None:
        payload["budget"] = budget_report
    return json.dumps(payload, indent=2)


# frob:ticket T-2235
def _budget_report_text(budget_report: dict) -> str:
    """The `--budget` coverage summary appended to `frob check --budget`'s
    human-readable text output (T-2235): which stage groups this
    invocation actually executed vs. skipped, so an operator reading a
    terminal sees the same completeness signal `"budget"`'s JSON key
    carries, without needing `--json`."""
    executed = budget_report.get("executed_groups", [])
    skipped = budget_report.get("skipped_groups", [])
    if skipped:
        skipped_line = f"SKIPPED this run ({len(skipped)}): {', '.join(skipped)}"
    else:
        skipped_line = "SKIPPED this run: none -- every planned stage group ran"
    return (
        f"## Budget coverage  ran={len(executed)}  skipped={len(skipped)}\n"
        f"  executed: {', '.join(executed) if executed else 'none'}\n"
        f"  {skipped_line}"
    )


def _fix_report_text(fix_report: dict) -> str:
    """The `--fix` summary block appended to `frob check --fix`'s
    human-readable text output: how many fixes were applied, rolled back,
    and left as Tier-C fix-its (T-1260's three-count acceptance shape;
    T-1481 wires real Tier-B/C content into `rolled_back`/`fixits`,
    previously always `[]` since neither engine had a CLI caller yet)."""
    fixed = fix_report.get("fixed", [])
    rolled_back = fix_report.get("rolled_back", [])
    fixits = fix_report.get("fixits", [])
    lines = [
        f"## Fix summary  fixed={len(fixed)}  rolled_back={len(rolled_back)}  "
        f"fix-its={len(fixits)}"
    ]
    for f in fixed:
        lines.append(f"  fixed  [{f['rule']}] {f['file']}:{f['line']}  {f['detail']}")
    for r in rolled_back:
        lines.append(
            f"  rolled back  [{r['rule']}] {r['file']}:{r['line']}  "
            f"{r['regression_detail']}"
        )
    for fi in fixits:
        lines.append(f"  fix-it  [{fi['rule']}] {fi['file']}:{fi['line']}")
    return "\n".join(lines)


def _run_auto_detected_stages(
    cfg: AppConfig, root: Path, *, progress: Progress | None = None, total: int = 0
) -> CheckResult:
    """`check_type` unset: run every detected project-type stage
    (`_run_all_detected`), logging which ones on a polyglot repo (T-0229)."""
    detected = _detected_types(root) or [detect_project_type(root)]
    if len(detected) > 1:
        _log.info(
            "polyglot repo: running every detected stage (%s) -- "
            "pin check_type in frob.toml or pass --type to run "
            "just one",
            "/".join(detected),
        )
    return _run_all_detected(cfg, root, detected, progress=progress, total=total)


def _run_pinned_stage(
    cfg: AppConfig, root: Path, *, progress: Progress | None = None, total: int = 0
) -> CheckResult:
    """`check_type` pinned: run just that stage, appending a `SKIPPED: ...`
    note (T-0022) for every other detected language on a polyglot repo."""
    assert cfg.check_type is not None  # narrows for the type checker; caller-guaranteed
    project_type = cfg.check_type
    others = [t for t in _detected_types(root) if t != project_type]
    # frob:ticket T-0022
    _warn_if_polyglot(root, project_type, others)
    if progress is not None:
        progress.update(f"check: {project_type}", 0, total)
    result = _dispatch_check(cfg, root, project_type)
    if progress is not None:
        progress.update(f"check: {project_type}", 1, total)
    if others:
        result = CheckResult(
            path=result.path,
            results=[
                *result.results,
                *(_skip_note_result(lang, project_type) for lang in others),
            ],
        )
    return result


# frob:ticket T-0419
def _append_deploy_stages(
    root: Path,
    result: CheckResult,
    *,
    progress: Progress | None = None,
    base: int = 0,
    total: int = 0,
) -> CheckResult:
    """Fold the opt-in `deploy-drift`/`deploy-conformance`/`claude-config-
    drift` stages (each `None` when its own opt-in condition is absent)
    onto `result`.

    `progress`/`base`/`total` (T-0419) advance the same live task-list
    `_run_all_detected` feeds, continuing its count rather than restarting
    at zero, so these stages read as the tail of one list, not a second
    one."""
    if progress is not None:
        progress.update("check: deploy-drift", base, total)
    deploy_result = _deploy_drift_result(root)
    if deploy_result is not None:
        result = CheckResult(path=result.path, results=[*result.results, deploy_result])
    if progress is not None:
        progress.update("check: deploy-conformance", base + 1, total)
    deploy_conform_result = _deploy_conformance_result(root)
    if deploy_conform_result is not None:
        result = CheckResult(
            path=result.path,
            results=[*result.results, deploy_conform_result],
        )
    n_deploy_actual = 2 if (root / "deploy").is_dir() else 0
    if progress is not None:
        progress.update("check: claude-config-drift", base + n_deploy_actual, total)
    # frob:ticket T-1809
    claude_result = _claude_config_drift_result(root)
    if claude_result is not None:
        result = CheckResult(path=result.path, results=[*result.results, claude_result])
    if progress is not None:
        progress.update("check: done", total, total)
    return result


# frob:ticket T-0627
#: The environment variable (T-0574) marking a shell as a dispatched
#: agent's, not a human/coordinator's -- `_refuse_full_check_for_agent`
#: reads it to decide whether a bare `frob check` must refuse.
_FROB_AGENT_ENV = "FROB_AGENT"

#: Override env var: set to `"1"` to run a full/unchunked `frob check`
#: from a `FROB_AGENT`-flagged shell anyway (T-0627), for the rare case a
#: coordinator deliberately wants the full run from such a shell.
_FROB_ALLOW_FULL_CHECK_ENV = "FROB_ALLOW_FULL_CHECK"


# frob:ticket T-0627
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_bare_check_refuses_under_frob_agent  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_stage_selected_check_runs_under_frob_agent  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckAgentRefusal.test_allow_full_check_override_bypasses_refusal  # noqa: E501
def _refuse_full_check_for_agent(cfg: AppConfig) -> bool:
    """True when a full, unchunked `frob check` must refuse under `FROB_AGENT` (T-0627).

    A full check/gates pass on this repo measures well past the ~120s
    agent foreground cap (playbook 3b) -- a dispatched sub-agent running a
    bare `frob check` walks straight into the harness auto-backgrounding
    the command and then stalls forever waiting on a notification that can
    never reach it (4+ occurrences in one session per T-0627's field
    evidence). When `_FROB_AGENT_ENV` is set in the environment, a bare
    invocation (no `--only` stage selection, and not one of the fast
    `--stamp-coverage`/`--stamp-baseline` exit-early modes `run` already
    short-circuits on) now refuses instead of walking into the stall --
    fail closed, not rarely-stall. `_FROB_ALLOW_FULL_CHECK_ENV=1` opts a
    specific invocation back into the full run, for the rare case a
    human/coordinator genuinely wants it from a `FROB_AGENT`-flagged shell.
    """
    # frob:waive SEC110 reason="worktree-agent detection flag, not a secret"
    if not os.environ.get(_FROB_AGENT_ENV):
        return False
    # frob:waive SEC110 reason="opt-in escape-hatch flag, not a secret"
    if os.environ.get(_FROB_ALLOW_FULL_CHECK_ENV) == "1":
        return False
    if cfg.check_only:
        return False
    if cfg.check_stamp_coverage or cfg.check_stamp_baseline:
        return False
    return True


# frob:ticket T-0627
def _refuse_full_check_message() -> str:
    """The refusal text `run` logs for `_refuse_full_check_for_agent` (T-0627):
    names the chunked `--only <stage>` loop as the sanctioned replacement,
    per `docs/guides/agent-playbook.md` section 3b/6."""
    stages = ", ".join(_stage_group_names())
    return (
        "frob check: refusing a full/unchunked run under FROB_AGENT (T-0627) -- "
        "a full pass on this repo exceeds the ~120s agent foreground cap and "
        "auto-backgrounds, stalling a dispatched sub-agent forever waiting on "
        "a notification that can never arrive. Run the chunked loop instead: "
        "for s in $(uv run frob check --only list); do uv run frob check "
        f'--only "$s"; done -- stage groups: {stages}. '
        "Set FROB_ALLOW_FULL_CHECK=1 to override deliberately."
    )


# frob:ticket T-0627
def _stage_group_names() -> list[str]:
    """`frob.check.available_stages()`, imported lazily like this module's
    other `frob.check`/`frob.gates` call-sites (T-0627)."""
    from frob.check import available_stages

    return available_stages()


# frob:ticket T-0627
# frob:tests \
# tests/system/test_cli_check.py::TestCheckStageGroups.test_only_list_prints_stage_names
def _print_stage_list(cfg: AppConfig) -> None:
    """`frob check --only list`: print every `--only` stage-group alias and
    exit without running any stage (T-0627) -- the discovery step the
    sanctioned chunked agent loop
    (`for s in $(frob check --only list); do frob check --only "$s"; done`)
    drives off of.

    Text mode prints exactly one stage name per line and nothing else
    (no header/prose) so the output is directly `$(...)`-splittable by a
    shell `for` loop without picking up stray words; `--json` wraps the
    same names in `{"stages": [...]}` for a machine caller that wants
    structure instead.
    """
    stages = _stage_group_names()
    if cfg.check_json:
        import json

        _log.info(json.dumps({"stages": stages}, indent=2))
    else:
        renderer = Renderer.for_stream(sys.stdout)
        renderer.line("\n".join(stages))


# frob:ticket T-1556
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_read_only_invocation_skips_the_lease_check kind="integration"  # noqa: E501
def _check_is_mutating(cfg: AppConfig) -> bool:
    """Whether this `frob check` invocation writes lease-protected worktree
    state (T-1556): `--stamp-baseline`/`--stamp-coverage` are the two flags
    that persist a new `.frob/baseline` or `frob-coverage.lock.json` --
    the state `ticket_lease_pin`'s cross-worktree pin actually exists to
    protect from a concurrent collision (see that function's own T-1556
    docstring section). Every other `frob check --ticket ...` shape (a
    plain gate read, `--only`, `--budget`, `--land-parity`) reads and
    reports without writing any of that, so it is not mutating and does
    not need a pinned lease to run."""
    return bool(cfg.check_stamp_baseline or cfg.check_stamp_coverage)


# frob:ticket T-0787
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_pins_to_own_worktree_lease kind="integration"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_refuses_when_lease_recorded_for_another_worktree kind="integration"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_read_only_invocation_skips_the_lease_check kind="integration"  # noqa: E501
def _refuse_ticket_lease_mismatch(root: Path, cfg: AppConfig) -> bool:
    """True (after logging a loud, `frob ticket start`-naming refusal) when
    `--ticket`/branch-derived ticket resolution does not pin to `root`'s own
    cross-worktree lease (T-0787).

    Wires `frob.gates.active_ticket` (the same `--ticket`-or-branch
    resolution `run_gates` itself uses) together with the new
    `frob.gates.ticket_lease_pin` (which wraps T-0766's `resolve_lease`) at
    the CLI boundary, before any stage or `run_gates` call -- the earliest
    point that can refuse loudly instead of letting a later gate silently
    run against the wrong worktree's ticket the way the T-0695 incident did.

    No active ticket resolves (`active_ticket` returns `Nothing` -- no
    `--ticket` and no ticket-prefixed branch) short-circuits to `False`
    immediately: this check only ever applies once a ticket id is in play.
    `ticket_lease_pin` itself is what keeps the no-lease-mechanism-engaged
    paths (plain repos, non-agent invocations of a repo where no ticket has
    ever been `frob ticket start`ed) working unchanged -- this function just
    surfaces its `Err` loudly at the CLI boundary when it does fire.

    T-1556: passes `mutating=` through to `ticket_lease_pin` based on
    `_check_is_mutating(cfg)` -- a plain read (`frob check --ticket` with
    neither `--stamp-baseline` nor `--stamp-coverage`) writes no lease-
    protected worktree state at all, so it no longer needs a pinned lease
    to run. Reviewers repeatedly could not re-verify a ticket's gate claims
    with `frob check --ticket` for exactly this reason (cli-hygiene.md
    Principle-adjacent papercut, this ticket's own acceptance criterion 1)."""
    from frob.gates import active_ticket, ticket_lease_pin

    ticket_opt = active_ticket(root, cfg.check_ticket)
    if ticket_opt.is_nothing:
        return False
    ticket_id = ticket_opt.danger_some
    pin_result = ticket_lease_pin(root, ticket_id, mutating=_check_is_mutating(cfg))
    if pin_result.is_ok:
        return False
    _log.error(
        "frob check: %s has no valid cross-worktree lease pinned to %s "
        "(%s) -- run: frob ticket start %s",
        ticket_id,
        root,
        pin_result.danger_err.value,
        ticket_id,
    )
    return True


# frob:ticket T-1004
# frob:ticket T-1535
def _handle_early_exit_modes(root: Path, cfg: AppConfig) -> bool:
    """`--only list`, `--budget SECONDS`, and `--land-parity` all exit `run`
    immediately without the normal full/`--only` dispatch below (T-1004:
    pulled out of `run` itself to keep it under ARCH001's line threshold) --
    returns `True` once any has fired, so `run` can return right after."""
    if cfg.check_only == ["list"]:
        _print_stage_list(cfg)
        return True
    if cfg.check_budget is not None:
        _run_budgeted_check(root, cfg)
        return True
    if cfg.check_land_parity:
        _run_land_parity(root, cfg)
        return True
    if cfg.check_census:
        _run_census(root, cfg)
        return True
    return False


# frob:ticket T-1535
# frob:doc docs/modules/tickets-landing.md#frob-check---land-parity-t-1535
# frob:tests tests/test_ticket_work_and_land_finish.py::TestLandParityFindings.test_parity_with_the_land_sweeps_own_exemption_function kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/modules/tickets.md's --land-parity section \
# (T-1535) is a deliberate architecture doc describing this exact private CLI \
# handler's own evaluation, same T-0524/T-0529 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries -- not accidental drift onto \
# a private helper"
def _run_land_parity(root: Path, cfg: AppConfig) -> None:
    """`frob check --land-parity` (T-1535): run
    `frob.app.ticket_runner._land_cmd.land_parity_findings` against `root`
    and report -- `None` (unmeasurable) exits 1 with a loud warning
    (never a false-clean pass), an empty set exits 0 and prints a clean
    message, and a non-empty set prints every `(rule, file)` finding
    (`--json` as a `{"findings": [...]}` payload) and exits 1, mirroring
    exactly what the real land sweep would refuse on."""
    import json

    from frob.app.ticket_runner._land_cmd import land_parity_findings

    findings = land_parity_findings(root)
    if findings is None:
        _log.error(
            "frob check --land-parity: could not evaluate (spawn refused, "
            "timeout, or unparsable output) -- this is NOT proof of a "
            "clean tree, re-run to get a real answer"
        )
        sys.exit(1)
    rows = [{"rule": rule, "file": file} for rule, file in sorted(findings)]
    if cfg.check_json:
        _log.info(json.dumps({"findings": rows}, indent=2))
    elif not rows:
        _log.info(
            "frob check --land-parity: clean -- 0 unscoped error(s), "
            "matches what the land sweep would see"
        )
    else:
        _log.error(
            "frob check --land-parity: %d unscoped error(s), exactly what "
            "the land sweep would refuse on:",
            len(rows),
        )
        for rule, file in sorted(findings):
            _log.error("  %s %s", rule, file)
    sys.exit(1 if rows else 0)


# frob:ticket T-1764
# frob:doc docs/modules/app.md#frob-check---census-t-1764
# frob:tests \
# tests/test_waive_gate.py::TestCensusCli.test_census_prints_a_table_and_exits_zero
# frob:waive ARCH103 reason="T-1764: same early-exit-mode orchestrator shape as \
# _run_land_parity right above it (run gates, log an error and exit on failure, else \
# print and exit) -- the log call and the sys.exit ARE the orchestration job; the pure \
# computation already lives in census_gate_rules/_census_gate_config/_print_census"
def _run_census(root: Path, cfg: AppConfig) -> None:
    """`frob check --census` (T-1764): run every gate, unscoped, over the
    whole tree, then print `frob.gates._waive.census_gate_rules`'s
    per-rule waive-rate table and exit. A `corpus_wide=False` rule (a
    diff-scoped detector, e.g. AFFECT001/DUP001) prints `n/a (diff-
    scoped)` for its rate rather than a number computed from this single
    clean-tree snapshot -- the exact T-1763 methodological correction
    this ticket's acceptance criteria require: a diff-scoped rule's 0
    live findings on a clean tree is its EXPECTED healthy signature, not
    evidence it is dead. Exits 1 only when the gate run itself could
    not be evaluated (never on a "bad" census number -- this is a
    report, not a gate, per the ticket's explicit "not blocking yet"
    acceptance criterion)."""
    from frob.gates import run_gates as _raw_run_gates
    from frob.gates._waive import census_gate_rules

    raw = _raw_run_gates(_census_gate_config(root, cfg))
    if raw.is_err:
        _log.error("frob check --census: could not run gates: %s", raw.danger_err)
        sys.exit(1)
    report = raw.danger_ok
    rows = census_gate_rules(report.violations, report.waived)
    _print_census(rows, as_json=cfg.check_json)
    sys.exit(0)


def _census_gate_config(root: Path, cfg: AppConfig):  # noqa: ANN201
    """The full, unscoped `GateConfig` `_run_census` runs against (T-1764,
    split out so `_run_census` itself stays a plain orchestration body):
    no `--only`/`--ticket` narrowing, since a scoped run would make a
    diff-scoped rule's live count meaningless for this snapshot."""
    from frob.gates import GateConfig

    base = cfg.check_base if cfg.check_base else "main"
    return GateConfig(root=str(root), base=base)


def _print_census(rows: tuple, *, as_json: bool) -> None:
    """Pure printing half of `_run_census` (T-1764, split out to keep
    `_run_census` itself under ARCH103's per-body decision-point
    threshold): `--json` emits `rows` as a JSON array of
    `RuleCensusEntry.model_dump()`s, otherwise a fixed-width text table
    with `n/a` in place of a diff-scoped rule's (never-computed)
    waive-rate."""
    import json

    if as_json:
        _log.info(json.dumps([r.model_dump() for r in rows], indent=2))
        return
    _log.info(
        "%-14s %6s %8s %10s %6s %s", "RULE", "FIRED", "WAIVED", "RATE", "DEAD", "SCOPE"
    )
    for r in rows:
        rate_str = f"{r.waive_rate:.0%}" if r.waive_rate is not None else "n/a"
        scope_str = "corpus" if r.corpus_wide else "diff-scoped"
        _log.info(
            "%-14s %6d %8d %10s %6d %s",
            r.rule,
            r.fired,
            r.waived,
            rate_str,
            r.dead_waivers,
            scope_str,
        )


def _handle_stamp_modes(root: Path, cfg: AppConfig) -> bool:
    """Run `--stamp-coverage`/`--stamp-baseline` and return True when one
    fired, so `run` can return immediately instead of running any stage."""
    if cfg.check_stamp_coverage:
        _run_stamp_coverage(root)
        return True
    if cfg.check_stamp_baseline:
        _run_stamp_baseline(root, cfg)
        return True
    return False


def _stdout_log_ctx(cfg: AppConfig):  # noqa: ANN201
    """The stdout-logging context `run` executes every stage under (T-0202):
    forced quiet for `--json` so the payload stays clean, otherwise gated by
    `-v`/`-vv`."""
    if cfg.check_json:
        return quiet_stdout_logs()
    return stdout_log_level(_verbosity_to_level(cfg.check_verbose))


# frob:ticket T-0420
class _ColorizedLevelFormatter(logging.Formatter):
    """Wraps `base`'s formatted line in `style_warn`/`style_fail` by level
    (T-0420): the pre-summary `PII010`/`SEC110`/module-policy-auto-inject
    WARNING lines used to print as PLAIN uncolored text while the final
    pass/FAIL summary was colored -- this makes both consistent. `color`
    is resolved once by the caller (TTY-aware, `NO_COLOR`/`FORCE_COLOR`
    honored via `should_color`) and never re-checked per record, matching
    every other coloring decision in this module."""

    def __init__(self, base: logging.Formatter, *, color: bool) -> None:
        """Bind this formatter to `base` (the pre-existing formatter whose
        text it wraps) and a resolved `color` decision."""
        super().__init__()
        self._base = base
        self._color = color

    # frob:doc docs/modules/app.md#runners
    # frob:ticket T-0588
    # frob:tests tests/system/test_cli_check.py::TestCheckBadCode.test_unused_import_output_mentions_error  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_debug_passes_through_unchanged kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_info_passes_through_unchanged kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_warning_is_painted_yellow_when_color_on kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_error_is_painted_red_when_color_on kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_error_is_unpainted_when_color_off kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.test_critical_uses_the_error_branch_too kind="unit"  # noqa: E501
    def format(self, record: logging.LogRecord) -> str:
        """Format via `base`, then paint ERROR+ red / WARNING yellow when
        `color` is on; DEBUG/INFO pass through unchanged."""
        msg = self._base.format(record)
        if record.levelno >= logging.ERROR:
            return style_fail(msg, self._color)
        if record.levelno >= logging.WARNING:
            return style_warn(msg, self._color)
        return msg


# frob:ticket T-0420
def _stderr_stream_handlers() -> list[logging.StreamHandler]:
    """The root logger's `StreamHandler`s writing to `sys.stderr` -- the
    WARNING+ handler(s) `frob.logging.config.toml` splits errors/warnings
    onto, mirroring `frob.logging.quiet._stdout_stream_handlers`'s stdout
    counterpart."""
    root_logger = logging.getLogger()
    return [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
    ]


# frob:ticket T-0420
@contextlib.contextmanager
def _colorized_stderr_logs():  # noqa: ANN201
    """Wrap every stderr `StreamHandler`'s formatter in
    `_ColorizedLevelFormatter` for the duration of the block, restoring the
    original formatter after (T-0420): the ONE place `frob check` makes its
    pre-summary WARNING/ERROR log lines match the final summary's coloring,
    TTY-aware via `should_color(sys.stderr)` so a piped/non-TTY run emits
    the exact same plain text as before. `--json` runs skip this entirely
    (see `run`) since `_stdout_log_ctx`'s `quiet_stdout_logs` already
    raises the bar to WARNING there and the JSON payload must stay
    unaffected by any stderr-side change."""
    handlers = _stderr_stream_handlers()
    color = should_color(sys.stderr)
    saved = [h.formatter for h in handlers]
    for h in handlers:
        base = h.formatter or logging.Formatter()
        h.setFormatter(_ColorizedLevelFormatter(base, color=color))
    try:
        yield
    finally:
        for h, formatter in zip(handlers, saved, strict=True):
            h.setFormatter(formatter)


# frob:ticket T-0419
def _stage_total(cfg: AppConfig, root: Path) -> int:
    """The live task-list's overall stage count: one per language stage
    that will actually run, plus one each for `deploy-drift`/
    `deploy-conformance` when `deploy/` exists -- computed up front so
    `Progress.update` can report a stable `current/total`, not a count
    that grows mid-run."""
    if cfg.check_type is None:
        n_lang = len(_detected_types(root)) or 1
    else:
        n_lang = 1
    n_deploy = 2 if (root / "deploy").is_dir() else 0
    claude_hook = root / ".claude" / "hooks" / "sync-claude-config.py"
    n_claude = 1 if claude_hook.is_file() else 0
    return n_lang + n_deploy + n_claude


# frob:ticket T-0419
def _run_all_stages(
    cfg: AppConfig, root: Path, *, progress: Progress | None = None
) -> CheckResult:
    """Run the auto-detected or pinned project-type stage(s) plus the
    opt-in deploy stages, under `run`'s stdout-logging context.

    `progress` (T-0419, a no-op off a TTY) is fed the running stage label
    and `current/total` count as each stage completes -- the TTY-only live
    task list; a piped/CI run never constructs a real `Progress` at all
    (see `run`), so this parameter changes nothing there.
    """
    stack = contextlib.ExitStack()
    stack.enter_context(_stdout_log_ctx(cfg))
    # frob:ticket T-0420
    if not cfg.check_json:
        stack.enter_context(_colorized_stderr_logs())
    with stack:
        cfg = _apply_frob_toml_defaults(cfg, root)
        total = _stage_total(cfg, root)
        n_deploy = 2 if (root / "deploy").is_dir() else 0
        n_lang = total - n_deploy
        # frob:ticket T-0229
        if cfg.check_type is None:
            result = _run_auto_detected_stages(
                cfg, root, progress=progress, total=total
            )
        else:
            result = _run_pinned_stage(cfg, root, progress=progress, total=total)
        return _append_deploy_stages(
            root, result, progress=progress, base=n_lang, total=total
        )


# frob:ticket T-0419
# frob:tests tests/system/test_cli_check.py::TestCheckPolyglot.test_unpinned_polyglot_runs_python_stage  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckPolyglot.test_pinned_check_type_reports_skipped_line  # noqa: E501
# frob:tests \
# tests/system/test_cli_check.py::TestCheckCleanProject.test_clean_code_exits_zero
# frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta.test_delta_reports_only_new_violation  # noqa: E501
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """`frob check [--type T] [--json] [--stamp-coverage|--stamp-baseline]`:
    run every applicable stage (ruff/ty/arch/cycle/dup/bind/exports plus the
    opt-in deploy stages) and report combined violations, exiting 1 on any
    error.

    T-0419: on a human TTY (and never for `--json`, which must stay byte-
    stable for machine capture), a live task-list with a progress bar
    tracks the running stages and clears itself entirely once the run
    completes, leaving only the final summary `_report_check_result`
    prints -- the `Renderer`/`Progress` contract from `frob.render`
    (`Progress` is a no-op off a TTY, so this never changes non-TTY/CI
    output).
    """
    root = cfg.check_path or Path(".")

    if not root.exists():
        _log.error("path does not exist: %s", root)
        sys.exit(1)

    # frob:ticket T-0627
    # frob:ticket T-1004
    if _handle_early_exit_modes(root, cfg):
        return

    # frob:ticket T-0627
    if _refuse_full_check_for_agent(cfg):
        _log.error(_refuse_full_check_message())
        sys.exit(1)

    # frob:ticket T-0787
    # frob:ticket T-0806
    # T-0806: `_refuse_ticket_lease_mismatch` (and `_handle_stamp_modes`,
    # via `stamp_baseline`'s own gate run) can each spawn `git` through
    # `frob.gitio` before `_run_all_stages` ever enters `_stdout_log_ctx`
    # below -- their DEBUG/INFO log lines used to print to stdout
    # unguarded even under `--json`, corrupting the JSON payload (observed
    # as a `json.loads` failure on real `git ls-files`/`rev-parse` noise
    # from a tmp-dir fixture with no `.git`). Wrap both under the same
    # `quiet_stdout_logs` `--json` uses everywhere else; the reentrant
    # depth-counter (T-0125) means `_run_all_stages`'s own nested entry
    # later is a no-op, not a double-clamp.
    lease_ctx = quiet_stdout_logs() if cfg.check_json else contextlib.nullcontext()
    with lease_ctx:
        lease_mismatch = _refuse_ticket_lease_mismatch(root, cfg)
        stamp_mode_ran = False if lease_mismatch else _handle_stamp_modes(root, cfg)
    if lease_mismatch:
        sys.exit(1)
    if stamp_mode_ran:
        return

    if cfg.check_json and _try_check_delta_via_daemon(root, cfg):
        return
    _run_stages_and_report(cfg, root)


# frob:ticket T-1260
def _run_stages_and_report(cfg: AppConfig, root: Path) -> None:
    """`run`'s stage-dispatch tail, split out to keep `run` itself under
    ARCH001's function-length ceiling (T-1260): run every applicable stage,
    apply `--fix`'s Tier-A pass when requested, then report."""
    if cfg.check_json:
        result = _run_all_stages(cfg, root)
    else:
        renderer = Renderer.for_stream(sys.stdout)
        with renderer.write.progress("frob check") as progress:
            result = _run_all_stages(cfg, root, progress=progress)
    fix_report = None
    if cfg.check_fix:
        result, fix_report = _apply_tier_a_and_reverify(cfg, root, result)
    _report_check_result(cfg, result, fix_report=fix_report)


# frob:ticket T-1260
# frob:ticket T-1481
def _apply_tier_a_and_reverify(
    cfg: AppConfig, root: Path, result: CheckResult
) -> tuple[CheckResult, dict]:
    """`frob check --fix`: apply every registered Tier-A auto-fix
    (`frob.gates._fix_engine.apply_tier_a_fixes`, T-1138/T-1177) and every
    Tier-B apply-verify-commit-or-rollback fix (`frob.gates.
    _fix_engine_tier_b.apply_tier_b_fixes`, T-1262), then re-run the gates
    stage ONCE so `result` reflects the post-fix state, then run every
    registered Tier-C emitter (`frob.gates._fix_engine_tier_c.
    apply_tier_c_fixits`, T-1263) over the POST-fix violation set --
    T-1260/T-1481's CLI wiring of all three engines. Returns
    `(updated_result, fix_report)`: `fix_report` always carries `"fixed"`/
    `"rolled_back"`/`"fixits"` keys, never a missing key, so `--fix --json`
    output shape never depends on whether anything was actually
    fixed/rolled-back/fixit-emitted this run.

    Absolute design constraints (docs/design/check-fix-engine.md): this
    never writes a `frob:waive` directive, never touches `frob.toml` or
    ratchet state, and applies nothing but the registered Tier-A/B/C
    tables those three engines themselves call -- this function is a thin
    CLI-facing wrapper, it does not add any fix logic of its own.
    """
    from frob.app._snapshot import load_or_build_snapshot
    from frob.check._python import _run_gates
    from frob.gates import GateConfig
    from frob.gates import run_gates as _raw_run_gates
    from frob.gates._fix_engine import apply_tier_a_fixes
    from frob.gates._fix_engine_tier_b import apply_tier_b_fixes
    from frob.gates._fix_engine_tier_c import apply_tier_c_fixits
    from frob.tickets import TicketQueue, load_queue

    snapshot = load_or_build_snapshot(root, log_context="check-fix")
    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.warning(
            "check --fix: ticket queue unavailable (%s) -- the TICK002 "
            "renumber handler was skipped this run; every other Tier-A "
            "handler still ran",
            queue_result.danger_err,
        )
        queue = TicketQueue(tickets={})
    else:
        queue = queue_result.danger_ok

    applied_a = apply_tier_a_fixes(root, snapshot, queue)
    committed_b, rolled_back_b = apply_tier_b_fixes(root, snapshot, queue)
    applied = [*applied_a, *committed_b]
    fixed_rules = sorted({f.rule for f in applied})
    fix_report: dict = {
        "fixed": [f.model_dump() for f in applied],
        "rolled_back": [r.model_dump() for r in rolled_back_b],
        "fixits": [],
    }

    updated = result
    if fixed_rules:
        rerun = _run_gates(
            root,
            ticket=cfg.check_ticket,
            base=cfg.check_base,
            gates=frozenset(),
            delta=cfg.check_delta,
        )
        rerun_results = rerun if isinstance(rerun, list) else [rerun]
        kept = [r for r in result.results if not r.tool.startswith("gate")]
        updated = CheckResult(path=result.path, results=[*kept, *rerun_results])
        fix_report["residual_by_rule"] = _residual_rule_counts(
            rerun_results, fixed_rules
        )

    # T-1481: Tier C never mutates, so it always runs over whatever the
    # gates stage reports RIGHT NOW (post Tier-A/B, if either fixed
    # anything) -- a fresh raw `run_gates` call for its `Violation` input,
    # since `_run_gates`'s own `ToolResult`/`Diagnostic` shape (used for
    # the rerun above) has no `Violation.rule`-keyed model `TIER_C_
    # EMITTERS` can dispatch on. Tier-C rule ids never overlap Tier-A/B's
    # by construction (T-1264's `FixabilityConflict` enforces this
    # mechanically once it lands), so this is independent of what was
    # fixed/rolled-back above.
    gate_cfg = GateConfig(
        root=str(root),
        base=cfg.check_base or "main",
        ticket=cfg.check_ticket,
        gates=frozenset(),
    )
    raw = _raw_run_gates(gate_cfg)
    if raw.is_ok:
        fixits = apply_tier_c_fixits(root, snapshot, raw.danger_ok.violations)
        fix_report["fixits"] = [f.model_dump() for f in fixits]
    return updated, fix_report


def _residual_rule_counts(
    rerun_results: list, fixed_rules: list[str]
) -> dict[str, int]:
    """How many diagnostics with each of `fixed_rules`'s rule ids remain
    across `rerun_results` -- the "affected rule re-verified clean"
    evidence `_apply_tier_a_and_reverify`'s `fix_report` carries (a `0`
    here for a given rule id is exactly what "re-verified clean" means)."""
    counts = {rule: 0 for rule in fixed_rules}
    for r in rerun_results:
        for d in r.diagnostics:
            if d.code in counts:
                counts[d.code] += 1
    return counts


# frob:ticket T-1147
def _check_delta_daemon_eligible(root: Path, cfg: AppConfig) -> bool:
    """T-1147/T-1162: pure decision -- True only for the one narrow `frob
    check --only gates --delta --json` invocation shape (exactly `--only
    gates`, no other tool stage or individual gate id mixed in, a single
    detected project language of python only with no polyglot SKIPPED-line
    siblings, no `deploy/` stage to append, and `--delta` itself set) where
    the daemon's narrower gates-only RPC answer is already the complete
    answer; see `_try_check_delta_via_daemon`'s docstring for the full
    rationale this gate exists to encode."""
    if cfg.check_only != ["gates"] or not cfg.check_delta:
        return False
    if (root / "deploy").is_dir():
        return False
    detected = _detected_types(root) or [detect_project_type(root)]
    return detected == ["python"]


# frob:ticket T-1162
def _query_check_delta_daemon(root: Path, cfg: AppConfig) -> dict | None:
    """T-1162: pure I/O -- ask the daemon proxy for `frob_check_delta` and
    return its raw `check_result` payload, or `None` on any miss (RPC
    error, or an older pre-T-1147 daemon answering without a `check_result`
    key -- see `_try_check_delta_via_daemon`'s docstring for why the latter
    must fall through rather than render)."""
    from frob.app._daemon_proxy import query

    proxied = query(
        root,
        "frob_check_delta",
        {"ticket_id": cfg.check_ticket, "base": cfg.check_base or "main"},
    )
    if proxied.is_err:
        return None
    return proxied.danger_ok.get("check_result")


# frob:ticket T-1162
def _reconcile_daemon_check_result(check_result: dict, root: Path) -> dict:
    """T-1162: pure formatting -- overwrite the daemon's own echoed
    (absolute, daemon-resolved) `path` with this invocation's own `root` so
    the daemon and in-process paths stay byte-identical (T-1147); the RPC's
    echo differs from the CLI's in-process `CheckResult.path` (usually the
    relative `cfg.check_path`) by resolution alone even when the underlying
    gate run is identical."""
    return {**check_result, "path": str(root)}


# frob:ticket T-1162
def _render_and_exit_on_daemon_errors(check_result: dict) -> None:
    """T-1162: pure decision/I-O split -- log the reconciled check result as
    JSON and `sys.exit(1)` if any gate diagnostic in it is error-severity,
    mirroring the in-process `_report_check_result` exit contract."""
    import json

    _log.info(json.dumps(check_result, indent=2))
    if any(
        any(d.get("severity") == "error" for d in r.get("diagnostics", []))
        for r in check_result["results"]
    ):
        sys.exit(1)


# frob:ticket T-1147
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_check_delta_gates_only_json_daemon_matches_in_process kind="unit"  # noqa: E501
def _try_check_delta_via_daemon(root: Path, cfg: AppConfig) -> bool:
    """T-1147: for the one narrow `frob check --only gates --delta --json`
    invocation shape -- exactly `--only gates` (no other tool stage or
    individual gate id mixed in), a single detected project language
    (python only, no polyglot SKIPPED-line siblings), no `deploy/` stage
    to append, and `--delta` itself set -- try `frob_check_delta`'s RPC
    (`frob.serve._tools.frob_check_delta`, T-1147's widened `check_result`
    key) via the daemon proxy before doing any local `run_gates` call.

    T-1128 wired `frob_graph_query`/`frob_doable_tickets`/
    `frob_run_touched_tests` this same way but investigated and explicitly
    did NOT wire `frob_check_delta`: that RPC answered only the
    gates-violations-delta question, a genuinely narrower shape than
    `frob check --delta --json`'s full multi-tool `CheckResult` (ruff/ty/
    arch/cycle/dup/bind/exports/gates). Reconciling the WHOLE shape would
    mean either running every non-gate tool inside the RPC too (a much
    bigger change, and a second copy of `check_runner.py`'s own dispatch
    logic living server-side) or detecting, CLI-side, the ONE invocation
    shape where the RPC's narrower gates-only answer already IS the
    complete answer -- this function is that detection, the second
    direction T-1147 investigated and chose.

    T-1162 split this into `_check_delta_daemon_eligible` (decision),
    `_query_check_delta_daemon` (I/O), `_reconcile_daemon_check_result`
    (formatting), and `_render_and_exit_on_daemon_errors` (render/exit) --
    this function is now just their composition.

    Returns `True` on a daemon hit (already rendered); `False` falls
    through to the normal in-process `_run_all_stages` path unchanged,
    same contract every other `_try_*_via_daemon` function in this
    codebase follows (T-1106/T-1128)."""
    if not _check_delta_daemon_eligible(root, cfg):
        return False

    check_result = _query_check_delta_daemon(root, cfg)
    if check_result is None:
        return False

    check_result = _reconcile_daemon_check_result(check_result, root)
    _render_and_exit_on_daemon_errors(check_result)
    return True
