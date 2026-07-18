from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import (
    detect_project_type,
    run_check,
    run_check_cpp,
    run_check_rust,
    run_check_ts,
)
from frob.logging import get_logger, quiet_stdout_logs

_log = get_logger(__name__)


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


def _warn_if_polyglot(root: Path, chosen: str) -> None:
    """Loudly name the language stages auto-detection is about to skip.

    Cargo.toml beats pyproject.toml in detect_project_type, so a mixed repo
    silently ran ONE language's checks -- gates included -- and looked clean
    (found during the feldspar adoption, T-0022). Detection stays simple;
    the warning makes the single-stage choice impossible to miss. Pin
    check_type in frob.toml (or --type) to silence it deliberately.
    """
    sentinels = {
        "rust": (root / "Cargo.toml").exists(),
        "cpp": (root / "CMakeLists.txt").exists(),
        "python": (root / "pyproject.toml").exists() or (root / "setup.py").exists(),
        "typescript": (root / "package.json").exists(),
    }
    others = sorted(
        lang for lang, present in sentinels.items() if present and lang != chosen
    )
    if others:
        _log.warning(
            "polyglot repo: running the %s stage only; %s checks (gates "
            "included) are NOT running -- pin check_type in frob.toml or "
            "pass --type to choose deliberately",
            chosen,
            "/".join(others),
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


def _dispatch_check(cfg: AppConfig, root: Path, project_type: str):
    """Run the language-appropriate check stack for `project_type`."""
    dispatch = _DISPATCH_BY_TYPE.get(project_type, _dispatch_check_python)
    return dispatch(cfg, root)


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
    """Log `result` as JSON or colorized text per `cfg`, then exit 1 on errors."""
    if cfg.check_json:
        _log.info(result.as_json())
    else:
        from frob.logging.color import should_color

        _log.info(result.as_text(color=should_color(sys.stdout)))

    if result.total_errors > 0:
        sys.exit(1)


# frob:doc docs/modules/app.md#runners
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

    _ctx = quiet_stdout_logs() if cfg.check_json else contextlib.nullcontext()

    with _ctx:
        cfg = _apply_frob_toml_defaults(cfg, root)
        auto_detected = cfg.check_type is None
        project_type = cfg.check_type or detect_project_type(root)
        if auto_detected:
            # frob:ticket T-0022
            _warn_if_polyglot(root, project_type)
        result = _dispatch_check(cfg, root, project_type)

    _report_check_result(cfg, result)
