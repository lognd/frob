from __future__ import annotations

import contextlib
import logging
import sys
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
    return not any(
        hunk.file.endswith(suffixes) for hunk in result.danger_ok.hunks
    )


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
    """Run `run_check_cpp` with `cfg`'s C++-toolchain skip flags."""
    return run_check_cpp(
        root,
        build_dir=cfg.check_build_dir,
        skip_build=cfg.check_skip_build,
        skip_clang_tidy=cfg.check_skip_clang_tidy,
        skip_clang_format=cfg.check_skip_clang_format,
        skip_tests=cfg.check_skip_tests,
        valgrind=cfg.check_valgrind,
    )


def _dispatch_check_rust(cfg: AppConfig, root: Path):
    """Run `run_check_rust` with `cfg`'s Rust-toolchain skip flags."""
    return run_check_rust(
        root,
        skip_check=cfg.check_skip_cargo_check,
        skip_clippy=cfg.check_skip_clippy,
        skip_fmt=cfg.check_skip_fmt,
        skip_tests=cfg.check_skip_tests,
        valgrind=cfg.check_valgrind,
    )


def _dispatch_check_ts(cfg: AppConfig, root: Path):
    """Run `run_check_ts` with `cfg`'s TypeScript-toolchain skip flags."""
    return run_check_ts(
        root,
        skip_tsc=cfg.check_skip_tsc,
        skip_eslint=cfg.check_skip_eslint,
        skip_prettier=cfg.check_skip_prettier,
        skip_tests=cfg.check_skip_tests,
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
}


def _dispatch_check(cfg: AppConfig, root: Path, project_type: str) -> CheckResult:
    """Run the language-appropriate check stack for `project_type`."""
    dispatch = _DISPATCH_BY_TYPE.get(project_type, _dispatch_check_python)
    return dispatch(cfg, root)


# frob:ticket T-0229
# frob:ticket T-0419
# frob:ticket T-0421
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_unchanged_python_reports_skipped_not_silent  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_changed_python_still_runs  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch6.py::TestSkipUnchangedLanguage::test_absent_language_never_shown  # noqa: E501
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
    if not (root / "deploy").is_dir():
        return None
    from frob.deploy import deploy_drift_violations

    violations = deploy_drift_violations(root)
    return _deploy_drift_tool_result(violations)


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
    too). Opt-in on `deploy/` existing; returns `None` (no stage) when the
    directory is absent."""
    if not (root / "deploy").is_dir():
        return None
    from frob.deploy import deploy_conformance_violations

    violations = deploy_conformance_violations(root)
    return _deploy_conformance_tool_result(violations)


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


def _run_stamp_coverage(root: Path) -> None:
    """`frob check --stamp-coverage`: record coverage.xml as the current stamp."""
    from frob.gates import stamp_coverage

    result = stamp_coverage(root)
    if result.is_err:
        _log.error("stamp-coverage failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("coverage stamp written")


# frob:doc docs/commands/check.md#public-api
def _run_stamp_baseline(root: Path, cfg: AppConfig) -> None:
    """`frob check --stamp-baseline`: record current gate violations as `--delta`'s
    baseline.

    Runs the gates stage (undelta'd, so the baseline captures the *current*
    full violation set, not a previously-filtered one) and hands the result
    to `frob.gates.stamp_baseline`. Mirrors `_run_stamp_coverage`'s
    run-then-exit shape (T-0107).
    """
    from frob.gates import GateConfig, GateError, run_gates, stamp_baseline

    gate_cfg = GateConfig(
        root=str(root), base=cfg.check_base or "main", ticket=cfg.check_ticket
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
    stamp_result = stamp_baseline(root, report.violations)
    if stamp_result.is_err:
        _log.error("stamp-baseline failed: %s", stamp_result.danger_err)
        sys.exit(1)
    _log.info("baseline stamp written: %d violation(s)", len(report.violations))


def _report_check_result(cfg: AppConfig, result) -> None:  # noqa: ANN001
    """Print `result` as JSON or colorized text per `cfg`, then exit 1 on errors.

    Printed directly to stdout rather than through the logger (T-0202): the
    summary/violations table is `frob check`'s actual deliverable output,
    not a diagnostic, so it must appear regardless of `-v` level or a
    caller having raised the stdout handler above INFO.
    """
    if cfg.check_json:
        print(result.as_json())
    else:
        from frob.logging.color import should_color

        print(result.as_text(color=should_color(sys.stdout)))

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
# frob:tests tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation  # noqa: E501
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

    if _handle_stamp_modes(root, cfg):
        return

    if cfg.check_json:
        result = _run_all_stages(cfg, root)
    else:
        renderer = Renderer.for_stream(sys.stdout)
        with renderer.write.progress("frob check") as progress:
            result = _run_all_stages(cfg, root, progress=progress)
    _report_check_result(cfg, result)
