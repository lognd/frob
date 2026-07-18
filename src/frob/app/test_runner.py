"""CLI wiring for `frob test [--all] [--base REF] [--lang L] [--fallback MODE]`
(docs/modules/testing.md)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"
_ALL_SENTINEL = "*"


def _fuzz_models_and_digests(root: Path, snapshot, obs) -> tuple[list, dict[str, str]]:  # noqa: ANN001
    """Derived pydantic models named by `obs`'s resolved param types, plus body
    digests keyed by `module.qualname` (for `stamp_fuzz`'s drift check)."""
    from pydantic import BaseModel

    from frob.fuzz import resolve_param_types

    models: list = []
    digests: dict[str, str] = {}
    for ob in obs:
        for tp in resolve_param_types(root, ob.ref) or ():
            if isinstance(tp, type) and issubclass(tp, BaseModel):
                models.append(tp)
                rec = snapshot.symbols.get(ob.ref)
                if rec is not None:
                    digests[f"{tp.__module__}.{tp.__qualname__}"] = rec.digests.body
    return models, digests


def _print_fuzz_results(results) -> list:  # noqa: ANN001
    """Print one PASS/FALSIFIED line per fuzz result; return the falsified subset."""
    falsified = [r for r in results if r.falsified]
    for r in results:
        mark = (
            f"FALSIFIED: {r.falsified}" if r.falsified else f"{r.examples} examples ok"
        )
        print(f"  {r.ref}: {mark}")
    return falsified


# frob:ticket T-0002
def _run_fuzz(root: Path) -> None:
    """`frob test --fuzz`: property-test the pydantic models in fuzz-obligated
    signatures via the hypothesis harness, then stamp so FUZZ003 is satisfied.

    v1 drives the DERIVED pydantic-model case (docs/modules/fuzz.md); non-model
    params are reported as skipped, not failed."""
    from frob.fuzz import FuzzEnforce, FuzzPolicy, obligations, run_fuzz, stamp_fuzz
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    snapshot = (loaded if loaded.is_ok else build_graph(root, cache)).danger_ok

    obs = obligations(snapshot, FuzzPolicy(enforce=FuzzEnforce.INVARIANT_ANCHORED))
    if not obs:
        print("frob test --fuzz: no obligated targets (add frob:invariant anchors)")
        return
    models, digests = _fuzz_models_and_digests(root, snapshot, obs)
    if not models:
        print("frob test --fuzz: no derived pydantic-model params to fuzz (v1 scope)")
        return

    results = run_fuzz(tuple(models), budget_s=60, digests=digests)
    falsified = _print_fuzz_results(results)
    stamped = stamp_fuzz(root, results)
    if stamped.is_err:
        _log.error("frob test --fuzz: stamp failed: %s", stamped.danger_err)
        sys.exit(1)
    if falsified:
        sys.exit(1)


def _load_test_snapshot(root: Path):
    """Load (or rebuild) the graph snapshot, exiting on hard failure."""
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        _log.info("frob test: cache stale/missing, building: %s", loaded.danger_err)
        loaded = build_graph(root, cache)
    if loaded.is_err:
        _log.error("frob test: graph unavailable: %s", loaded.danger_err)
        sys.exit(1)
    return loaded.danger_ok


def _selection_report(cfg: AppConfig, root: Path, snapshot, runners, base: str):
    """The touched-set selection (or an all-runners selection with --all)."""
    from frob.gitio import working_diff
    from frob.testing import SelectConfig, select_tests
    from frob.testing._models import SelectionReport

    if cfg.test_all:
        selected = {spec.language: (_ALL_SENTINEL,) for spec in runners}
        return SelectionReport(
            touched=(), selected=selected, ripple=(), unbound=(), fallback="all"
        )

    diff_result = working_diff(root, base)
    if diff_result.is_err:
        _log.error("frob test: %s", diff_result.danger_err)
        sys.exit(1)
    select_cfg = SelectConfig(fallback=cfg.test_fallback or "package")
    report = select_tests(snapshot, diff_result.danger_ok, select_cfg)
    if cfg.test_lang:
        kept = {
            lang: ids for lang, ids in report.selected.items() if lang in cfg.test_lang
        }
        report = report.model_copy(update={"selected": kept})
    return report


def _print_outcomes(test_run) -> None:
    """Log a PASS/FAIL line per runner outcome, with tails on failure."""
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


def _resolve_test_root(cfg: AppConfig) -> Path:
    """The repo root `frob test` operates in, or exit(1) if not found."""
    from frob.gitio import repo_root

    start = (cfg.test_path or Path(".")).resolve()
    root_result = repo_root(start)
    if root_result.is_err:
        _log.error("frob test: %s", root_result.danger_err)
        sys.exit(1)
    return root_result.danger_ok


def _loaded_runners(cfg: AppConfig, root: Path) -> tuple:
    """`load_runners(root)`, filtered to `cfg.test_lang` and exit(1) on failure."""
    from frob.testing import load_runners

    runners_result = load_runners(root)
    if runners_result.is_err:
        _log.error("frob test: could not load runners: %s", runners_result.danger_err)
        sys.exit(1)
    runners = runners_result.danger_ok
    if cfg.test_lang:
        runners = tuple(r for r in runners if r.language in cfg.test_lang)
    return runners


def _run_selected_and_report(cfg: AppConfig, report, runners, root: Path) -> None:
    """Run the selected tests and report PASS/FAIL, exiting 1 on any failure."""
    from frob.testing import run_selected

    run_result = run_selected(report, runners, root)
    if run_result.is_err:
        _log.error("frob test: %s", run_result.danger_err)
        sys.exit(1)
    test_run = run_result.danger_ok

    if cfg.test_json:
        _log.info(test_run.model_dump_json(indent=2))
    else:
        _print_outcomes(test_run)

    if not test_run.ok:
        sys.exit(1)


def run(cfg: AppConfig) -> None:
    """Compute the touched set (or run everything with --all) and run the tests."""
    root = _resolve_test_root(cfg)

    if cfg.test_fuzz:
        _run_fuzz(root)
        return

    runners = _loaded_runners(cfg, root)
    snapshot = _load_test_snapshot(root)
    report = _selection_report(cfg, root, snapshot, runners, cfg.test_base or "main")

    _log.info(
        "selection: touched=%d ripple=%d unbound=%d fallback=%s",
        len(report.touched),
        len(report.ripple),
        len(report.unbound),
        report.fallback,
    )

    if not any(report.selected.values()):
        _log.info("nothing touched selects any test")
        if cfg.test_json:
            _log.info(report.model_dump_json(indent=2))
        return

    _run_selected_and_report(cfg, report, runners, root)
