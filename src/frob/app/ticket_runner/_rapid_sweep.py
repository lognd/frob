# frob:ticket T-1684
# frob:waive INV006 reason="this module docstring's exclusivity wording (the sweep is \
# the only thing between a durable commit and the prompt; an already-filed error must \
# not be re-filed) describes this module's OWN implemented branching, verifiable by \
# reading the code it annotates -- not a cross-module contract needing a tracked \
# invariant, same disposition as _profile.py's identical waiver"
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
from collections.abc import Sequence
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


# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_leaves_the_repo_clean  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_stages_only_the_debt_file  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_is_a_noop_when_nothing_was_appended  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_a_non_repo_never_raises  # noqa: E501
# frob:ticket T-1698
def _commit_rapid_debt(root: Path, ticket_id: str) -> None:
    """Commit the `rapid-debt.jsonl` line this land just appended, so the
    land leaves `root` CLEAN.

    `rapid-debt.jsonl` is tracked on purpose (it must survive a clone and
    a `frob clean`, and be reviewable in a diff), and this record is
    written AFTER the land commit is sealed because it names that commit
    -- so it cannot ride along in it, and amending is forbidden here. It
    therefore gets its own tiny follow-up commit. Without this, every
    rapid land left the shared root checkout dirty and the NEXT land from
    ANY agent refused with `DirtyMain`: one uncommitted line deadlocked a
    whole three-agent wave (T-1698).

    Stages `rapid-debt.jsonl` and NOTHING else. A blanket `git add -A` on
    a root checkout that concurrent lands are racing against would sweep
    up whatever another agent had in flight -- the opposite of the
    isolation this file exists to record.

    Best-effort: a failure here must never fail a land that has already
    succeeded, but it is logged at ERROR, because the resulting dirty root
    is invisible in the `DirtyMain` error every other agent then hits."""
    from frob.gitio import run_argv

    rel = "rapid-debt.jsonl"
    status = run_argv(["git", "-C", str(root), "status", "--porcelain", "--", rel])
    if status.is_err or status.danger_ok.returncode != 0:
        _log.error(
            "rapid sweep: %s could not read %s status in %s -- if it is "
            "dirty, every subsequent land in this repo will refuse with "
            "DirtyMain",
            ticket_id,
            rel,
            root,
        )
        return
    if not status.danger_ok.stdout.strip():
        return  # nothing appended (e.g. the write failed and logged already)

    staged = run_argv(["git", "-C", str(root), "add", "--", rel])
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("rapid sweep: %s could not stage %s in %s", ticket_id, rel, root)
        return
    committed = run_argv(
        [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            f"chore(rapid): record {ticket_id}'s deferred post-land sweep",
            "--",
            rel,
        ]
    )
    if committed.is_err or committed.danger_ok.returncode != 0:
        _log.error(
            "rapid sweep: %s could not commit %s in %s -- root is now DIRTY "
            "and the next land from any agent will refuse with DirtyMain; "
            "commit it by hand",
            ticket_id,
            rel,
            root,
        )
        return
    _log.info("rapid sweep: %s committed the deferred-sweep debt line", ticket_id)


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
    _commit_rapid_debt(root, ticket_id)

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


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_empty_queue_returns_empty_mapping  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestAttributeNewFindings.test_attributed_and_unattributed_round_trip  # noqa: E501
def _attribute_new_findings(
    root: Path, pairs: Sequence[tuple[str, str] | tuple[str, str, int]]
):  # noqa: ANN201 -- dict[tuple[str, str], Attribution], deferred-import type
    """T-1690 tier-2: attribute each `(rule, file)` (or, when a caller has
    a line number, `(rule, file, line)`) pair in `pairs` to the single
    durable `VerifyQueueEntry` (if any) whose `touched_symbols`
    graph-reaches it, using the CURRENT verify queue as the batch (the set
    of lands recorded since the last watermark advance -- exactly the
    commits this red sweep could have been caused by). Returns `{}`
    (attribution unavailable for every pair, never a partial mapping) when
    the queue cannot be read or the reference graph cannot be built --
    `_file_regression_ticket` treats an empty mapping as "no attribution
    information", not "everything unattributed", falling back to filing
    the whole set exactly as it did before this ticket."""
    from frob.verify import attribute_batch, queue_status

    queue = queue_status(root)
    if queue.is_err:
        _log.warning(
            "rapid sweep: attribution: verify queue unreadable (%s) -- "
            "filing without attribution",
            queue.danger_err,
        )
        return {}
    batch = queue.danger_ok
    if not batch:
        _log.info(
            "rapid sweep: attribution: verify queue is empty -- filing "
            "without attribution"
        )
        return {}
    attributed = attribute_batch(root, pairs, batch)
    if attributed.is_err:
        _log.warning(
            "rapid sweep: attribution: reference graph unavailable (%s) -- "
            "filing without attribution",
            attributed.danger_err,
        )
        return {}
    return {(a.rule_id, a.file): a for a in attributed.danger_ok}


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:tests tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_open_ticket_is_open
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_done_ticket_is_not_open
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestTicketIsOpen.test_missing_ticket_is_not_open
def _ticket_is_open(root: Path, ticket_id: str) -> bool:
    """`True` when `ticket_id` still exists and is NOT `done`/`dropped` --
    the "owning ticket still open" half of T-1690's filing rule. A ticket
    that cannot be loaded at all (queue read failure, id not found)
    counts as NOT open: attribution should never suppress a real
    regression's own ticket because the owning ticket became
    unreadable."""
    from frob.tickets import load_queue
    from frob.tickets._models import TicketState

    queue = load_queue(root)
    if queue.is_err:
        return False
    ticket = queue.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        return False
    return ticket.state not in (TicketState.DONE, TicketState.DROPPED)


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
def _partition_findings_by_attribution(
    root: Path, final_id: str, pairs: list[tuple[str, str]]
) -> tuple[list[tuple[str, str]], list[str]]:
    """T-1690: split `pairs` into `(unfiled_pairs, attribution_lines)`
    (ARCH001 split of `_file_regression_ticket`, which was previously one
    122-line function). `unfiled_pairs` is every pair that still needs its
    own regression ticket -- unattributed, or attributed to a
    closed/dropped ticket's commit; a pair attributed to a STILL-OPEN
    ticket is left out of it entirely (logged instead, at INFO, once per
    owning ticket) since it already has a home. `attribution_lines` is the
    human-readable audit trail for EVERY pair with attribution
    information (including the already-open ones, so a caller that wants
    the full picture -- not just what got filed -- still has it), in the
    same order `pairs` was given."""
    attributions = _attribute_new_findings(root, pairs)

    unfiled_pairs: list[tuple[str, str]] = []
    attribution_lines: list[str] = []
    already_open: dict[str, int] = {}
    for rule, file in pairs:
        attr = attributions.get((rule, file))
        if attr is None:
            unfiled_pairs.append((rule, file))
            continue
        if attr.status == "attributed" and _ticket_is_open(root, attr.ticket_id):
            already_open[attr.ticket_id] = already_open.get(attr.ticket_id, 0) + 1
            attribution_lines.append(
                f"- {rule}  {file}  -> attributed to {attr.ticket_id} "
                f"(commit {attr.commit_sha[:12]}, already open -- not "
                f"re-filed) via {' -> '.join(attr.reachability_path)}"
            )
            continue
        unfiled_pairs.append((rule, file))
        if attr.status == "attributed":
            attribution_lines.append(
                f"- {rule}  {file}  -> attributed to {attr.ticket_id} "
                f"(commit {attr.commit_sha[:12]}, already closed/dropped -- "
                f"filed below) via {' -> '.join(attr.reachability_path)}"
            )
        else:
            attribution_lines.append(
                f"- {rule}  {file}  -> UNATTRIBUTED ({attr.reason}); "
                f"candidate commits: {list(attr.candidate_commits)}"
            )

    if already_open:
        _log.info(
            "rapid sweep: %s: %d finding(s) already attributed to still-"
            "open ticket(s) %s -- not re-filed",
            final_id,
            sum(already_open.values()),
            sorted(already_open),
        )
    return unfiled_pairs, attribution_lines


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_no_attribution_files_everything_as_before  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_closed_ticket_is_refiled  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_all_attributed_to_open_tickets_files_nothing  # noqa: E501
def _file_regression_ticket(
    root: Path, final_id: str, commit_sha: str, new_findings: frozenset[tuple[str, str]]
) -> str | None:
    """File one `bug` ticket naming every newly-introduced `(rule_id,
    file)` pair NOT already owned by a still-open ticket, and return its
    id (`None` if the ledger write failed -- logged at ERROR, since an
    unfiled regression is the one outcome that makes deferred sweeping
    unsound; also `None` when every finding attributes to an
    already-open ticket, since that finding already has a home and
    re-filing it would just be noise).

    T-1690: each pair is first run through `_partition_findings_by_
    attribution` (tier-2 symbolic reachability over the durable verify
    queue, via `_attribute_new_findings`). A pair that attributes to
    EXACTLY ONE batch commit whose ticket is still open is logged and left
    off this ticket entirely -- it is already tracked. Every other pair
    (attributed to a closed/dropped ticket's commit, or UNATTRIBUTED --
    zero or more than one reaching commit) is filed here, with the full
    attribution audit trail (commit, symbol, reachability path, or the
    reason it could not be attributed) in the body, so a reader never has
    to re-derive what this ticket already computed. Attribution
    unavailability (empty mapping from `_attribute_new_findings`)
    degrades to the pre-T-1690 behavior: every pair filed, no attribution
    lines -- "cannot attribute" must never suppress a real regression's
    own ticket."""
    from frob.tickets import TicketSpec, new_ticket
    from frob.tickets._models import Origin, Priority, TicketKind

    pairs = sorted(new_findings)
    unfiled_pairs, attribution_lines = _partition_findings_by_attribution(
        root, final_id, pairs
    )

    if not unfiled_pairs:
        _log.info(
            "rapid sweep: %s: every new finding attributed to an already-"
            "open ticket -- no regression ticket filed",
            final_id,
        )
        return None

    rules = sorted({rule for rule, _ in unfiled_pairs})
    body_lines = [
        f"The deferred post-land unscoped sweep (T-1684) for {final_id} at "
        f"commit {commit_sha} found {len(pairs)} error identit(ies) that "
        "were not present in the previous sweep's baseline.",
        "",
        "New (rule, file) pairs filed here:",
        "",
        *(f"- {rule}  {file}" for rule, file in unfiled_pairs),
    ]
    if attribution_lines:
        body_lines += [
            "",
            "Attribution (T-1690, symbolic reachability over the verify "
            "queue's touched-symbol sets):",
            "",
            *attribution_lines,
        ]
    body_lines += [
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
            f"{len(unfiled_pairs)} new error(s) ({', '.join(rules[:4])})"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        scope=tuple(sorted({file for _, file in unfiled_pairs})),
        body="\n".join(body_lines),
    )
    created = new_ticket(root, spec)
    if created.is_err:
        _log.error(
            "rapid sweep: %s introduced %d new error(s) but the regression "
            "ticket could NOT be filed (%s) -- pairs: %s",
            final_id,
            len(unfiled_pairs),
            created.danger_err,
            unfiled_pairs,
        )
        return None
    regression_id = created.danger_ok.id
    _commit_regression_ticket(root, regression_id, final_id)
    return regression_id


# frob:ticket T-1755
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commits_the_ledger_write  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commit_failure_logs_at_error_and_does_not_raise  # noqa: E501
def _commit_regression_ticket(root: Path, regression_id: str, final_id: str) -> None:
    """T-1755: `_file_regression_ticket`'s `new_ticket(root, spec)` call
    (the whole point of the deferred sweep) writes `tickets.md` through
    `frob.tickets._new_renumber.new_ticket` DIRECTLY -- the LIBRARY
    function, not the `frob ticket new` CLI verb -- and `new_ticket`
    itself never commits (confirmed by reading it: it takes `ledger_lock`,
    calls `write_ticket`, and returns; T-1130/T-1615's auto-commit lives
    entirely in the CLI dispatch layer, `commit_ticket_ledger_change`,
    which a programmatic caller like this one never reaches). This is the
    THIRD root-cause candidate this ticket's own body named as most
    likely, confirmed: T-1615's uniform auto-commit covers the CLI
    surface, not programmatic callers, which is a wider gap than this one
    call site -- filed as a follow-up (see this function's own Done
    report for the real id) rather than silently left for the next
    detached-write incident to rediscover.

    Calls `frob.tickets._leases.commit_ticket_ledger_change` -- the SAME
    scoped `git add <ledger pathspecs> && git commit -- <ledger
    pathspecs>` primitive `frob ticket new`/`drop`/`fail`/`start` already
    funnel through, never a bare `git commit` or `git add -A` (T-1740's
    own incident: a blanket add on a root checkout concurrent lands are
    racing against published 1416 lines of another agent's in-flight work
    under an unrelated commit message). A commit failure is logged at
    ERROR naming `regression_id` and warning explicitly that the NEXT
    land will refuse with `DirtyMain` -- never swallowed, never silent;
    this function's own return type is `None` (best-effort, matching
    `_commit_rapid_debt`'s identical "must never fail an already-
    succeeded sweep" posture immediately below it in this module) --
    the regression ticket itself is already durably filed by the time
    this runs, so a commit failure here degrades to "dirty root, logged
    loudly", never to "the ticket silently vanishes"."""
    from frob.tickets._leases import _ledger_pathspecs, commit_ticket_ledger_change

    message = (
        f"chore(tickets): file {regression_id} "
        f"(post-land sweep regression from {final_id})"
    )
    committed = commit_ticket_ledger_change(root, regression_id, message)
    if committed.is_err:
        pathspecs = " ".join(_ledger_pathspecs(root, regression_id))
        _log.error(
            "rapid sweep: %s: committing the filed regression ticket %s "
            "failed (%s) -- the ledger is now DIRTY and every subsequent "
            "`frob ticket land` in %s will refuse with DirtyMain until a "
            'human commits it by hand: git -C %s add %s && git -C %s '
            "commit -m %r -- %s",
            final_id,
            regression_id,
            committed.danger_err,
            root,
            root,
            pathspecs,
            root,
            message,
            pathspecs,
        )


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
