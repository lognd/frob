# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/check_runner.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
from __future__ import annotations

import contextlib
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

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


def _toml_check_section_updates(cfg: AppConfig, section: dict) -> dict:
    """`check_only`/`check_skip_*` defaults from `frob.toml`'s `[check]` table."""
    updates: dict = {}
    if not cfg.check_only and isinstance(section.get("only"), list):
        updates["check_only"] = [str(s) for s in section["only"]]
    raw_skip = section.get("skip")
    skip_list: list = raw_skip if isinstance(raw_skip, list) else []
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
    )


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
    )


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
    )


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
# frob:tests tests/integration/test_interfaces.py::TestInterfaces.test_main_cli_dispatches  # noqa: E501
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
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_mode_passes_loaded_snapshot kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_mode_calls_stamp_and_returns kind="unit"  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_coverage_failure_exits_1 kind="unit"  # noqa: E501
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


# frob:ticket T-0751
def _stamp_baseline_gate_chunks() -> list[frozenset[str]]:
    """Gate-id batches `_run_stamp_baseline` runs `run_gates` over one at a
    time (T-0751), instead of one undelta'd all-gates call.

    Reuses `frob.check`'s existing `gates-fast`/`gates-native`/
    `gates-security` `--only` stage-group split (T-0627) rather than
    inventing a second grouping (NO DUPLICATION) -- those groups were
    already measured safely under the ~90s per-stage foreground budget
    individually (playbook section 3b), and `--stamp-baseline` has exactly
    the same undelta'd-full-run hazard a bare `frob check` does (measured:
    a single unchunked `--stamp-baseline` takes ~187s wall / ~172s inside
    `run_gates` alone on this repo, well past the ~120s agent foreground
    cap -- see this ticket's Done report for the raw numbers). Only pure
    gate groups are used (a group whose members are entirely gate ids, not
    `lint`/`static`'s tool names) since `--stamp-baseline` only ever
    concerns gate violations. Any gate id `_STAGE_GROUPS` does not cover
    (e.g. a newly added gate not yet slotted into a group) is appended as
    its own trailing chunk, so a `_STAGE_GROUPS` drift can under-chunk
    (leaving one gate its own slow chunk) but can never silently drop a
    gate from the stamped baseline.
    """
    from frob.check import _STAGE_GROUPS
    from frob.gates import _ALL_GATES

    chunks = [members for members in _STAGE_GROUPS.values() if members <= _ALL_GATES]
    covered: frozenset[str] = frozenset().union(*chunks) if chunks else frozenset()
    leftover = _ALL_GATES - covered
    if leftover:
        chunks.append(leftover)
    return chunks


# frob:ticket T-0751
_BASELINE_CHUNKS_REL = Path(".frob") / "baseline-chunks.json"


# frob:ticket T-0751
def _baseline_chunks_path(root: Path) -> Path:
    """Where `--stamp-baseline --only <group>`'s partial-chunk accumulator lives
    (T-0751): scratch state distinct from `.frob/baseline` itself, so
    `frob.gates.stamp_baseline` stays the sole writer of the real stamp --
    this file only ever holds not-yet-complete chunk results, and is
    deleted the moment the last expected chunk lands and the real stamp
    is written."""
    return root / _BASELINE_CHUNKS_REL


# frob:ticket T-0751
def _load_baseline_chunks(root: Path) -> dict[str, list[str]]:
    """The `--only`-keyed chunk accumulator (T-0751): `{group_name:
    [violation_json, ...]}`, or `{}` if no partial run is in flight yet or
    the file is missing/corrupt (corrupt is treated as "start over", never
    a crash -- this is disposable scratch state, not the real baseline)."""
    import json as _json

    path = _baseline_chunks_path(root)
    if not path.exists():
        return {}
    try:
        data = _json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


# frob:ticket T-0751
def _save_baseline_chunks(root: Path, chunks: dict[str, list[str]]) -> None:
    """Persist `chunks` to `_baseline_chunks_path` (T-0751), creating
    `.frob/` if this is the first chunk of a run."""
    import json as _json

    path = _baseline_chunks_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(chunks))


# frob:ticket T-0751
def _resolve_baseline_only_chunk(only: list[str]) -> frozenset[str] | None:
    """The gate-id set a `--stamp-baseline --only <name>` invocation should
    run (T-0751): `<name>` may be a `_STAGE_GROUPS` alias (`gates-fast`,
    ...) or a bare gate id; `None` means no `--only` was given (the
    all-at-once, coordinator-only path)."""
    if not only:
        return None
    from frob.check import _STAGE_GROUPS
    from frob.gates import _ALL_GATES

    expanded: set[str] = set()
    for name in only:
        expanded |= _STAGE_GROUPS.get(name, {name})
    return frozenset(expanded) & _ALL_GATES


# frob:ticket T-0970
# frob:ticket T-0972
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_baseline_mode_calls_stamp_and_returns  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_baseline_gate_error_exits_1  # noqa: E501
# frob:waive ARCH103 reason="T-0977: chunk-loop orchestrator -- runs each gate chunk, \
# logs progress, folds violations into the caller's accumulator, exits on first \
# failure; the loop/log/exit ARE the orchestration job T-0627's chunked-check design \
# assigns this function"
def _run_baseline_chunks(
    root: Path,
    cfg: AppConfig,
    chunks_to_run: list[frozenset[str]],
    accumulated: dict[str, list[str]],
) -> None:
    """Run each gate chunk in `chunks_to_run` and fold its violations into
    `accumulated` (mutated in place); exits 1 on the first gate-run failure."""
    from frob.gates import GateConfig, GateError, run_gates

    for chunk in chunks_to_run:
        gate_cfg = GateConfig(
            root=str(root),
            base=cfg.check_base or "main",
            ticket=cfg.check_ticket,
            gates=chunk,
        )
        result = run_gates(gate_cfg)
        if result.is_err:
            err = result.danger_err
            if err is GateError.QueueUnavailable:
                _log.error("stamp-baseline failed: ticket queue failed to load")
            else:
                _log.error("stamp-baseline failed: %s", err.value)
            sys.exit(1)
        report = result.danger_ok
        # frob:waive PERF004 reason="chunk is this loop's own distinct member, not a shared re-sort"  # noqa: E501
        accumulated[",".join(sorted(chunk))] = [
            v.model_dump_json() for v in report.violations
        ]
        _log.info(
            "stamp-baseline: chunk of %d gate(s) done, %d violation(s)",
            len(chunk),
            len(report.violations),
        )


# frob:ticket T-0751
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_baseline_only_chunk_records_without_stamping  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_baseline_only_chunk_completes_and_stamps  # noqa: E501
def _run_stamp_baseline(root: Path, cfg: AppConfig) -> None:
    """`frob check --stamp-baseline`: record current gate violations as `--delta`'s
    baseline.

    T-0751: a bare `--stamp-baseline` (no `--only`) still runs every gate
    chunk (`_stamp_baseline_gate_chunks`) back to back in one process --
    this remains a coordinator-only path (like `make coverage`, playbook
    section 6b), since the sum still measures past the ~120s agent
    foreground cap even though no single `run_gates` call inside it does
    (measured: ~187s wall unchunked before this ticket, ~130s summed
    across chunks after -- see this ticket's Done report). A dispatched
    agent instead passes `--only <group>` (any `_STAGE_GROUPS` alias, same
    as a normal `frob check --only`) to run and record just ONE chunk per
    CLI invocation, each safely under the cap on its own: results
    accumulate in `_baseline_chunks_path`'s scratch file across
    invocations, and the moment every gate `_stamp_baseline_gate_chunks`
    expects has been recorded, the real `.frob/baseline` is (re)stamped
    from their union and the scratch file is deleted -- so N separate
    `--only`-scoped calls converge on exactly the same baseline the old
    one-shot call used to produce, without any single call approaching
    the cap.
    """
    from frob.gates import Violation, stamp_baseline

    only_gates = _resolve_baseline_only_chunk(cfg.check_only)
    expected_chunks = _stamp_baseline_gate_chunks()
    chunks_to_run = [only_gates] if only_gates is not None else expected_chunks

    accumulated = _load_baseline_chunks(root) if only_gates is not None else {}
    _run_baseline_chunks(root, cfg, chunks_to_run, accumulated)

    if only_gates is not None:
        covered: frozenset[str] = frozenset().union(
            *(frozenset(key.split(",")) if key else frozenset() for key in accumulated)
        )
        expected_union: frozenset[str] = frozenset().union(*expected_chunks)
        if covered < expected_union:
            _save_baseline_chunks(root, accumulated)
            _log.info(
                "stamp-baseline: chunk recorded (%d/%d gate(s) covered so far) -- "
                "run the remaining --only group(s) before the baseline is (re)stamped",
                len(covered),
                len(expected_union),
            )
            return

    all_violations = [
        Violation.model_validate_json(raw)
        for values in accumulated.values()
        for raw in values
    ]
    stamp_result = stamp_baseline(root, tuple(all_violations))
    if stamp_result.is_err:
        _log.error("stamp-baseline failed: %s", stamp_result.danger_err)
        sys.exit(1)
    chunks_path = _baseline_chunks_path(root)
    if chunks_path.exists():
        chunks_path.unlink()
    _log.info("baseline stamp written: %d violation(s)", len(all_violations))


# frob:ticket T-1004
#: Seconds assumed for a stage group `--budget` has never measured yet
#: (first run, or a group added to `_STAGE_GROUPS` since the last
#: measurement) -- the playbook's own "~90s per-stage budget" target
#: (agent-playbook.md section 3b), so an unmeasured group is treated as
#: "roughly at the per-stage cap" rather than free or infinite.
_BUDGET_DEFAULT_ESTIMATE_S = 90.0

#: Exponential-moving-average weight `_update_budget_timing` gives the
#: newest measurement (T-1004): 0.5 means the last two runs dominate the
#: estimate, so a stage group that has genuinely gotten slower/faster
#: (new gate added, tree grown) is reflected within a couple of budgeted
#: runs instead of being dragged out by a long history.
_BUDGET_TIMING_EMA_ALPHA = 0.5

# frob:ticket T-1004
_BUDGET_TIMING_REL = Path(".frob") / "check-budget-timing.json"

# frob:ticket T-1004
_BUDGET_STATE_REL = Path(".frob") / "check-budget-state.json"


# frob:ticket T-1004
def _budget_timing_path(root: Path) -> Path:
    """Where `--budget`'s rolling per-stage-group timing estimate lives
    (T-1004): `{group_name: estimated_seconds}`, updated after every stage
    group `--budget` actually runs."""
    return root / _BUDGET_TIMING_REL


# frob:ticket T-1004
def _budget_state_path(root: Path) -> Path:
    """Where `--budget`'s resume state lives (T-1004): the ordered list of
    stage group names not yet run from the most recent budgeted pass, so
    the next `--budget` invocation continues instead of restarting from
    the top every time."""
    return root / _BUDGET_STATE_REL


# frob:ticket T-1004
def _load_budget_timing(root: Path) -> dict[str, float]:
    """The persisted `{group: seconds}` estimate map (T-1004), or `{}` if
    no measurement has ever been recorded or the file is missing/corrupt
    (corrupt is "start over with defaults", never a crash -- this is a
    disposable performance hint, not the real gate state)."""
    import json as _json

    path = _budget_timing_path(root)
    if not path.exists():
        return {}
    try:
        data = _json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


# frob:ticket T-1004
def _save_budget_timing(root: Path, timing: dict[str, float]) -> None:
    """Persist `timing` to `_budget_timing_path`, creating `.frob/` if this
    is the first budgeted run in this checkout."""
    import json as _json

    path = _budget_timing_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(timing))


# frob:ticket T-1004
def _update_budget_timing(
    timing: dict[str, float], group: str, elapsed_s: float
) -> dict[str, float]:
    """Fold one fresh `group` measurement into `timing` via an EMA
    (`_BUDGET_TIMING_EMA_ALPHA`), returning a new dict (does not mutate
    `timing` in place, so a caller can compare before/after if it wants
    to)."""
    updated = dict(timing)
    prior = updated.get(group)
    if prior is None:
        updated[group] = elapsed_s
    else:
        alpha = _BUDGET_TIMING_EMA_ALPHA
        updated[group] = (alpha * elapsed_s) + ((1.0 - alpha) * prior)
    return updated


# frob:ticket T-1004
def _load_budget_remaining(root: Path) -> list[str] | None:
    """The resume list from a prior truncated `--budget` run (T-1004), or
    `None` if there is no resume state (a fresh start, or the last run
    completed every stage group)."""
    import json as _json

    path = _budget_state_path(root)
    if not path.exists():
        return None
    try:
        data = _json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        return None
    return data


# frob:ticket T-1004
def _save_budget_remaining(root: Path, remaining: list[str]) -> None:
    """Persist `remaining` (the stage groups a `--budget` run deferred) as
    the resume state the next `--budget` invocation continues from."""
    import json as _json

    path = _budget_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(remaining))


# frob:ticket T-1004
def _clear_budget_remaining(root: Path) -> None:
    """Delete the resume-state file (T-1004): every stage group the last
    `--budget` run considered has now been run, so there is nothing left
    to continue from."""
    path = _budget_state_path(root)
    if path.exists():
        path.unlink()


# frob:ticket T-1004
# frob:tests tests/unit/test_check_budget.py::TestSelectBudgetChunks.test_greedy_pack_fits_under_budget  # noqa: E501
# frob:tests tests/unit/test_check_budget.py::TestSelectBudgetChunks.test_first_stage_always_selected_even_if_over_budget  # noqa: E501
def _select_budget_chunks(
    remaining: list[str], timing: dict[str, float], budget_s: int
) -> tuple[list[str], list[str]]:
    """Greedily split `remaining` into `(selected, deferred)` so the summed
    estimated cost of `selected` fits `budget_s` (T-1004).

    Uses `timing.get(group, _BUDGET_DEFAULT_ESTIMATE_S)` per group and
    walks `remaining` in order, adding a group while the running total
    (including it) stays `<= budget_s`. The FIRST group is always
    selected even if its own estimate alone exceeds `budget_s` --
    guarantees every `--budget` invocation makes forward progress instead
    of a too-small budget selecting nothing and silently spinning
    forever."""
    selected: list[str] = []
    total = 0.0
    for i, group in enumerate(remaining):
        estimate = timing.get(group, _BUDGET_DEFAULT_ESTIMATE_S)
        if i == 0:
            selected.append(group)
            total += estimate
            continue
        if total + estimate <= budget_s:
            selected.append(group)
            total += estimate
        else:
            break
    deferred = remaining[len(selected) :]
    return selected, deferred


# frob:ticket T-1004
def _run_budget_chunk(
    cfg: AppConfig, root: Path, group: str
) -> tuple[CheckResult, float]:
    """Run one stage `group` (a `--only` group name) exactly like a normal
    `--only <group>` invocation would, returning `(result, elapsed_s)`
    (T-1004) so the caller can fold both the `CheckResult` and the fresh
    timing measurement into its own accumulators."""
    import time

    chunk_cfg = cfg.model_copy(update={"check_only": [group], "check_budget": None})
    start = time.monotonic()
    result = _run_all_stages(chunk_cfg, root)
    elapsed = time.monotonic() - start
    return result, elapsed


# frob:ticket T-1004
def _budget_deferred_result(deferred: list[str], budget_s: int) -> ToolResult:
    """A visible (WARNING-severity, never silent) `ToolResult` naming every
    stage group `--budget` did NOT get to this run (T-1004) -- deferring
    work is fine, deferring it quietly is the exact stall class this
    ticket exists to remove."""
    names = ", ".join(deferred)
    message = (
        f"BUDGET001: --budget {budget_s} deferred {len(deferred)} stage "
        f"group(s) to a later run: {names}. Resume state persisted -- "
        "run `frob check --budget <seconds>` again to continue."
    )
    return ToolResult(
        tool="budget",
        exit_code=0,
        summary=f"deferred {len(deferred)} stage group(s): {names}",
        diagnostics=[Diagnostic(severity="warning", code="BUDGET001", message=message)],
    )


# frob:ticket T-1004
# frob:tests tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_runs_selected_chunks_and_reports_result  # noqa: E501
# frob:tests tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_persists_resume_state_for_deferred_groups  # noqa: E501
# frob:tests tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_resumes_from_prior_remaining_state  # noqa: E501
# frob:tests tests/unit/test_check_budget.py::TestRunBudgetedCheck.test_clears_resume_state_once_every_group_has_run  # noqa: E501
def _run_budgeted_check(root: Path, cfg: AppConfig) -> None:
    """`frob check --budget SECONDS`: self-select and order `--only` stage
    groups to fit inside `SECONDS`, run exactly that subset, persist
    resume state for whatever was deferred, and report the deferral
    loudly (T-1004).

    Reuses `frob.check.available_stages()` (the same 5 groups the
    playbook's manual chunked `--only` loop iterates) as the chunk
    universe -- NO DUPLICATION of a second grouping. Resume state
    (`_budget_state_path`) carries forward across invocations: a second
    `--budget` call continues from where the first left off rather than
    restarting the same already-run groups. Timing estimates
    (`_budget_timing_path`) are a rolling EMA seeded from real measured
    wall time of each chunk actually run, persisted immediately after
    each chunk so a mid-run crash still keeps whatever it measured.
    """
    from frob.check import available_stages

    # narrows for the type checker; caller-guaranteed by `run`'s `is not None` check
    assert cfg.check_budget is not None
    budget_s = cfg.check_budget

    remaining = _load_budget_remaining(root)
    if remaining is None:
        remaining = available_stages()
    # A resume file can go stale relative to `available_stages()` (a group
    # renamed/removed since it was written) -- drop anything no longer
    # recognized rather than trying to run a stage that does not exist.
    known = set(available_stages())
    remaining = [g for g in remaining if g in known]
    if not remaining:
        remaining = available_stages()

    timing = _load_budget_timing(root)
    selected, deferred = _select_budget_chunks(remaining, timing, budget_s)

    _log.info(
        "check --budget %d: running %d stage group(s) (%s), deferring %d (%s)",
        budget_s,
        len(selected),
        ", ".join(selected),
        len(deferred),
        ", ".join(deferred) if deferred else "none",
    )

    all_results: list[ToolResult] = []
    for group in selected:
        chunk_result, elapsed = _run_budget_chunk(cfg, root, group)
        all_results.extend(chunk_result.results)
        timing = _update_budget_timing(timing, group, elapsed)
        _save_budget_timing(root, timing)
        _log.info("check --budget: stage group %r done in %.1fs", group, elapsed)

    if deferred:
        all_results.append(_budget_deferred_result(deferred, budget_s))
        _save_budget_remaining(root, deferred)
    else:
        _clear_budget_remaining(root)

    result = CheckResult(path=str(root), results=all_results)
    _report_check_result(cfg, result)


# frob:ticket T-0563
def _report_check_result(cfg: AppConfig, result) -> None:  # noqa: ANN001
    """Emit `result` as JSON or colorized text per `cfg`, then exit 1 on errors.

    T-0563: routed through `frob.render`/`_log.info` instead of a bare
    `print`, matching every other runner (RENDER001 forbids bare stdout
    writes everywhere, including the `--json` escape hatch). `_report_
    check_result` runs after `_run_all_stages`'s `_stdout_log_ctx` has
    already restored the stdout handler to its pre-stage level (T-0202),
    so this is not gated by `-v`/`--json`-forced-quiet the way per-stage
    diagnostics are -- the summary/violations table always appears.
    """
    if cfg.check_json:
        _log.info(result.as_json())
    else:
        from frob.logging.color import should_color

        renderer = Renderer.for_stream(sys.stdout)
        renderer.line(result.as_text(color=should_color(sys.stdout)))

    if result.total_errors > 0:
        sys.exit(1)


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
    """Fold the opt-in `deploy-drift`/`deploy-conformance` stages (each
    `None` when `deploy/` is absent) onto `result`.

    `progress`/`base`/`total` (T-0419) advance the same live task-list
    `_run_all_detected` feeds, continuing its count rather than restarting
    at zero, so the deploy stages read as the tail of one list, not a
    second one."""
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
# frob:tests tests/system/test_cli_check.py::TestCheckStageGroups.test_only_list_prints_stage_names  # noqa: E501
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


# frob:ticket T-0787
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_pins_to_own_worktree_lease kind="integration"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestCheckTicketLeaseCli.test_refuses_when_lease_recorded_for_another_worktree kind="integration"  # noqa: E501
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
    """
    from frob.gates import active_ticket, ticket_lease_pin

    ticket_opt = active_ticket(root, cfg.check_ticket)
    if ticket_opt.is_nothing:
        return False
    ticket_id = ticket_opt.danger_some
    pin_result = ticket_lease_pin(root, ticket_id)
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
def _handle_early_exit_modes(root: Path, cfg: AppConfig) -> bool:
    """`--only list` and `--budget SECONDS` both exit `run` immediately
    without the normal full/`--only` dispatch below (T-1004: pulled out of
    `run` itself to keep it under ARCH001's line threshold) -- returns
    `True` once either has fired, so `run` can return right after."""
    if cfg.check_only == ["list"]:
        _print_stage_list(cfg)
        return True
    if cfg.check_budget is not None:
        _run_budgeted_check(root, cfg)
        return True
    return False


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
    return n_lang + n_deploy


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
# frob:tests tests/system/test_cli_check.py::TestCheckCleanProject.test_clean_code_exits_zero  # noqa: E501
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

    if cfg.check_json:
        if _try_check_delta_via_daemon(root, cfg):
            return
        result = _run_all_stages(cfg, root)
    else:
        renderer = Renderer.for_stream(sys.stdout)
        with renderer.write.progress("frob check") as progress:
            result = _run_all_stages(cfg, root, progress=progress)
    _report_check_result(cfg, result)


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
