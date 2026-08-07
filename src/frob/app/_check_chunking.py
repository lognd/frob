"""Chunked gate-execution bookkeeping for `frob check --stamp-baseline` and
`frob check --budget` (extracted from `frob.app.check_runner` by T-1195,
LARGE001 residue split): gate-id batching, the `.frob/`-scratch
accumulator files each mode persists between individually-cheap CLI
invocations, and the two top-level entry points
(`_run_stamp_baseline`/`_run_budgeted_check`) `check_runner.run` dispatches
to (docs/commands/check.md's delta/baseline agent workflow).
"""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import CheckResult
from frob.logging import get_logger
from frob.process.parsers.common import Diagnostic, ToolResult

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


# frob:ticket T-1004
#: Seconds assumed for a stage group `--budget` has never measured yet
#: (first run, or a group added to `_STAGE_GROUPS` since the last
#: measurement) -- the playbook's own "~90s per-stage budget" target
#: (agent-playbook.md section 3b), so an unmeasured group is treated as
#: "roughly at the per-stage cap" rather than free or infinite.
# frob:ticket T-1195
_BUDGET_DEFAULT_ESTIMATE_S = 90.0

#: Exponential-moving-average weight `_update_budget_timing` gives the
#: newest measurement (T-1004): 0.5 means the last two runs dominate the
#: estimate, so a stage group that has genuinely gotten slower/faster
#: (new gate added, tree grown) is reflected within a couple of budgeted
#: runs instead of being dragged out by a long history.
# frob:ticket T-1195
_BUDGET_TIMING_EMA_ALPHA = 0.5

# frob:ticket T-1004
# frob:ticket T-1195
_BUDGET_TIMING_REL = Path(".frob") / "check-budget-timing.json"

# frob:ticket T-1004
# frob:ticket T-1195
_BUDGET_STATE_REL = Path(".frob") / "check-budget-state.json"


# frob:ticket T-1004
# frob:ticket T-1195
def _budget_timing_path(root: Path) -> Path:
    """Where `--budget`'s rolling per-stage-group timing estimate lives
    (T-1004): `{group_name: estimated_seconds}`, updated after every stage
    group `--budget` actually runs."""
    return root / _BUDGET_TIMING_REL


# frob:ticket T-1004
# frob:ticket T-1195
def _budget_state_path(root: Path) -> Path:
    """Where `--budget`'s resume state lives (T-1004): the ordered list of
    stage group names not yet run from the most recent budgeted pass, so
    the next `--budget` invocation continues instead of restarting from
    the top every time."""
    return root / _BUDGET_STATE_REL


# frob:ticket T-1004
# frob:ticket T-1195
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
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


# frob:ticket T-1004
# frob:ticket T-1195
def _save_budget_timing(root: Path, timing: dict[str, float]) -> None:
    """Persist `timing` to `_budget_timing_path`, creating `.frob/` if this
    is the first budgeted run in this checkout."""
    import json as _json

    path = _budget_timing_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(timing))


# frob:ticket T-1004
# frob:ticket T-1195
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
# frob:ticket T-1195
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
    except Exception:
        return None
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        return None
    return data


# frob:ticket T-1004
# frob:ticket T-1195
def _save_budget_remaining(root: Path, remaining: list[str]) -> None:
    """Persist `remaining` (the stage groups a `--budget` run deferred) as
    the resume state the next `--budget` invocation continues from."""
    import json as _json

    path = _budget_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(remaining))


# frob:ticket T-1004
# frob:ticket T-1195
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
# frob:ticket T-1195
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
# frob:ticket T-1195
def _run_budget_chunk(
    cfg: AppConfig, root: Path, group: str
) -> tuple[CheckResult, float]:
    """Run one stage `group` (a `--only` group name) exactly like a normal
    `--only <group>` invocation would, returning `(result, elapsed_s)`
    (T-1004) so the caller can fold both the `CheckResult` and the fresh
    timing measurement into its own accumulators."""
    import time

    from frob.app.check_runner import _run_all_stages

    chunk_cfg = cfg.model_copy(update={"check_only": [group], "check_budget": None})
    start = time.monotonic()
    result = _run_all_stages(chunk_cfg, root)
    elapsed = time.monotonic() - start
    return result, elapsed


# frob:ticket T-1004
# frob:ticket T-1195
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
# frob:ticket T-1195
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

    # T-1703: these two progress lines are the ONLY output this function
    # prints outside `_run_budget_chunk`'s own `_run_all_stages` call,
    # which enters/exits `_stdout_log_ctx` for the duration of each chunk
    # it runs (quiet under `--json`, same as every other stage). Left
    # unguarded, they printed straight to stdout ahead of the eventual
    # JSON payload `_report_check_result` emits below -- corrupting it
    # for any `json.loads` consumer (the exact leak `_unscoped_error_
    # findings`'s own `--budget ... --json` spawn, frob.app.ticket_
    # runner._land_cmd, hit in practice: `[{"tool": "gate:...", ...` with
    # this line's own prose prepended is not valid JSON). `_log.info` at
    # its own default level would otherwise reach stdout even under
    # `--json`'s later `quiet_stdout_logs` wrap in `run` -- that wrap
    # only covers the SETUP calls before `_handle_early_exit_modes`
    # dispatches here, not this function's own body.
    if not cfg.check_json:
        _log.info(
            "check --budget %d: running %d stage group(s) (%s), deferring "
            "%d (%s)",
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
        if not cfg.check_json:
            _log.info(
                "check --budget: stage group %r done in %.1fs", group, elapsed
            )

    if deferred:
        all_results.append(_budget_deferred_result(deferred, budget_s))
        _save_budget_remaining(root, deferred)
    else:
        _clear_budget_remaining(root)

    result = CheckResult(path=str(root), results=all_results)

    from frob.app.check_runner import _report_check_result

    _report_check_result(cfg, result)
