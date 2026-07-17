from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import (
    detect_project_type,
    run_check,
    run_check_cpp,
    run_check_rust,
    run_check_ts,
)
from frob.logging import get_logger

_log = get_logger(__name__)


@contextlib.contextmanager
def _quiet_stdout_logs() -> Iterator[None]:
    """Temporarily silence INFO/DEBUG logging to stdout.

    `--json` output must be pure JSON on stdout; library modules invoked by a
    check stage (e.g. `frob.gates.run_gates`) log liberally at INFO/DEBUG per
    this project's logging convention, which would otherwise interleave with
    (and corrupt) the final JSON payload."""
    root_logger = logging.getLogger()
    stdout_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
    ]
    saved = [h.level for h in stdout_handlers]
    for h in stdout_handlers:
        h.setLevel(logging.WARNING)
    try:
        yield
    finally:
        for h, level in zip(stdout_handlers, saved, strict=True):
            h.setLevel(level)


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
    updates: dict = {}
    if cfg.check_base is None and isinstance(data.get("check_base"), str):
        updates["check_base"] = data["check_base"]
    if cfg.check_type is None and isinstance(data.get("check_type"), str):
        updates["check_type"] = data["check_type"]
    section = data.get("check", {})
    if not cfg.check_only and isinstance(section.get("only"), list):
        updates["check_only"] = [str(s) for s in section["only"]]
    skip_list = section.get("skip") if isinstance(section.get("skip"), list) else []
    for stage in skip_list:
        field = f"check_skip_{str(stage).replace('-', '_')}"
        if hasattr(cfg, field) and not getattr(cfg, field):
            updates[field] = True
    if updates:
        _log.debug("check defaults from frob.toml: %s", sorted(updates))
        return cfg.model_copy(update=updates)
    return cfg


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


def run(cfg: AppConfig) -> None:
    root = cfg.check_path or Path(".")

    if not root.exists():
        _log.error("path does not exist: %s", root)
        sys.exit(1)

    if cfg.check_stamp_coverage:
        from frob.gates import stamp_coverage

        result = stamp_coverage(root)
        if result.is_err:
            _log.error("stamp-coverage failed: %s", result.danger_err)
            sys.exit(1)
        _log.info("coverage stamp written")
        return

    _ctx = _quiet_stdout_logs() if cfg.check_json else contextlib.nullcontext()

    with _ctx:
        cfg = _apply_frob_toml_defaults(cfg, root)
        auto_detected = cfg.check_type is None
        project_type = cfg.check_type or detect_project_type(root)
        if auto_detected:
            # frob:ticket T-0022
            _warn_if_polyglot(root, project_type)
        if project_type == "cpp":
            result = run_check_cpp(
                root,
                build_dir=cfg.check_build_dir,
                skip_build=cfg.check_skip_build,
                skip_clang_tidy=cfg.check_skip_clang_tidy,
                skip_clang_format=cfg.check_skip_clang_format,
                skip_tests=cfg.check_skip_tests,
                valgrind=cfg.check_valgrind,
            )
        elif project_type == "rust":
            result = run_check_rust(
                root,
                skip_check=cfg.check_skip_cargo_check,
                skip_clippy=cfg.check_skip_clippy,
                skip_fmt=cfg.check_skip_fmt,
                skip_tests=cfg.check_skip_tests,
                valgrind=cfg.check_valgrind,
            )
        elif project_type == "typescript":
            result = run_check_ts(
                root,
                skip_tsc=cfg.check_skip_tsc,
                skip_eslint=cfg.check_skip_eslint,
                skip_prettier=cfg.check_skip_prettier,
                skip_tests=cfg.check_skip_tests,
            )
        else:
            # Python (default)
            result = run_check(
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
            )

    if cfg.check_json:
        _log.info(result.as_json())
    else:
        from frob.logging.color import should_color

        _log.info(result.as_text(color=should_color(sys.stdout)))

    if result.total_errors > 0:
        sys.exit(1)
