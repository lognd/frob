"""CLI wiring for `frob test [--all] [--base REF] [--lang L] [--fallback MODE]`
(docs/testing.md)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"
_ALL_SENTINEL = "*"


def run(cfg: AppConfig) -> None:
    """Compute the touched set (or run everything with --all) and run the tests."""
    from frob.gitio import repo_root, working_diff
    from frob.graph import build_graph, load_graph
    from frob.testing import (
        SelectConfig,
        load_runners,
        run_selected,
        select_tests,
    )

    start = (cfg.test_path or Path(".")).resolve()
    root_result = repo_root(start)
    if root_result.is_err:
        _log.error("frob test: %s", root_result.danger_err)
        sys.exit(1)
    root = root_result.danger_ok

    base = cfg.test_base or "main"

    runners_result = load_runners(root)
    if runners_result.is_err:
        _log.error("frob test: could not load runners: %s", runners_result.danger_err)
        sys.exit(1)
    runners = runners_result.danger_ok
    if cfg.test_lang:
        runners = tuple(r for r in runners if r.language in cfg.test_lang)

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("frob test: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.error("frob test: graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    snapshot = loaded.danger_ok

    if cfg.test_all:
        selected = {spec.language: (_ALL_SENTINEL,) for spec in runners}
        from frob.testing._models import SelectionReport

        report = SelectionReport(
            touched=(),
            selected=selected,
            ripple=(),
            unbound=(),
            fallback="all",
        )
    else:
        diff_result = working_diff(root, base)
        if diff_result.is_err:
            _log.error("frob test: %s", diff_result.danger_err)
            sys.exit(1)
        diff = diff_result.danger_ok
        select_cfg = SelectConfig(fallback=cfg.test_fallback or "package")
        report = select_tests(snapshot, diff, select_cfg)
        if cfg.test_lang:
            report = report.model_copy(
                update={
                    "selected": {
                        lang: ids
                        for lang, ids in report.selected.items()
                        if lang in cfg.test_lang
                    }
                }
            )

    _log.info(
        "selection: touched=%d ripple=%d unbound=%d fallback=%s",
        len(report.touched),
        len(report.ripple),
        len(report.unbound),
        report.fallback,
    )

    any_selected = any(report.selected.values())
    if not any_selected:
        _log.info("nothing touched selects any test")
        if cfg.test_json:
            _log.info(report.model_dump_json(indent=2))
        return

    run_result = run_selected(report, runners, root)
    if run_result.is_err:
        _log.error("frob test: %s", run_result.danger_err)
        sys.exit(1)
    test_run = run_result.danger_ok

    if cfg.test_json:
        _log.info(test_run.model_dump_json(indent=2))
    else:
        for outcome in test_run.outcomes:
            status = "PASS" if outcome.exit_code == 0 else "FAIL"
            _log.info(
                "[%s] %s  exit=%d  %.2fs",
                status,
                outcome.language,
                outcome.exit_code,
                outcome.duration_s,
            )
            if outcome.exit_code != 0:
                if outcome.stdout_tail:
                    _log.info(outcome.stdout_tail)
                if outcome.stderr_tail:
                    _log.info(outcome.stderr_tail)

    if not test_run.ok:
        sys.exit(1)
