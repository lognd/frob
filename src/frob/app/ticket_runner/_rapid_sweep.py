# frob:ticket T-1684
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

T-1935: the baseline/attribution/quarantine machinery below all operate
on `(rule_id, file)` IDENTITIES (via `_land_cmd._unscoped_error_
findings`, which itself dedupes on `(rule, file)` -- see `frob.app.
ticket_runner._verify._parse_error_findings_from_json`'s own docstring),
never on raw per-finding counts. This is deliberate for attribution and
quarantine (both reason about "which files/rules went red", not
individual diagnostics) and stays that way here (widening the identity
itself would need changes inside `_land_cmd.py`/`_verify.py`'s shared
parsers, both under another agent's live lease at the time of this fix,
T-1720/T-1929). What changes here instead: a filed regression ticket's
own "N new identit(ies)" count can be smaller than the true number of
distinct findings when several findings share one `(rule, file)` pair --
confirmed live, T-1923's sweep reported 6 identities for a commit whose
real unscoped `frob check` found 19 distinct findings (18 COV003 across 5
files collapsed to 5 identities, plus 1 F401) -- so `_file_regression_
ticket` (a) labels its own headline count "(rule, file) identit(ies)",
never "error(s)", and (b) pays for ONE extra, independent `frob check
--json` spawn (`_true_finding_count_for_identities`) ONLY on this rare
red-batch path (a clean sweep never reaches it, so the common-case "one
check per land" design goal above is unaffected) to report the TRUE
per-finding count alongside the identity count, rather than let the
identity count alone be misread as a completeness claim."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
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

#: T-1983: `_file_regression_ticket`'s title prefix, reused here to
#: recognize a sweep-filed ticket for `_close_resolved_sweep_tickets`'s
#: staleness check -- a title match plus `_REGRESSION_IDENTITY_HEADING`
#: parsing recovers the exact identity set the sweep itself recorded,
#: rather than re-deriving a second, possibly-drifting notion of "which
#: findings this ticket is about".
_REGRESSION_TITLE_PREFIX = "post-land sweep regression from "

#: T-1983: the exact heading `_file_regression_ticket` writes immediately
#: before its `"- {rule}  {file}"` lines -- the anchor
#: `_parse_sweep_ticket_identities` scans from, so parsing only ever
#: reads the identity list itself, never the attribution section below it
#: (which reuses the same "- rule  file  -> ..." shape but is not the
#: ticket's own obligation).
_REGRESSION_IDENTITY_HEADING = "New (rule, file) identit(ies) filed here:"

#: T-1935: the check budget (seconds) `_true_finding_count_for_identities`
#: passes to its own independent `frob check --budget --json` re-measure.
#: Deliberately the SAME value as `_land_cmd._POST_LAND_SWEEP_BUDGET_S`
#: (300) rather than an import of it -- `_land_cmd.py` is under another
#: agent's live lease at the time of this fix (T-1720), so this is a
#: literal duplicate of one constant, not a shared import; keep the two
#: values in sync by hand if either changes.
_TRUE_COUNT_BUDGET_S = 300


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


# frob:ticket T-2009
# frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_absent_is_none  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_read_baseline_commit_round_trips  # noqa: E501
def _read_baseline_commit(root: Path) -> str | None:
    """T-2009: the commit the last recorded baseline was ACTUALLY
    measured at, as opposed to the `commit_sha` a land passed to
    `spawn_deferred_post_land_sweep`, which only names the land that
    SPAWNED the sweep -- not necessarily the tree state the detached
    sweep actually measured once it finally ran (other agents' lands can
    and do land in between, since the sweep is deliberately off the land
    critical path, T-1684). `None` under the same conditions `_read_
    baseline` returns `None` for (absent/corrupt -- deliberately not "no
    commits happened", the same "unmeasured is not zero" posture)."""
    path = _baseline_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return str(raw["commit"])
    except Exception:  # noqa: BLE001 -- same posture as _read_baseline
        return None


#: T-2009: matches a `frob ticket land`-authored commit subject, e.g.
#: "fix(tickets): land T-1977 <title...>" -- see `_land_ids_between`.
_LAND_COMMIT_ID_RE = re.compile(r"\bland (T-\d+)\b")


# frob:ticket T-2009
# frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_single_land_in_range  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_multiple_lands_in_range_oldest_first  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_land_commits_are_ignored  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestLandIdsBetween.test_non_repo_returns_empty_list  # noqa: E501
def _land_ids_between(root: Path, since_commit: str, until_commit: str) -> list[str]:
    """T-2009: every distinct `T-####` id named in a `land T-####` commit
    subject reachable in `since_commit..until_commit` (oldest first).

    This is the mechanical fix for misattribution: `run_deferred_post_
    land_sweep`'s `fresh` measurement reflects whatever `root`'s tree
    looks like at the moment the DETACHED sweep child actually runs, not
    the moment it was spawned -- an arbitrary number of OTHER agents'
    lands can land in between (the sweep is deliberately off the land
    critical path, T-1684). Blaming `new_findings` solely on the land
    that happened to spawn this particular sweep process is only correct
    when exactly one land occurred in that window; this function answers
    "how many, and which" so the caller can tell the two cases apart
    instead of guessing. Returns `[]` on any git failure (a non-repo
    `tmp_path` in tests, or a detached-worktree edge case) so callers
    degrade to the pre-T-2009 single-attribution behavior rather than
    raise -- an unmeasurable range must never crash a sweep that has
    already found real findings to file."""
    from frob.gitio import run_argv

    result = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "--format=%s",
            f"{since_commit}..{until_commit}",
        ]
    )
    if result.is_err or result.danger_ok.returncode != 0:
        return []
    ids: list[str] = []
    for line in result.danger_ok.stdout.splitlines():
        match = _LAND_COMMIT_ID_RE.search(line)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


# frob:ticket T-2009
# frob:tests tests/unit/test_rapid_sweep.py::TestResolveActualHead.test_non_repo_falls_back_to_the_given_commit  # noqa: E501
def _resolve_actual_head(root: Path, fallback: str) -> str:
    """T-2009: the actual git HEAD of `root` at the moment this sweep's
    `frob check` finished running, or `fallback` (the land's own
    `commit_sha`, i.e. the pre-T-2009 assumption) when `root` is not a
    git worktree or the resolve fails. Recording THIS as the baseline's
    `commit` (instead of blindly trusting `commit_sha`) is what lets
    `_land_ids_between` compute an honest window on the NEXT sweep --
    never worse than the old behavior, since a resolve failure falls
    straight back to it."""
    from frob.gitio import run_argv

    result = run_argv(["git", "-C", str(root), "rev-parse", "HEAD"])
    if result.is_err or result.danger_ok.returncode != 0:
        return fallback
    head = result.danger_ok.stdout.strip()
    return head or fallback


# frob:tests \
# tests/unit/test_rapid_sweep.py::TestRollingBaseline.test_write_then_read_round_trips
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


# frob:tests \
# tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_leaves_the_repo_clean
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_stages_only_the_debt_file
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_is_a_noop_when_nothing_was_appended  # noqa: E501
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_a_non_repo_never_raises
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
# frob:ticket T-1791
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed
def _partition_findings_by_attribution(
    root: Path,
    final_id: str,
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
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
    same order `pairs` was given.

    `attributions` is computed ONCE by the caller (`_file_regression_
    ticket`, via `_attribute_new_findings`) and passed in here rather than
    recomputed -- T-1791 needs that same mapping a second time (to raise
    quarantine over the whole red batch), and a second `attribute_batch`
    call would mean a second reference-graph build for no new
    information."""
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


#: T-1847: rule ids whose shape is consistent with cold-worktree
#: native-extension noise (a `ty check`/import-resolution failure that
#: fires on a fresh worktree before `frob natives build`/`make core` has
#: run) rather than a genuine regression. Deliberately narrow -- widening
#: this set silently swallows real findings, so only the one rule id the
#: T-1697 incident actually observed is listed; add another only against a
#: second confirmed incident, never speculatively.
_NATIVE_EXTENSION_ADJACENT_RULE_IDS = frozenset({"unresolved-import"})


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1847
def _warm_tree_clears_unattributed_native_noise(root: Path, rule: str, attr) -> bool:  # noqa: ANN001 -- Attribution | None, deferred-import type
    """T-1847: `True` when `(rule, attr)` matches the cold-worktree
    native-extension-noise shape (UNATTRIBUTED, rule in
    `_NATIVE_EXTENSION_ADJACENT_RULE_IDS`) AND a re-check RIGHT NOW shows
    every declared native imports cleanly. That combination means the
    finding's own likely cause -- a native extension not yet built when
    the sweep's check ran -- no longer holds: the tree has since warmed
    (another sweep/build finished, or this is simply a slightly later
    point in the same cold-worktree window), so treating this one finding
    as durable regression signal would just be re-reporting environment
    staleness. `attr` is the `Attribution | None` for the pair; only a
    genuinely UNATTRIBUTED pair (no attribution info, or `attr.status !=
    "attributed"`) is eligible -- an attributed finding already has a real
    commit behind it and this warm re-check is never allowed to override
    that.

    If any declared native is STILL unimportable right now, this returns
    `False` -- that is not transient noise, it is a still-broken
    environment, and the raise proceeds exactly as before this ticket."""
    if rule not in _NATIVE_EXTENSION_ADJACENT_RULE_IDS:
        return False
    if attr is not None and attr.status == "attributed":
        return False
    from frob.strata._native_staleness import unimportable_natives

    broken = unimportable_natives(root)
    if broken:
        _log.debug(
            "rapid sweep: quarantine warm-tree re-check: %s still broken "
            "(%s) -- treating %r as real, not cold-worktree noise",
            rule,
            [s.name for s in broken],
            rule,
        )
        return False
    return True


# frob:doc docs/modules/tickets.md#quarantine-circuit-breaker-t-1693
# frob:ticket T-1791
# frob:ticket T-1847
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raises_with_attributed_and_unattributed_findings  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_drops_cold_worktree_native_noise  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_keeps_finding_when_native_still_broken  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_never_drops_an_attributed_finding  # noqa: E501
def _raise_quarantine_for_red_batch(
    root: Path,
    final_id: str,
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> None:
    """T-1791: the batch-verification driver's missing half -- `frob.
    verify._quarantine.raise_quarantine` existed (T-1693) and the land
    path already enforces it (T-1693's own `_land_cmd._quarantine_
    override_ceilings`), but nothing ever CALLED it. `_file_regression_
    ticket` is the shared "a red batch verification came back" seam both
    T-1684's per-land sweep and T-1688's coalescing worker call through,
    so wiring the raise here covers both drivers from one call site.

    `batch_commit_shas` comes from the CURRENT verify queue (`frob.
    verify.queue_status`) -- the exact set of lands this red result could
    have been caused by, same batch `_attribute_new_findings` itself
    reads. An empty or unreadable queue means there is nothing to name as
    the raising batch (a red result with no queued lands to blame is not
    this ticket's scope to invent an answer for) -- logged and skipped,
    never a raise with a fabricated batch. A `raise_quarantine` failure
    (`QuarantineError.EmptyFindings`, structurally unreachable here since
    `pairs` is always non-empty by the caller's own contract, or a write
    failure) is logged at ERROR and swallowed: the regression ticket
    filing this function's caller does next must never be blocked by the
    quarantine flag failing to persist -- the filed ticket is still the
    primary, durable record of what went wrong.

    T-1847: before naming the batch, every pair is passed through
    `_warm_tree_clears_unattributed_native_noise` -- a pair matching the
    cold-worktree native-extension-noise shape (UNATTRIBUTED,
    `unresolved-import`) whose warm re-check now shows every native
    importing cleanly is dropped from the set that raises quarantine
    entirely (it is still filed as a regression ticket by this function's
    caller -- this only changes what reaches the quarantine dispose
    queue). If dropping cold-worktree noise leaves nothing, the raise is
    skipped altogether and logged at INFO, same "nothing to name" shape as
    the empty-queue branch below."""
    from frob.verify import queue_status
    from frob.verify._quarantine import raise_quarantine

    queue = queue_status(root)
    if queue.is_err or not queue.danger_ok:
        _log.warning(
            "rapid sweep: %s: red batch at %s but the verify queue is "
            "empty/unreadable -- no batch to name, quarantine NOT raised",
            final_id,
            pairs,
        )
        return

    quarantine_pairs = [
        (rule, file)
        for rule, file in pairs
        if not _warm_tree_clears_unattributed_native_noise(
            root, rule, attributions.get((rule, file))
        )
    ]
    dropped = len(pairs) - len(quarantine_pairs)
    if dropped:
        _log.info(
            "rapid sweep: %s: warm-tree re-check cleared %d cold-worktree "
            "native-extension finding(s) from the quarantine raise (still "
            "filed as a regression ticket, just not sent to the dispose "
            "queue)",
            final_id,
            dropped,
        )
    if not quarantine_pairs:
        _log.info(
            "rapid sweep: %s: every finding in this red batch cleared as "
            "cold-worktree native-extension noise -- quarantine NOT raised",
            final_id,
        )
        return

    batch_commit_shas = tuple(e.commit_sha for e in queue.danger_ok)
    findings = _quarantined_findings_from_attributions(quarantine_pairs, attributions)
    raised = raise_quarantine(
        root, batch_commit_shas=batch_commit_shas, findings=findings
    )
    if raised.is_err:
        _log.error(
            "rapid sweep: %s: raise_quarantine failed (%s) for batch %s -- "
            "the regression ticket this red result files is still the "
            "durable record; quarantine flag may be stale until the next "
            "red batch retries the raise",
            final_id,
            raised.danger_err,
            batch_commit_shas,
        )


# frob:ticket T-1791
def _quarantined_findings_from_attributions(
    pairs: list[tuple[str, str]],
    attributions: dict,  # noqa: ANN401 -- dict[tuple[str, str], Attribution], deferred-import type
) -> tuple:  # noqa: ANN401 -- tuple[QuarantinedFinding, ...], deferred-import type
    """Build one `QuarantinedFinding` per `pairs` entry from `attributions`
    (`_raise_quarantine_for_red_batch`'s own ARCH001 split) -- `commit_sha`/
    `ticket_id` are set only for a pair whose `Attribution.status ==
    "attributed"`; an unattributed or unmapped pair gets `None` for both
    (never a guess), matching `QuarantinedFinding`'s own "both `None` for
    an unattributed finding" contract."""
    from frob.verify._quarantine import QuarantinedFinding

    findings = []
    for rule, file in pairs:
        attr = attributions.get((rule, file))
        attributed = attr is not None and attr.status == "attributed"
        findings.append(
            QuarantinedFinding(
                rule_id=rule,
                file=file,
                line=attr.line if attr is not None else None,
                commit_sha=attr.commit_sha if attributed else None,
                ticket_id=attr.ticket_id if attributed else None,
            )
        )
    return tuple(findings)


# frob:ticket T-1935
def _spawn_true_count_check(root: Path, budget: int):  # noqa: ANN201 -- Result[CompletedProcess, ...] | None sentinel via caller, deferred import
    """T-1935: spawn the independent `frob check --budget --json`
    `_true_finding_count_for_identities` needs (ARCH001 split of that
    function). Returns the spawned `subprocess.CompletedProcess` on
    success, or `None` on any of the three unmeasurable outcomes (timeout,
    spawn refused, decode failure) -- each already logged here at WARNING
    with the specific reason, so the caller only has to check for `None`
    and degrade."""
    import subprocess as _subprocess

    from frob.app.ticket_runner._verify import _python_for_tree
    from frob.process._guard import guarded_subprocess_run

    try:
        guarded = guarded_subprocess_run(
            [
                _python_for_tree(root),
                "-m",
                "frob",
                "check",
                "--budget",
                str(budget),
                "--json",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=budget + 60,
            check=False,
        )
    except _subprocess.TimeoutExpired:
        _log.warning(
            "rapid sweep: T-1935 true-finding-count re-measure timed out "
            "after %ds -- reporting the identity count alone",
            budget + 60,
        )
        return None
    if guarded.is_err:
        _log.warning(
            "rapid sweep: T-1935 true-finding-count re-measure spawn "
            "refused (%s) -- reporting the identity count alone",
            guarded.danger_err,
        )
        return None
    return guarded.danger_ok


# frob:ticket T-1935
# frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_counts_every_diagnostic_matching_an_identity  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_unparsable_json_is_none_not_zero  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestTrueFindingCount.test_spawn_refused_is_none_not_zero  # noqa: E501
def _true_finding_count_for_identities(
    root: Path, pairs: frozenset[tuple[str, str]], budget: int = _TRUE_COUNT_BUDGET_S
) -> int | None:
    """T-1935: the TRUE per-finding count restricted to `pairs` -- as
    opposed to `len(pairs)`, which is only ever a count of DISTINCT
    `(rule, file)` IDENTITIES, never a raw finding count (this module's
    docstring). Spawns its own independent `frob check --budget --json`
    (`_spawn_true_count_check`) and counts every `severity == "error"`
    diagnostic whose `(code, file)` is in `pairs`, WITHOUT deduping by
    identity -- so several findings sharing one `(rule, file)` pair are
    each counted, unlike `_land_cmd._unscoped_error_findings`'s own
    identity set.

    Returns `None` (never a wrong number) when unmeasurable: spawn
    refused, a timeout, or output that does not decode as a `frob check
    --json` payload (including a `--budget`-truncated run that deferred a
    stage group -- `_parse_check_json` alone cannot detect that case, so
    an unparsable/budget-truncated `results` list is treated the same as
    "could not measure"). The caller degrades gracefully to reporting the
    identity count alone when this returns `None`.

    Deliberately a SECOND check spawn, paid only by
    `_file_regression_ticket`'s red-batch path (a clean sweep never calls
    this) -- see the module docstring for why that does not reopen T-
    1684's "one check per land" cost concern."""
    from frob.app.ticket_runner._verify import _parse_check_json

    proc = _spawn_true_count_check(root, budget)
    if proc is None:
        return None
    data = _parse_check_json(proc.stdout)
    if data is None:
        _log.warning(
            "rapid sweep: T-1935 true-finding-count re-measure produced "
            "unparsable output -- reporting the identity count alone"
        )
        return None
    results = data.get("results")
    if not isinstance(results, list):
        return None
    count = 0
    for r in results:
        if not isinstance(r, dict):
            continue
        for d in r.get("diagnostics", ()):
            if not isinstance(d, dict) or d.get("severity") != "error":
                continue
            if (d.get("code") or "", d.get("file") or "") in pairs:
                count += 1
    return count


# frob:doc docs/modules/tickets.md#symbolic-attribution-t-1690
# frob:ticket T-1690
# frob:ticket T-1791
# frob:waive AFFECT001 reason="T-1935 changed this function's own count/ wording logic \
# only, not its (rule, file) attribution/filing behavior the affects()-closure doc \
# docs/modules/tickets.md#symbolic-attribution-t-1690 describes; \
# docs/modules/tickets.md is under T-1720's live lease at the time of this fix and \
# cannot be edited here -- filed as follow-up residue"
# frob:waive DRIFT001 reason="same T-1720 live-lease block as the AFFECT001 waiver \
# directly above -- docs/modules/tickets.md cannot be acked here; the underlying \
# attribution/filing behavior this doc describes is unchanged by T-1935, only the \
# reported count/wording, so the doc's own content is still accurate -- filed as \
# follow-up residue to re-ack once the lease frees"
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_no_attribution_files_everything_as_before  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_attributed_to_closed_ticket_is_refiled  # noqa: E501
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_unattributed_is_filed
# frob:tests tests/unit/test_rapid_sweep.py::TestFileRegressionTicket.test_all_attributed_to_open_tickets_files_nothing  # noqa: E501
def _file_regression_ticket(
    root: Path,
    final_id: str,
    commit_sha: str,
    new_findings: frozenset[tuple[str, str]],
    *,
    attributed_ids: Sequence[str] | None = None,
) -> str | None:
    """File one `bug` ticket naming every newly-introduced `(rule_id,
    file)` pair NOT already owned by a still-open ticket, and return its
    id (`None` if the ledger write failed -- logged at ERROR, since an
    unfiled regression is the one outcome that makes deferred sweeping
    unsound; also `None` when every finding attributes to an
    already-open ticket, since that finding already has a home and
    re-filing it would just be noise).

    T-2009: `attributed_ids`, when given (non-empty), OVERRIDES `final_id`
    in the filed ticket's own TITLE and first body line only -- every
    other use of `final_id` in this function (attribution/quarantine
    logging) is unchanged. This exists because `final_id` names the land
    that happened to SPAWN this detached sweep, which is not necessarily
    the same as "the land(s) that actually introduced `new_findings`"
    when more than one land occurred between the last baseline and the
    tree this sweep measured (`_land_ids_between`, computed by the
    caller). `None`/empty falls back to `[final_id]`, i.e. the pre-T-2009
    behavior, unchanged.

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
    own ticket.

    T-1791: EVERY call here is, by definition, a red batch verification
    (the caller only reaches this function when `new_findings` is
    non-empty) -- so this also raises `frob.verify._quarantine.
    raise_quarantine` over the whole batch, using the SAME attributions
    this function already computed for the ticket body, before deciding
    whether a fresh regression ticket is needed. Quarantine is raised
    even when every pair already has an open ticket (the `not
    unfiled_pairs` early return below): the circuit breaker's job is
    "did the tree go red", not "did filing produce a NEW ticket" -- those
    are different questions, and conflating them would let a red batch
    whose findings all happen to already be tracked slip past the
    breaker with deferred landing still enabled."""
    attribution_label = ", ".join(attributed_ids) if attributed_ids else final_id
    from frob.tickets import TicketSpec, new_ticket
    from frob.tickets._models import Origin, Priority, TicketKind

    pairs = sorted(new_findings)
    attributions = _attribute_new_findings(root, pairs)
    unfiled_pairs, attribution_lines = _partition_findings_by_attribution(
        root, final_id, pairs, attributions
    )
    _raise_quarantine_for_red_batch(root, final_id, pairs, attributions)

    if not unfiled_pairs:
        _log.info(
            "rapid sweep: %s: every new finding attributed to an already-"
            "open ticket -- no regression ticket filed",
            final_id,
        )
        return None

    rules = sorted({rule for rule, _ in unfiled_pairs})
    true_count = _true_finding_count_for_identities(root, frozenset(unfiled_pairs))
    if true_count is None:
        count_line = (
            "T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, "
            "not a raw finding count -- every finding sharing a (rule, "
            "file) pair collapses into ONE identity here (deliberately, "
            'so attribution and quarantine reason about "which files '
            'went red", not individual diagnostics). The true per-'
            "finding count could not be independently re-measured this "
            "run (spawn refused/timeout/unparsable) -- re-run `frob "
            "check` unscoped against the file(s) below for the exact "
            "count before treating this identity count as a "
            "completeness claim."
        )
    else:
        count_line = (
            f"T-1935: this is a count of DISTINCT (rule, file) IDENTITIES "
            f"({len(unfiled_pairs)}), not a raw finding count -- every "
            "finding sharing a (rule, file) pair collapses into ONE "
            "identity here (deliberately, so attribution and quarantine "
            'reason about "which files went red", not individual '
            f"diagnostics). An independent re-measurement found "
            f"{true_count} actual finding(s) across those "
            f"{len(unfiled_pairs)} identit(ies)."
        )
    body_lines = [
        f"The deferred post-land unscoped sweep (T-1684) for {attribution_label} "
        f"at commit {commit_sha} found {len(pairs)} new (rule, file) "
        "identit(ies) that were not present in the previous sweep's "
        "baseline.",
        "",
        count_line,
        "",
        _REGRESSION_IDENTITY_HEADING,
        "",
        *(f"- {rule}  {file}" for rule, file in unfiled_pairs),
    ]
    if attributed_ids and len(attributed_ids) > 1:
        body_lines += [
            "",
            f"T-2009: {len(attributed_ids)} lands ({', '.join(attributed_ids)}) "
            "landed between the previous sweep's baseline and the commit "
            "THIS sweep actually measured (the sweep is deliberately "
            "detached, off the land critical path -- T-1684 -- so other "
            "agents' lands can land in the window before it runs). Which "
            "specific land introduced which finding below could not be "
            "determined without re-measuring at each intermediate commit; "
            "this ticket is filed against all of them rather than "
            f"falsely pinned on {final_id} alone (the one that happened "
            "to spawn this sweep process).",
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
    title_count = (
        f"{len(unfiled_pairs)} new (rule, file) identit(ies)"
        if true_count is None
        else f"{len(unfiled_pairs)} new (rule, file) identit(ies), "
        f"{true_count} finding(s)"
    )
    spec = TicketSpec(
        title=(
            f"{_REGRESSION_TITLE_PREFIX}{attribution_label}: {title_count} "
            f"({', '.join(rules[:4])})"
        ),
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.HIGH,
        scope=tuple(sorted({file for _, file in unfiled_pairs})),
        body="\n".join(body_lines),
    )
    # T-1758: new_ticket now auto-commits internally by default -- opt
    # out here (no_commit=True) so _commit_regression_ticket's own commit
    # below still lands, carrying the more informative message naming
    # BOTH the regression ticket id and the land it regressed from,
    # rather than new_ticket's own generic "file T-####" commit.
    # T-1891: warn_if_dirty=False too -- _commit_regression_ticket below
    # always attempts its own commit for the same pathspecs (retried on
    # a transient land-in-progress conflict, T-1841), so a dirty ledger
    # HERE is never the final, left-behind state a --no-commit warning
    # would correctly describe.
    created = new_ticket(root, spec, no_commit=True, warn_if_dirty=False)
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
    _commit_regression_ticket(root, regression_id, attribution_label)
    return regression_id


#: T-1841: `_commit_regression_ticket`'s retry budget for a commit that
#: fails because a CONCURRENT `frob ticket land` holds root's exclusive
#: lock (`LeaseError.LandInProgress`) or loses a transient `git add`/
#: `git commit` race against one. The sweep runs DETACHED after every
#: rapid land, so a land from some OTHER agent still in flight is the
#: NORMAL operating condition here (T-1841's own evidence: four same-day
#: incidents, all under five concurrent agents), not an edge case worth
#: giving up on after one attempt.
_REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS = 5

#: T-1841: seconds between retry attempts. This repo's own land-lock wait
#: (`_land.py`'s `LAND_LOCK_POLL_S`) polls far faster because a live human/
#: agent is blocked on it; a detached sweep has no such urgency, so a
#: coarser interval trades a few extra seconds of sweep latency for far
#: fewer wasted attempts against a land that commonly runs for tens of
#: seconds.
_REGRESSION_TICKET_COMMIT_RETRY_DELAY_S = 3.0


def _discard_uncommitted_regression_ticket(root: Path, regression_id: str) -> None:
    """T-1841: remove `regression_id`'s just-written, never-committed
    ledger content from `root` so a fully-exhausted commit retry leaves
    root CLEAN rather than DirtyMain-blocking every concurrent land --
    the exact tradeoff this ticket's own body mandates ("a half-completed
    bookkeeping step that stalls the fleet is worse than a skipped one it
    can retry").

    v2 (sharded) stores keep one ticket entirely under its own `tickets/
    <id>/` directory (`ticket.md`, `done-report.md`, `attachments/`) that
    this call is the ONLY writer of at this point -- `no_commit=True`
    guarantees nothing has touched git's index yet, so a plain `rmtree`
    cannot destroy anyone else's work. v1 (monofile `tickets.md`) writes
    the SAME shared file every other ledger op reads/writes -- rolling
    back a still-uncommitted append there risks discarding a concurrent
    writer's own in-flight edit to that file, so this deliberately does
    NOT attempt it for v1; the existing best-effort "dirty root, logged
    loudly" posture stands for that (legacy, no longer the default)
    store shape."""
    from frob.tickets._store import _store_mode

    if _store_mode(root) != "v2":
        _log.error(
            "rapid sweep: %s: regression ticket %s could not be committed "
            "after %d attempt(s) and this is a v1 (monofile) store -- "
            "cannot safely auto-discard a shared tickets.md append, root "
            "stays DIRTY; a human must resolve tickets.md by hand",
            root,
            regression_id,
            _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
        )
        return
    ticket_dir = root / "tickets" / regression_id
    shutil.rmtree(ticket_dir, ignore_errors=True)
    _log.error(
        "rapid sweep: regression ticket %s could not be committed to %s "
        "after %d attempt(s) (each spaced %.0fs apart) -- DISCARDED rather "
        "than left as untracked dirt (T-1841); this specific regression is "
        "unfiled for now and will resurface on a future sweep's diff "
        "against the rolling baseline if it is still present",
        regression_id,
        root,
        _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
        _REGRESSION_TICKET_COMMIT_RETRY_DELAY_S,
    )


# frob:ticket T-1755
# frob:ticket T-1791
# frob:ticket T-1841
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commits_the_ledger_write  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_commit_failure_logs_at_error_and_does_not_raise  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_retries_then_succeeds_on_a_transient_land_in_progress  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket.test_exhausted_retries_discard_the_v2_ticket_dir_rather_than_leave_it_dirty  # noqa: E501
def _commit_regression_ticket(
    root: Path,
    regression_id: str,
    final_id: str,
    *,
    max_attempts: int = _REGRESSION_TICKET_COMMIT_MAX_ATTEMPTS,
    retry_delay_s: float = _REGRESSION_TICKET_COMMIT_RETRY_DELAY_S,
) -> None:
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
    under an unrelated commit message).

    T-1841: retries up to `max_attempts` times, `retry_delay_s` apart,
    before giving up -- the sweep runs DETACHED after a land, so a
    DIFFERENT concurrent land holding root's exclusive lock
    (`LeaseError.LandInProgress`) is the routine case, not a rare fluke
    worth surfacing on the very first attempt (T-1841's evidence: four
    same-day incidents, each a coordinator hand-committing a file the
    sweep gave up on after one try). If every attempt still fails, this
    now calls `_discard_uncommitted_regression_ticket` instead of leaving
    the file behind -- T-1841's own requirement: "if the commit cannot
    succeed ... the sweep must NOT leave the file behind. Either
    write-then-commit atomically or do not write." This function's own
    return type stays `None` (best-effort, matching `_commit_rapid_debt`'s
    identical "must never fail an already-succeeded sweep" posture
    immediately below it in this module) -- a land it degraded is already
    published either way; only whether ROOT stays clean is at stake."""
    from frob.tickets._leases import commit_ticket_ledger_change

    message = (
        f"chore(tickets): file {regression_id} "
        f"(post-land sweep regression from {final_id})"
    )
    for attempt in range(1, max_attempts + 1):
        # frob:waive PERF008 reason="deliberate retry with identical arguments, not an \
        # accidental loop-invariant call -- root's exclusive land lock held by a \
        # DIFFERENT concurrent agent is the routine case for a detached sweep \
        # (T-1841), so freshness under concurrency (does the lock still block?) is \
        # exactly the reason this must re-run every iteration rather than being \
        # hoisted or memoized"
        committed = commit_ticket_ledger_change(root, regression_id, message)
        if committed.is_ok:
            return
        if attempt < max_attempts:
            _log.warning(
                "rapid sweep: %s: committing regression ticket %s failed "
                "(%s) on attempt %d/%d -- retrying in %.0fs (a concurrent "
                "land holding root's lock is the routine case, T-1841)",
                final_id,
                regression_id,
                committed.danger_err,
                attempt,
                max_attempts,
                retry_delay_s,
            )
            time.sleep(retry_delay_s)
    _discard_uncommitted_regression_ticket(root, regression_id)


# frob:ticket T-1983
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_parses_a_sweep_titled_ticket_identity_set  # noqa: E501
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_non_sweep_ticket_returns_none  # noqa: E501
def _parse_sweep_ticket_identities(ticket) -> frozenset[tuple[str, str]] | None:  # noqa: ANN001 -- Ticket, deferred-import type
    """T-1983: recover the exact `(rule, file)` identity set
    `_file_regression_ticket` recorded in `ticket`'s body, or `None` if
    `ticket` was not filed by this sweep (its title lacks
    `_REGRESSION_TITLE_PREFIX`) or the identity list could not be found/
    was empty.

    Scans from `_REGRESSION_IDENTITY_HEADING` and stops at the first
    blank line once at least one identity has been collected -- the
    attribution section right below reuses the same `"- rule  file  ->
    ..."` shape for a DIFFERENT purpose (human-readable audit trail, not
    the ticket's own obligation), so this deliberately stops before it
    rather than also matching `" -> "` lines, which would silently widen
    the parsed set with attribution text fragments that can never appear
    in a real fresh measurement -- a wrong identity here can only ever
    make the later subset check fail closed (no drop), never wrongly
    succeed."""
    if not ticket.title.startswith(_REGRESSION_TITLE_PREFIX):
        return None
    lines = ticket.body.splitlines()
    try:
        start = lines.index(_REGRESSION_IDENTITY_HEADING) + 1
    except ValueError:
        return None
    identities: set[tuple[str, str]] = set()
    for line in lines[start:]:
        if not line.strip():
            if identities:
                break
            continue
        if not line.startswith("- ") or " -> " in line:
            break
        parts = line[2:].split("  ", 1)
        if len(parts) != 2:
            continue
        identities.add((parts[0].strip(), parts[1].strip()))
    return frozenset(identities) if identities else None


# frob:ticket T-1983
def _maybe_drop_resolved_ticket(
    root: Path,
    final_id: str,
    ticket,  # noqa: ANN001 -- Ticket, deferred-import type
    vanished: frozenset[tuple[str, str]],
) -> str | None:
    """T-1983 (ARCH001 split of `_close_resolved_sweep_tickets`, one
    ticket's worth of the drop-if-resolved decision): `None` unless
    `ticket`'s full recorded identity set is a non-empty subset of
    `vanished`, in which case it drops `ticket` (`drop_ticket` +
    `commit_ticket_ledger_change`, mirroring `frob ticket drop`'s own CLI
    wiring) and returns its id. Best-effort: a `drop_ticket`/commit
    failure is logged and returns `None`, never raised -- one
    un-droppable stale ticket must not abort the sweep's real job
    (recording the fresh baseline) for every other ticket."""
    from frob.tickets import drop_ticket
    from frob.tickets._leases import commit_ticket_ledger_change

    identities = _parse_sweep_ticket_identities(ticket)
    if not identities or not identities <= vanished:
        return None
    # frob:waive PERF004 reason="this function itself runs once per candidate ticket \
    # from _close_resolved_sweep_tickets' loop, but `identities` is a DIFFERENT set \
    # per ticket (this ticket's own recorded findings) -- there is nothing to hoist, \
    # the sort is not loop-invariant"
    reason = (
        "T-1983: auto-dropped by the deferred post-land sweep -- every "
        f"(rule, file) identity this ticket named "
        f"({', '.join(f'{r} {f}' for r, f in sorted(identities))}) is "
        f"absent from the fresh unscoped measurement at {final_id}'s "
        "deferred sweep, i.e. no longer reproduces. If this is wrong (a "
        "flaky/incomplete measurement), re-file with `frob check --only "
        "<gate>` evidence attached."
    )
    result = drop_ticket(root, ticket.id, reason)
    if result.is_err:
        _log.error(
            "rapid sweep: %s: could not auto-drop resolved regression "
            "ticket %s (%s)",
            final_id,
            ticket.id,
            result.danger_err,
        )
        return None
    committed = commit_ticket_ledger_change(
        root, ticket.id, f"chore(tickets): auto-drop {ticket.id} (resolved, T-1983)"
    )
    if committed.is_err:
        _log.error(
            "rapid sweep: %s: dropped %s but could not commit the ledger "
            "change (%s) -- ticket is dropped in this worktree's tree "
            "but not yet recorded on disk for other agents",
            final_id,
            ticket.id,
            committed.danger_err,
        )
        return None
    _log.info(
        "rapid sweep: %s: auto-dropped resolved regression ticket %s (%d "
        "identit(ies) no longer reproduce)",
        final_id,
        ticket.id,
        len(identities),
    )
    return ticket.id


# frob:ticket T-1983
# frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_drops_a_fully_resolved_sweep_ticket  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_partially_resolved_ticket_untouched  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets.test_leaves_a_still_reproducing_ticket_untouched  # noqa: E501
def _close_resolved_sweep_tickets(
    root: Path, final_id: str, vanished: frozenset[tuple[str, str]]
) -> tuple[str, ...]:
    """T-1983: auto-DROP (never close -- dropping states no work happened
    and no evidence exists, matching how T-1947/T-1972 were handled by
    hand) every QUEUED/PLANNED sweep-filed regression ticket whose full
    recorded identity set is now a subset of `vanished` -- (rule, file)
    identities present in the PREVIOUS baseline but absent from THIS
    sweep's fresh unscoped measurement, i.e. no longer reproducing, per
    this exact same land's own re-measurement rather than a guess or a
    stale prior run. Per-ticket decision + drop lives in
    `_maybe_drop_resolved_ticket`; this function is just the queue scan
    + IN_PROGRESS exclusion.

    A ticket with only SOME of its identities vanished is left untouched
    entirely -- no partial drop, matching this ticket's own acceptance
    ("no false drops, since dropping a live regression is strictly worse
    than leaving a stale one"). IN_PROGRESS tickets are never touched
    here either: a ticket someone is actively working must never be
    yanked out from under them by a background sweep. Returns the
    dropped ids, for the caller's own log line."""
    if not vanished:
        return ()
    from frob.tickets import TicketState, load_queue

    queue = load_queue(root)
    if queue.is_err:
        _log.warning(
            "rapid sweep: %s: could not load the queue to check for "
            "resolved sweep tickets (%s) -- skipping the T-1983 close "
            "pass this run",
            final_id,
            queue.danger_err,
        )
        return ()

    dropped = []
    for ticket in sorted(queue.danger_ok.tickets.values(), key=lambda t: t.id):
        if ticket.state not in (TicketState.QUEUED, TicketState.PLANNED):
            continue
        result = _maybe_drop_resolved_ticket(root, final_id, ticket, vanished)
        if result is not None:
            dropped.append(result)
    return tuple(dropped)


# frob:doc docs/modules/tickets.md#deferred-post-land-sweep-rapid-only-t-1684
# frob:waive AFFECT001 reason="T-1935 changed only this function's own log-line \
# wording (identity vs finding count caveat), not the deferred-sweep-mechanism doc \
# (see the frob:doc target directly above); that doc is under T-1720's live lease at \
# the time of this fix and cannot be edited here -- filed as follow-up residue"
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_unmeasurable_check_leaves_the_baseline_untouched  # noqa: E501
# frob:tests tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_first_sweep_records_a_baseline_and_files_nothing  # noqa: E501
# frob:tests \
# tests/unit/test_rapid_sweep.py::TestDeferredSweepRun.test_no_new_findings_is_clean
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

    # T-2009: the baseline's `commit` must record what was ACTUALLY
    # measured (this sweep's real HEAD at the moment `fresh` finished),
    # not `commit_sha` (the land that merely SPAWNED this detached
    # process) -- other agents' lands routinely land in between, since
    # taking the sweep off the land critical path (T-1684) is the whole
    # point. `prev_baseline_commit` (read BEFORE the rewrite below) is
    # what lets the NEXT sweep compute an honest land-range via
    # `_land_ids_between` instead of guessing.
    prev_baseline_commit = _read_baseline_commit(root)
    actual_head = _resolve_actual_head(root, commit_sha)

    baseline = _read_baseline(root)
    _write_baseline(root, fresh, actual_head)
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

    # frob:ticket T-1983
    # T-1983: `vanished` (identities the PREVIOUS baseline had that this
    # fresh measurement no longer finds) was always computable from the
    # same two sets `new_findings` above already diffs -- this sweep just
    # never used it before. Run the close pass regardless of whether this
    # sweep is otherwise clean or red: a resolved regression ticket and a
    # brand-new one are independent outcomes of the same measurement.
    vanished = baseline - fresh
    closed = _close_resolved_sweep_tickets(root, final_id, vanished)
    if closed:
        _log.info(
            "rapid sweep: %s: closed the loop on %d resolved regression "
            "ticket(s) (T-1983): %s",
            final_id,
            len(closed),
            ", ".join(closed),
        )

    if not new_findings:
        _log.info(
            "rapid sweep: %s deferred unscoped sweep CLEAN (%d error(s), "
            "none new vs the previous sweep)",
            final_id,
            len(fresh),
        )
        return Ok(None)

    # T-2009: only trust `final_id` as the sole attribution when the
    # window between the previous baseline and this sweep's actual HEAD
    # contains exactly one land -- otherwise name every land that
    # occurred in it, so the filed ticket is never pinned on the wrong
    # (or merely coincidental) land.
    attributed_ids: list[str] | None = None
    if prev_baseline_commit and prev_baseline_commit != actual_head:
        land_ids = _land_ids_between(root, prev_baseline_commit, actual_head)
        if len(land_ids) > 1:
            attributed_ids = land_ids
            _log.warning(
                "rapid sweep: %s: %d lands (%s) landed between the last "
                "sweep baseline and the tree this sweep actually "
                "measured -- attributing the regression to all of them "
                "instead of just %s (T-2009)",
                final_id,
                len(land_ids),
                ", ".join(land_ids),
                final_id,
            )

    if attributed_ids is not None:
        filed = _file_regression_ticket(
            root, final_id, actual_head, new_findings, attributed_ids=attributed_ids
        )
    else:
        filed = _file_regression_ticket(root, final_id, actual_head, new_findings)
    _log.error(
        "rapid sweep: %s deferred unscoped sweep found %d NEW (rule, "
        "file) identit(ies) at %s -- filed as %s (the commit stands; "
        "rapid never reverts published history; T-1935: this is a "
        "distinct-identity count, not a raw per-finding count -- see "
        "the filed ticket's body for the caveat)",
        final_id,
        len(new_findings),
        actual_head[:12],
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
