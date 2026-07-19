# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"
from __future__ import annotations

import logging
import sys
from pathlib import Path

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
from frob.process.parsers.common import Diagnostic, ToolResult

#: DEPLOY001's severity literal, matching `Diagnostic.severity`'s type
#: (`frob.process.parsers.common.Severity`) without importing it just for
#: this one string -- the same pragmatic inline-literal precedent
#: `_skip_note_result` below already uses for its own diagnostic.
_DEPLOY001_SEVERITY = "error"

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
def _run_all_detected(cfg: AppConfig, root: Path, types: list[str]) -> CheckResult:
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
    """
    results: list[ToolResult] = []
    for project_type in types:
        results.extend(_dispatch_check(cfg, root, project_type).results)
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


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 0.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    root = cfg.check_path or Path(".")

    if not root.exists():
        _log.error("path does not exist: %s", root)
        sys.exit(1)

    if cfg.check_stamp_coverage:
        _run_stamp_coverage(root)
        return

    if cfg.check_stamp_baseline:
        _run_stamp_baseline(root, cfg)
        return

    # T-0202: --json always forces stdout logs quiet (payload must stay
    # clean); otherwise the stdout handler level is gated by -v/-vv so
    # default output is the summary/violations table with no log chatter.
    _ctx = (
        quiet_stdout_logs()
        if cfg.check_json
        else stdout_log_level(_verbosity_to_level(cfg.check_verbose))
    )

    with _ctx:
        cfg = _apply_frob_toml_defaults(cfg, root)
        auto_detected = cfg.check_type is None
        # frob:ticket T-0229
        if auto_detected:
            detected = _detected_types(root) or [detect_project_type(root)]
            if len(detected) > 1:
                _log.info(
                    "polyglot repo: running every detected stage (%s) -- "
                    "pin check_type in frob.toml or pass --type to run "
                    "just one",
                    "/".join(detected),
                )
            result = _run_all_detected(cfg, root, detected)
        else:
            project_type = cfg.check_type
            others = [t for t in _detected_types(root) if t != project_type]
            # frob:ticket T-0022
            _warn_if_polyglot(root, project_type, others)
            result = _dispatch_check(cfg, root, project_type)
            if others:
                result = CheckResult(
                    path=result.path,
                    results=[
                        *result.results,
                        *(_skip_note_result(lang, project_type) for lang in others),
                    ],
                )

        deploy_result = _deploy_drift_result(root)
        if deploy_result is not None:
            result = CheckResult(
                path=result.path, results=[*result.results, deploy_result]
            )

    _report_check_result(cfg, result)
