# frob:ticket T-1684
# frob:waive INV006 reason="this module docstring's exclusivity wording (the sweep \
# is the only thing between a durable commit and the prompt; an already-filed error \
# must not be re-filed) describes this module's OWN implemented branching, \
# verifiable by reading the code it annotates -- not a cross-module contract needing \
# a tracked invariant, same disposition as _profile.py's identical waiver"
"""T-1684: the `rapid`-profile replacement for `_land_cmd`'s synchronous
post-land unscoped error sweep -- a DETACHED sweep that files a ticket
instead of blocking the land.

`standard`'s post-land sweep (T-1456) is synchronous and reverts an
already-made land commit when it finds new unscoped errors. That is the
right bargain when a land is rare and expensive to unwind, but it costs a
full unscoped `frob check` (measured at 2-8 minutes on this repo) on the
critical path of every single land, plus a second full check for the
T-1463 pre-land baseline. A land that takes five minutes is its own
correctness risk: the queue stops draining, and work batches up into
giant unreviewable lands.

Under `rapid` the same verification still happens -- just not while the
developer waits, and without ever rewriting published history:

- **Rolling baseline, one check instead of two.** `standard` measures a
  pre-land baseline (check #1) and a post-land set (check #2) and diffs
  them. Here the previous deferred sweep's recorded absolute error set IS
  the baseline (`.frob/rapid-sweep-baseline.json`), so a sweep costs
  exactly one check and the land itself costs zero. The first sweep in a
  repo has no stored baseline: it records one and reports nothing, the
  same "unmeasurable baseline is not zero" posture `_land_cmd`'s sweeps
  already take rather than pretending every pre-existing error is new.
- **Files, never reverts.** The land commit is already published (and,
  under rapid, other agents are landing against it concurrently) -- a
  `git reset --hard` of another agent's base is strictly worse than a
  filed bug. New `(rule_id, file)` pairs become one `bug` ticket naming
  every pair and the commit that introduced them.
- **The window is recorded, not silent.** Every deferred sweep appends a
  `rapid-debt.jsonl` line at spawn time, so "this commit landed
  unverified" is a machine-readable fact from the instant it is true --
  even if the child is killed before it ever reports.

The baseline is rewritten to the freshly measured set on EVERY sweep,
including a red one. Errors that have already been filed as a ticket must
not be re-filed by the next land; the filed ticket is the record from
then on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

#: Rolling absolute error set from the last deferred sweep. Under
#: `.frob/` (local, disposable, per-checkout) on purpose: it is a
#: measurement cache, not a record -- the RECORD is `rapid-debt.jsonl`
#: plus the filed tickets, both tracked. Losing this file costs one
#: skipped comparison, never a lost obligation.
_BASELINE_REL = Path(".frob") / "rapid-sweep-baseline.json"

#: Detached-child stdout/stderr, one file per swept ticket, so a sweep
#: that dies (OOM, reboot) leaves its partial output behind to read.
_LOG_DIR_REL = Path(".frob") / "rapid-sweep"


# frob:doc docs/modules/tickets.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:ticket T-1684
class RapidSweepError(ErrorSet):
    """Fallible outcomes of the deferred-sweep spawn and run."""

    SpawnRefused = "the detached sweep child could not be spawned"
    Unmeasurable = "the unscoped check produced no parsable error set"


def _baseline_path(root: Path) -> Path:
    """`.frob/rapid-sweep-baseline.json` for a checkout rooted at `root`."""
    return root / _BASELINE_REL


# frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_absent_baseline_reads_as_none_not_empty  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_corrupt_baseline_reads_as_none_not_empty  # noqa: E501
def _read_baseline(root: Path) -> frozenset[tuple[str, str]] | None:
    """The last recorded absolute `(rule_id, file)` error set, or `None`
    when there is no usable baseline yet (absent or corrupt file).

    `None` is deliberately NOT an empty set: comparing a fresh scan
    against an assumed-clean baseline would report every pre-existing
    error in the repo as newly introduced by this land, which is exactly
    the false alarm that makes an automated filer get ignored."""
    path = _baseline_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return frozenset((str(rule), str(file)) for rule, file in raw["findings"])
    except Exception as exc:  # noqa: BLE001 -- json/shape, any corruption
        _log.warning(
            "rapid sweep: baseline %s unreadable (%s) -- treating as NO "
            "baseline (unmeasured, not zero); this sweep records a fresh "
            "one and compares nothing",
            path,
            exc,
        )
        return None


# frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_write_then_read_round_trips  # noqa: E501
def _write_baseline(
    root: Path, findings: frozenset[tuple[str, str]], commit: str
) -> None:
    """Record `findings` as the baseline the NEXT deferred sweep diffs
    against. Written on every sweep, red or green -- see this module's
    docstring on why an already-filed error must not be re-filed."""
    path = _baseline_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "commit": commit,
        "findings": sorted([rule, file] for rule, file in findings),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _log.info(
        "rapid sweep: recorded rolling baseline of %d error(s) at %s",
        len(findings),
        commit[:12],
    )


# frob:doc docs/modules/tickets.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn.test_exec_disabled_records_debt_and_refuses  # noqa: E501
# frob:ticket T-1684
def spawn_deferred_post_land_sweep(
    root: Path, ticket_id: str, final_id: str, commit_sha: str
) -> Result[int, RapidSweepError]:
    """Fire the unscoped post-land sweep for `final_id` into a DETACHED
    child and return its pid immediately -- the whole point of the rapid
    land path. Records the deferral to `rapid-debt.jsonl` BEFORE the
    spawn, so the "this commit is unverified" fact survives a child that
    never starts or is killed mid-sweep.

    Never raises and never blocks: a refused spawn is `Err(SpawnRefused)`
    and the caller logs it and proceeds. The land commit is already
    durable at this point; nothing here can or should undo it."""
    from frob.process import exec_enabled
    from frob.tickets._evidence import record_rapid_debt

    record_rapid_debt(root, ticket_id, "post-land-unscoped-sweep-deferred")

    if not exec_enabled():
        _log.warning(
            "rapid sweep: %s exec is disabled -- the deferred unscoped "
            "sweep for %s was NOT spawned; that commit stays unverified "
            "(recorded in rapid-debt.jsonl), run `frob check` by hand",
            final_id,
            commit_sha[:12],
        )
        return Err(RapidSweepError.SpawnRefused)

    log_dir = root / _LOG_DIR_REL
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{final_id}-{commit_sha[:12]}.log"
    argv = [
        sys.executable,
        "-m",
        "frob",
        "ticket",
        "sweep-async",
        final_id,
        "--commit",
        commit_sha,
    ]
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=root,
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError as exc:
        _log.error(
            "rapid sweep: %s deferred sweep spawn failed: %s -- commit %s "
            "stays unverified (recorded in rapid-debt.jsonl)",
            final_id,
            exc,
            commit_sha[:12],
        )
        return Err(RapidSweepError.SpawnRefused)

    _log.info(
        "rapid sweep: %s post-land unscoped sweep DEFERRED to detached "
        "pid=%d (log: %s) -- land is not waiting on it; new errors become "
        "a filed bug ticket, never a revert of the published commit",
        final_id,
        proc.pid,
        log_path,
    )
    return Ok(proc.pid)


def _file_regression_ticket(
    root: Path, final_id: str, commit_sha: str, new_findings: frozenset[tuple[str, str]]
) -> str | None:
    """File one `bug` ticket naming every newly-introduced `(rule_id,
    file)` pair, and return its id (`None` if the ledger write failed --
    logged at ERROR, since an unfiled regression is the one outcome that
    makes deferred sweeping unsound)."""
    from frob.tickets import TicketSpec, new_ticket
    from frob.tickets._models import Origin, Priority, TicketKind

    pairs = sorted(new_findings)
    rules = sorted({rule for rule, _ in pairs})
    body_lines = [
        f"The deferred post-land unscoped sweep (T-1684) for {final_id} at "
        f"commit {commit_sha} found {len(pairs)} error identit(ies) that "
        "were not present in the previous sweep's baseline.",
        "",
        "New (rule, file) pairs:",
        "",
        *(f"- {rule}  {file}" for rule, file in pairs),
        "",
        "Under the rapid profile the sweep runs detached and files this "
        "ticket rather than reverting an already-published commit. Fix the "
        "errors, or -- if they are pre-existing residue the rolling "
        "baseline simply had not recorded yet -- close this ticket with "
        "that finding stated explicitly.",
    ]
    spec = TicketSpec(
        title=(
            f"post-land sweep regression from {final_id}: "
            f"{len(pairs)} new error(s) ({', '.join(rules[:4])})"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        scope=tuple(sorted({file for _, file in pairs})),
        body="\n".join(body_lines),
    )
    created = new_ticket(root, spec)
    if created.is_err:
        _log.error(
            "rapid sweep: %s introduced %d new error(s) but the regression "
            "ticket could NOT be filed (%s) -- pairs: %s",
            final_id,
            len(pairs),
            created.danger_err,
            pairs,
        )
        return None
    return created.danger_ok.id


# frob:doc docs/modules/tickets.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_no_new_findings_is_clean  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_new_findings_file_a_ticket_and_rebaseline  # noqa: E501
# frob:ticket T-1684
def run_deferred_post_land_sweep(
    root: Path, final_id: str, commit_sha: str
) -> Result[str | None, RapidSweepError]:
    """The detached child's whole job (`frob ticket sweep-async`): run one
    unscoped `frob check` over `root`, diff it against the rolling
    baseline, file a bug ticket for anything new, and record the fresh set
    as the next baseline.

    Returns the filed ticket id, or `Ok(None)` when the sweep was clean or
    had no baseline to compare against. `Err(Unmeasurable)` when the check
    itself produced no parsable error set -- the baseline is left
    untouched in that case, so an unmeasurable run degrades to "compare
    against the last set we actually trust" rather than silently adopting
    a guess as ground truth."""
    from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

    _log.info(
        "rapid sweep: %s starting deferred unscoped sweep at %s",
        final_id,
        commit_sha[:12],
    )
    fresh = _unscoped_error_findings(root, final_id)
    if fresh is None:
        _log.error(
            "rapid sweep: %s deferred unscoped sweep was UNMEASURABLE "
            "(refused spawn, timeout, or unparsable output) -- baseline "
            "left as-is, commit %s stays unverified",
            final_id,
            commit_sha[:12],
        )
        return Err(RapidSweepError.Unmeasurable)

    baseline = _read_baseline(root)
    _write_baseline(root, fresh, commit_sha)
    if baseline is None:
        _log.warning(
            "rapid sweep: %s had no rolling baseline -- recorded %d "
            "error(s) as the baseline and filed nothing; the NEXT land's "
            "sweep is the first one that can attribute a regression",
            final_id,
            len(fresh),
        )
        return Ok(None)

    new_findings = fresh - baseline
    if not new_findings:
        _log.info(
            "rapid sweep: %s deferred unscoped sweep CLEAN (%d error(s), "
            "none new vs the previous sweep)",
            final_id,
            len(fresh),
        )
        return Ok(None)

    filed = _file_regression_ticket(root, final_id, commit_sha, new_findings)
    _log.error(
        "rapid sweep: %s deferred unscoped sweep found %d NEW error(s) at "
        "%s -- filed as %s (the commit stands; rapid never reverts "
        "published history)",
        final_id,
        len(new_findings),
        commit_sha[:12],
        filed or "UNFILED",
    )
    return Ok(filed)


# frob:ticket T-1684
def _sweep_async(root: Path, cfg) -> None:  # noqa: ANN001 -- AppConfig, deferred import
    """`frob ticket sweep-async <id> --commit <sha>`: the CLI entry point
    the detached child runs. Exits 0 whether the sweep was clean, filed a
    regression ticket, or found no baseline -- this process's exit status
    is nobody's gate (the land that spawned it finished minutes ago); the
    filed ticket and the log are the outputs. Only an UNMEASURABLE sweep
    exits non-zero, so a human re-running this by hand can tell "verified"
    from "could not verify"."""
    if cfg.ticket_id is None or not getattr(cfg, "ticket_sweep_commit", None):
        _log.error("frob ticket sweep-async requires <id> and --commit <sha>")
        sys.exit(1)
    result = run_deferred_post_land_sweep(root, cfg.ticket_id, cfg.ticket_sweep_commit)
    if result.is_err:
        sys.exit(1)


__all__ = [
    "RapidSweepError",
    "run_deferred_post_land_sweep",
    "spawn_deferred_post_land_sweep",
]
