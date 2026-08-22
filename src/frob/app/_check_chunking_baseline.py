# frob:waive REF002 reason="T-2826: this module has exactly one inbound reference by \
# design -- _check_chunking.py re-exports _run_stamp_baseline (`from frob.app. \
# _check_chunking_baseline import _run_stamp_baseline`) so every existing \
# `frob.app._check_chunking.<name>` call site (check_runner.py and the test suite) \
# keeps working unchanged after this split, exactly like T-2830/T-2829's sibling \
# ticket_runner split modules re-export through their own package __init__ for the \
# identical reason. A second direct consumer would defeat the point of the re-export \
# -- external code is meant to go through _check_chunking.py, not import this module \
# directly."
"""`frob check --stamp-baseline` chunked bookkeeping (extracted from
`frob.app._check_chunking` by T-2826, LARGE001 split): gate-id batching
and the `.frob/`-scratch accumulator file `_run_stamp_baseline` persists
between individually-cheap CLI invocations.

Split out because `--stamp-baseline` and `--budget` (the sibling half
that stays in `_check_chunking.py`) are two independent CLI-flag
features with their own state files and entry points that never call
each other -- confirmed via `git grep` before splitting: every external
caller of this module (`check_runner.py`, `_land_cmd.py`,
`_rapid_sweep.py`, `_land.py`, and the test suite) imports either
`_run_stamp_baseline`/`_run_budgeted_check` (re-exported from
`_check_chunking.py` unchanged so those call sites need no edit) or one
of the BUDGET-side helpers (`_derive_post_land_sweep_budget_s`,
`_budget_timing_path`, `_load_budget_timing`) -- nothing external reaches
into this file's own baseline-chunking internals.
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0751
# frob:ticket T-1195
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
# frob:ticket T-1195
_BASELINE_CHUNKS_REL = Path(".frob") / "baseline-chunks.json"


# frob:ticket T-0751
# frob:ticket T-1195
def _baseline_chunks_path(root: Path) -> Path:
    """Where `--stamp-baseline --only <group>`'s partial-chunk accumulator lives
    (T-0751): scratch state distinct from `.frob/baseline` itself, so
    `frob.gates.stamp_baseline` stays the sole writer of the real stamp --
    this file only ever holds not-yet-complete chunk results, and is
    deleted the moment the last expected chunk lands and the real stamp
    is written."""
    return root / _BASELINE_CHUNKS_REL


# frob:ticket T-0751
# frob:ticket T-1195
# frob:invariant INV-050
# invariant spec: [INV-050](invariants/INV-050.md)
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
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


# frob:ticket T-0751
# frob:ticket T-1195
def _save_baseline_chunks(root: Path, chunks: dict[str, list[str]]) -> None:
    """Persist `chunks` to `_baseline_chunks_path` (T-0751), creating
    `.frob/` if this is the first chunk of a run."""
    import json as _json

    path = _baseline_chunks_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(chunks))


# frob:ticket T-0751
# frob:ticket T-1195
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
# frob:ticket T-1195
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
# frob:ticket T-1195
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
