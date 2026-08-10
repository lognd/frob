"""frob.app.ticket_runner._lifecycle -- the `plan`/`start`/`requeue`/
`sweep`/`reconcile`/`attach`/`block` command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from frob.app.config import AppConfig
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.process._guard import EXEC_KILL_SWITCH_ENV, exec_enabled

if TYPE_CHECKING:
    from frob.tickets._reconcile import ReconcileReport

_log = get_logger("frob.app.ticket_runner")


def _plan(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket plan requires <id>")
        sys.exit(1)
    planned = transition(root, cfg.ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket plan failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("planned %s", cfg.ticket_id)


# frob:ticket T-0472
def _requeue(root: Path, cfg: AppConfig) -> None:
    """Transition an in-progress ticket back to queued (the state-machine-
    legal reverse of `start`'s auto-plan+start), for a parked or
    mis-started ticket that must be honestly requeued instead of hand-
    edited (T-0472). Since the T-0453 tree-lease is derived live from
    IN_PROGRESS state + scope, this transition alone releases the lease --
    no separate lease-release step is needed. `--reason` is optional and,
    when given, is only logged (not persisted) -- requeue carries no
    Done-report/evidence surface of its own to attach it to.

    T-1178: auto-commits the ledger change (parity with new/drop/fail's
    T-1130 auto-commit) -- `--no-commit` (`cfg.ticket_no_commit`) opts
    out."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket requeue requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="requeue")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error(
            "ticket requeue failed: %s is %s, not in-progress -- only an "
            "in-progress ticket can be requeued",
            cfg.ticket_id,
            ticket.state.value,
        )
        sys.exit(1)

    requeued = transition(root, cfg.ticket_id, TicketState.QUEUED)
    if requeued.is_err:
        _log.error("ticket requeue failed: %s", requeued.danger_err)
        sys.exit(1)
    if cfg.ticket_reason:
        _log.info(
            "%s requeued (in-progress -> queued): %s",
            cfg.ticket_id,
            cfg.ticket_reason,
        )
    else:
        _log.info("%s requeued (in-progress -> queued)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="requeued")

    # frob:ticket T-1178
    from frob.tickets._leases import commit_ticket_ledger_change

    committed = commit_ticket_ledger_change(
        root,
        cfg.ticket_id,
        f"chore(tickets): requeue {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)


def _load_ticket_or_exit(root: Path, ticket_id: str, *, verb: str):  # noqa: ANN201
    """The ticket `ticket_id`, or exit(1) if the queue or lookup fails."""
    from frob.tickets import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket %s failed: %s", verb, queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.error("no ticket %s", ticket_id)
        sys.exit(1)
    return ticket


def _auto_plan_if_queued(root: Path, ticket_id: str, ticket):  # noqa: ANN201
    """Transition a QUEUED ticket to PLANNED first; `start` takes both legal steps."""
    from frob.tickets import TicketState, transition

    if ticket.state != TicketState.QUEUED:
        return ticket
    planned = transition(root, ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket start failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("auto-planned %s (queued -> planned)", ticket_id)
    return planned.danger_ok


def _find_landing_commit(root: Path, ticket_id: str) -> str | None:
    """The short hash of the commit that landed `ticket_id`, if cheaply
    derivable (T-0835) -- `frob ticket land`'s own commits are conventionally
    titled `land <id> ...` (see this repo's own git history), so a `git log
    --grep` for that exact phrase against `root` finds it in one spawn. Best-
    effort: `None` on any git failure, an empty result, or a non-repo `root`
    -- a terminal-state refusal must still fire even when the commit cannot
    be named, just without the extra detail."""
    from frob import gitio

    spawned = gitio.run_argv(
        (
            "git",
            "-C",
            str(root),
            "log",
            "--oneline",
            "-E",
            "--grep",
            f"land {ticket_id}([^0-9]|$)",
            "-n",
            "1",
        )
    )
    if spawned.is_err:
        return None
    line = spawned.danger_ok.stdout.strip()
    if not line:
        return None
    return line.split(maxsplit=1)[0]


def _refuse_if_terminal(root: Path, ticket_id: str, ticket) -> None:  # noqa: ANN001
    """`sys.exit(1)` with an actionable message if `ticket` is DONE or
    DROPPED (T-0835): re-`start`ing a terminal ticket is never legitimate --
    the T-0835 incident was exactly a second agent's `start` succeeding on a
    ticket another worktree had already finished. Names the landing commit
    when `_find_landing_commit` can cheaply find one; otherwise names just
    the terminal state, never blocking the refusal on git being unavailable."""
    from frob.tickets import TicketState

    if ticket.state not in (TicketState.DONE, TicketState.DROPPED):
        return
    commit = (
        _find_landing_commit(root, ticket_id)
        if ticket.state is TicketState.DONE
        else None
    )
    if commit is not None:
        _log.error(
            "ticket start failed: %s is already %s (landed at %s) -- nothing to start",
            ticket_id,
            ticket.state.value,
            commit,
        )
    else:
        _log.error(
            "ticket start failed: %s is already %s -- nothing to start",
            ticket_id,
            ticket.state.value,
        )
    sys.exit(1)


def _refuse_if_foreign_live_lease(root: Path, ticket_id: str, *, steal: bool) -> None:
    """`sys.exit(1)` if `ticket_id` holds a LIVE lease pinned to a worktree
    other than `root`, unless `steal` is set (T-0835 -- the double-dispatch
    fix). A lease pinned to `root` itself is idempotent (no refusal, so a
    restart after an interrupted session in the SAME worktree keeps
    working); an EXPIRED lease (`is_lease_ttl_expired`) never blocks --
    that is the existing dead-agent recovery path (T-0782/T-0476) and must
    stay intact.

    Stealing does not itself rewrite the lease file: the caller's own
    `transition(..., TicketState.IN_PROGRESS)` call (via `_sync_cross_
    worktree_lease`) already re-`record_lease`s pinned to `root`
    unconditionally, which overwrites the stolen worktree's file in place --
    reusing that existing machinery rather than inventing a second lease
    write path. The losing worktree's OWN lease is gone the moment this
    returns, so its later `resolve_lease`/`ticket_lease_pin` (`frob check
    --ticket`, `frob ticket close`) fails against the new content, exactly
    the "cannot silently land" property T-0835 requires."""
    from frob.tickets._leases import (
        is_lease_ttl_expired,
        lease_age_seconds,
        read_all_leases,
    )

    record = next((r for r in read_all_leases(root) if r.ticket_id == ticket_id), None)
    if record is None or is_lease_ttl_expired(record):
        return
    record_worktree = Path(record.worktree).resolve()
    if record_worktree == root.resolve():
        return

    age = lease_age_seconds(record)
    age_desc = f"{age:.0f}s ago" if age is not None else "unknown age"
    if steal:
        _log.warning(
            "ticket start: %s stealing live lease from worktree %s "
            "(recorded %s) -- that worktree's lease is now invalidated and "
            "cannot close/land %s",
            ticket_id,
            record_worktree,
            age_desc,
            ticket_id,
        )
        return
    _log.error(
        "ticket start failed: %s has a live lease held by worktree %s "
        "(recorded %s) -- pass --steal to override (this invalidates the "
        "other worktree's lease so it can no longer close/land %s)",
        ticket_id,
        record_worktree,
        age_desc,
        ticket_id,
    )
    sys.exit(1)


# frob:ticket T-1175
def _default_work_worktree(root: Path, ticket_id: str) -> Path:
    """The default `.claude/worktrees/<slug>` path `frob ticket work`
    creates/reuses for `ticket_id` when `--worktree` is not given (T-1175):
    the ticket id lowercased (`T-1175` -> `t-1175`), matching this repo's
    own dispatch-worktree naming convention (`.claude/worktrees/w21-...`
    series slugs, `t-####` per-ticket slugs) closely enough to be
    predictable without colliding with a hand-named series worktree."""
    return root / ".claude" / "worktrees" / ticket_id.lower()


# frob:ticket T-1790
# frob:tests tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree.test_detects_root_under_dot_claude_worktrees  # noqa: E501
# frob:tests tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree.test_primary_checkout_is_not_nested  # noqa: E501
def _root_is_itself_a_nested_worktree(root: Path) -> bool:
    """`True` iff `root` (already resolved) has a `.claude/worktrees`
    segment anywhere in its own path -- i.e. `root` is ITSELF a
    dispatched agent worktree, not the primary checkout (T-1790, the
    root cause behind T-1779 finding 7).

    `frob ticket work` always creates the new worktree UNDER `root`'s
    OWN `.claude/worktrees/` (`_default_work_worktree`) -- when `root`
    already lives under someone else's `.claude/worktrees/agent-X/`, the
    result NESTS: `agent-X/.claude/worktrees/t-1766`. This is doomed on
    two counts observed live: it cannot land cleanly (the "nested-
    worktree lands don't stick" failure mode), and it dies SILENTLY the
    moment its parent worktree is retired/removed -- taking the nested
    one with it while any lease pointing at it survives untouched,
    orphaning whatever ticket held it (T-1766's actual incident; see
    `frob.tickets._leases.orphaned_leases`, T-1779's downstream fix for
    the SYMPTOM this function prevents at the SOURCE).

    Same segment-matching shape as `frob.tickets._leases.
    _is_agent_worktree_path` (not imported directly -- that module's own
    private helper, and this ticket's declared scope is `_lifecycle.py`
    alone), deliberately kept as a small, independent check rather than
    a new cross-module dependency for one boolean test."""
    parts = root.parts
    return any(
        parts[i] == ".claude" and parts[i + 1] == "worktrees"
        for i in range(len(parts) - 1)
    )


# frob:ticket T-1175
def _run_git_or_exit(argv: list[str], *, ticket_id: str, error_template: str) -> None:
    """Spawn `argv` via `run_argv`; `sys.exit(1)` with `error_template %
    (ticket_id, detail)` (a spawn-level error, or stderr, whichever
    applies) on any non-zero/`Err` outcome. Shared by `_worktree_add_or_
    reuse`/`_ensure_worktree_fresh` (T-1175) so each stays a single
    decision (did the one git spawn it cares about succeed) instead of
    also carrying this same error-formatting branch inline (ARCH103)."""
    spawned = run_argv(argv)
    if spawned.is_ok and spawned.danger_ok.returncode == 0:
        return
    detail = spawned.danger_err if spawned.is_err else spawned.danger_ok.stderr
    _log.error(error_template, ticket_id, detail)
    sys.exit(1)


# frob:ticket T-1175
def _worktree_add_or_reuse(root: Path, worktree: Path, ticket_id: str) -> None:
    """`frob ticket work`'s worktree half (T-1175, playbook section 0 step
    1): if `worktree` does not exist on disk yet, `git worktree add` it on
    a fresh branch cut from `root`'s CURRENT local `main` tip (plain `git
    worktree add ... main`, never touching `origin` -- the exact form
    section 1's T-1030 root-cause note already documents as immune to the
    stale-origin-tip bug a dispatch-harness worktree tool can otherwise
    hit). If it already exists, this is a no-op here -- freshness is
    `_ensure_worktree_fresh`'s job, run unconditionally right after this
    either way, so a REUSED worktree gets the exact same freshness
    guarantee a FRESH one already has by construction."""
    if worktree.exists():
        return
    worktree.parent.mkdir(parents=True, exist_ok=True)
    branch = ticket_id.lower()
    _run_git_or_exit(
        [
            "git",
            "-C",
            str(root),
            "worktree",
            "add",
            str(worktree),
            "-b",
            branch,
            "main",
        ],
        ticket_id=ticket_id,
        error_template="ticket work: %s could not create worktree: %s",
    )
    _log.info(
        "ticket work: %s created worktree %s (branch %s)", ticket_id, worktree, branch
    )


# frob:ticket T-1175
def _ensure_worktree_fresh(worktree: Path, ticket_id: str) -> None:
    """`frob ticket work`'s freshness half (T-1175, playbook section 0 step
    1 / section 1's `git merge main` + tip-verification warm-up): merge
    `worktree`'s local `main` into HEAD -- a no-op ("Already up to date")
    for a worktree this call just created fresh off `main`'s own tip, and
    the real fix for a REUSED worktree that has gone stale since its last
    session. A merge conflict here is refused loudly rather than resolved
    silently -- `frob ticket work` is not the ledger-splice recovery path
    (docs/guides/agent-playbook.md#10-ledger-conflict-splice-guidance)."""
    _run_git_or_exit(
        ["git", "-C", str(worktree), "merge", "main", "--no-edit"],
        ticket_id=ticket_id,
        error_template=(
            "ticket work: %s could not merge main: %s -- resolve by hand "
            "(see docs/guides/agent-playbook.md#10-ledger-conflict-splice-"
            "guidance for tickets.md conflicts specifically)"
        ),
    )


# frob:ticket T-1175
def _build_natives_for_work(worktree: Path, ticket_id: str) -> None:
    """`frob ticket work`'s natives-build half (T-1175, playbook section 0
    step 2): build every declared `[[native]]` crate into `worktree`'s own
    venv via `frob.natives.build_natives` -- the in-process function
    `frob natives build`'s own CLI wraps, not a subprocess re-invocation of
    the CLI, so this needs no `guarded_subprocess_run` exec-guard plumbing.
    `NoNatives` (a project with no declared native crates) is not an
    error -- most tickets in most repos never touch this at all."""
    from frob.natives import NativesError, build_natives

    result = build_natives(worktree)
    if result.is_err:
        if result.danger_err is NativesError.NoNatives:
            return
        _log.error(
            "ticket work: %s natives build failed: %s",
            ticket_id,
            result.danger_err.value,
        )
        sys.exit(1)
    report = result.danger_ok
    if not report.ok:
        _log.error(
            "ticket work: %s natives build reported failing crate(s) -- see "
            "the `frob natives build` output above for detail",
            ticket_id,
        )
        sys.exit(1)


# frob:ticket T-1243
def _default_cluster_worktree(root: Path, cluster_id: str) -> Path:
    """The default `.claude/worktrees/<slug>` path `frob ticket work
    --cluster` creates/reuses when `--worktree` is not given (T-1243) --
    same naming convention as `_default_work_worktree`, just keyed off the
    cluster (epic/story) id instead of a single ticket id."""
    return root / ".claude" / "worktrees" / cluster_id.lower()


# frob:ticket T-1243
def _refuse_on_cluster_scope_conflict(
    root: Path, cluster_id: str, members: tuple
) -> None:
    """`sys.exit(1)` naming the conflicting ticket/glob if the union scope of
    `members` (T-1243) overlaps an ALREADY in-progress ticket's active
    lease that is not itself one of `members` (a sibling cluster, or a
    lone-ticket mission, already holding overlapping files) -- preserves
    the disjoint-scope dispatch guarantee `frob.tickets.leased_by` already
    gives single-ticket `start`/`doable` at the cluster level too. A clean
    return means the whole union scope is free to lease."""
    from frob.tickets import load_queue
    from frob.tickets._brief import cluster_union_scope
    from frob.tickets._doable import _all_leases
    from frob.tickets._models import scope_overlap_globs

    member_ids = {t.id for t in members}
    union_scope = cluster_union_scope(members)
    if not union_scope:
        return

    queue_result = load_queue(root)
    if queue_result.is_err:
        return
    queue = queue_result.danger_ok
    for holder_id, holder_scope in _all_leases(queue, root):
        if holder_id in member_ids:
            continue
        collision = scope_overlap_globs(union_scope, holder_scope)
        if collision is not None:
            _log.error(
                "ticket work --cluster %s failed: union scope %r collides "
                "with %s's active lease on %r -- resolve the overlap "
                "before dispatching this cluster",
                cluster_id,
                collision[0],
                holder_id,
                collision[1],
            )
            sys.exit(1)


# frob:ticket T-1243
def _start_cluster_members(
    worktree: Path, cluster_id: str, members: tuple, cfg: AppConfig
) -> tuple[str, ...]:
    """Start every `members` ticket that has no OPEN blocker right now
    (T-1243), in `cluster_descendants`' dependency order, against
    `worktree` -- reusing `_start` per member rather than a second state-
    machine path. A member still blocked by an earlier member of this same
    cluster is left alone and its id returned in the deferred tuple (see
    `_work_cluster`'s docstring for why becoming in-progress cannot
    resolve a sibling's own open blocker within this same pass). Reloads
    the queue fresh before each member since the PRECEDING member's own
    start just committed a ledger change."""
    from frob.tickets import load_queue
    from frob.tickets._doable import _open_blockers

    deferred: list[str] = []
    for member in members:
        queue_now = load_queue(worktree)
        if queue_now.is_err:
            _log.error("ticket work --cluster failed: %s", queue_now.danger_err)
            sys.exit(1)
        open_blockers = _open_blockers(queue_now.danger_ok, member)
        if open_blockers:
            deferred.append(member.id)
            _log.info(
                "ticket work --cluster %s: %s deferred -- still blocked by "
                "%s (start it with `frob ticket start %s` in this same "
                "worktree once that closes)",
                cluster_id,
                member.id,
                list(open_blockers),
                member.id,
            )
            continue
        member_cfg = cfg.model_copy(update={"ticket_id": member.id})
        _start(worktree, member_cfg)
    return tuple(deferred)


# frob:ticket T-1243
# frob:ticket T-1790
# frob:tests tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree.test_work_cluster_refuses_from_a_nested_worktree  # noqa: E501
def _work_cluster(root: Path, cfg: AppConfig) -> None:
    """`frob ticket work --cluster <epic-or-story-id> [--worktree PATH]`
    (T-1243): the cluster form of `_work` -- create/reuse ONE worktree,
    merge `main` for freshness, and build natives ONCE for the whole
    mission (instead of once per ticket), then lease every currently-
    dispatchable descendant of the cluster into it via the union of their
    declared scopes (`frob.tickets._brief.cluster_union_scope`),
    dependency-ordered (`frob.tickets._brief.cluster_descendants`).
    Refuses loudly, before creating/touching anything, if the union scope
    collides with an already-leased ticket outside this cluster
    (`_refuse_on_cluster_scope_conflict`) -- the T-1243 acceptance
    criterion that a second cluster with an overlapping union scope fails
    loud rather than silently double-leasing files. Each member whose
    blockers are ALREADY resolved (no open `blocked_by`, including a
    sibling cluster member the dependency-ordering already sequenced
    first) transitions to in-progress immediately, exactly the way
    `_start` already does (auto-plan a queued ticket, background pre-work
    sweep); a member still blocked by an EARLIER member of this same
    cluster cannot legally start in the same pass -- the ticket state
    machine's own transition guard refuses an open blocker, and becoming
    IN_PROGRESS is not the same as the blocker CLOSING -- so it is left
    queued/planned and reported as deferred, startable with an ordinary
    `frob ticket start <id>` in this SAME already-leased worktree the
    moment its blocker actually closes. Each started member's own lease
    releases individually, exactly like any ordinary single-ticket lease;
    this adds no new release mechanism, only a shared worktree/warmup."""
    from frob.tickets import _load_one, load_queue
    from frob.tickets._brief import cluster_descendants

    cluster_id = cfg.ticket_cluster
    assert cluster_id is not None  # caller-checked

    loaded = _load_one(root, cluster_id)
    if loaded.is_err:
        _log.error("ticket work --cluster failed: %s", loaded.danger_err)
        sys.exit(1)

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket work --cluster failed: %s", queue_result.danger_err)
        sys.exit(1)
    members = cluster_descendants(queue_result.danger_ok, cluster_id)
    if not members:
        _log.error(
            "ticket work --cluster %s failed: no dispatchable descendant "
            "leaf tickets found (all done/dropped, or all blocked by "
            "something outside the cluster)",
            cluster_id,
        )
        sys.exit(1)

    _refuse_on_cluster_scope_conflict(root, cluster_id, members)

    # frob:ticket T-1790
    if _root_is_itself_a_nested_worktree(root.resolve()):
        _log.error(
            "ticket work --cluster: %s refused -- %s is itself a "
            "dispatched agent worktree (nested under another "
            ".claude/worktrees/ entry); creating a worktree UNDER it "
            "would nest a second level, which dies silently if the "
            "parent is ever retired (T-1790, the T-1766 incident) -- "
            "run `frob ticket work --cluster` from the PRIMARY checkout "
            "instead",
            cluster_id,
            root,
        )
        sys.exit(1)

    worktree = (
        cfg.ticket_worktree or _default_cluster_worktree(root, cluster_id)
    ).resolve()
    _worktree_add_or_reuse(root, worktree, cluster_id)
    _ensure_worktree_fresh(worktree, cluster_id)
    _build_natives_for_work(worktree, cluster_id)

    _log.info(
        "ticket work --cluster %s: worktree ready at %s -- starting %d "
        "member ticket(s): %s",
        cluster_id,
        worktree,
        len(members),
        [t.id for t in members],
    )
    deferred = _start_cluster_members(worktree, cluster_id, members, cfg)
    if deferred:
        _log.info(
            "ticket work --cluster %s: %d member(s) started now, %d "
            "deferred pending an intra-cluster blocker: %s",
            cluster_id,
            len(members) - len(deferred),
            len(deferred),
            list(deferred),
        )


# frob:ticket T-1175
# frob:ticket T-1790
# frob:tests tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree.test_work_refuses_from_a_nested_worktree  # noqa: E501
def _work(root: Path, cfg: AppConfig) -> None:
    """`frob ticket work <id> [--worktree PATH]` (T-1175): the one-verb
    replacement for playbook section 0 steps 1-2 plus `start` -- create or
    reuse the ticket's own worktree, merge `main` into it for freshness,
    build natives, then run the exact same `_start` transition+sweep
    `frob ticket start` already runs, now against the worktree instead of
    whatever `root` happened to be. `--worktree` overrides the default
    `.claude/worktrees/<id-lowercased>` path (`_default_work_worktree`) for
    a caller that wants a differently-named or differently-located
    worktree; `--foreground`/`--steal` pass through to `_start` unchanged.
    Every step here is a REUSE of existing machinery (worktree add/merge
    via plain git, `build_natives`, `_start`) -- no new subsystem, per the
    T-1175 user directive this ticket implements verbatim.

    `--cluster <epic-or-story-id>` (T-1243) dispatches to `_work_cluster`
    instead: the same worktree-warmup/natives-build steps run ONCE for the
    whole cluster rather than once per ticket."""
    if cfg.ticket_cluster is not None:
        _work_cluster(root, cfg)
        return

    if cfg.ticket_id is None:
        _log.error("frob ticket work requires <id> or --cluster <epic-or-story-id>")
        sys.exit(1)

    # frob:ticket T-1790
    if _root_is_itself_a_nested_worktree(root.resolve()):
        _log.error(
            "ticket work: %s refused -- %s is itself a dispatched agent "
            "worktree (nested under another .claude/worktrees/ entry); "
            "creating a worktree UNDER it would nest a second level, "
            "which dies silently if the parent is ever retired (T-1790, "
            "the T-1766 incident) -- run `frob ticket work` from the "
            "PRIMARY checkout instead",
            cfg.ticket_id,
            root,
        )
        sys.exit(1)

    worktree = (
        cfg.ticket_worktree or _default_work_worktree(root, cfg.ticket_id)
    ).resolve()
    _worktree_add_or_reuse(root, worktree, cfg.ticket_id)
    _ensure_worktree_fresh(worktree, cfg.ticket_id)
    _build_natives_for_work(worktree, cfg.ticket_id)

    _log.info(
        "ticket work: %s worktree ready at %s -- starting", cfg.ticket_id, worktree
    )
    _start(worktree, cfg)


def _start(root: Path, cfg: AppConfig) -> None:
    """Transition to in-progress (auto-planning a queued ticket first) and
    run the pre-work sweep. Starting a ticket that is ALREADY in-progress is
    a hard error, not a silent no-op or refresh (T-0215): `frob ticket
    sweep <id>` already exists as the idempotent refresh path, so re-running
    `start` on an in-progress ticket is treated as a coordinator mistake and
    named explicitly, pointing at `sweep` instead of quietly duplicating it.

    T-0835: also refuses (a) a ticket already in a terminal state (done/
    dropped) and (b) a ticket holding a LIVE lease pinned to a DIFFERENT
    worktree, both before the in-progress check above -- either can be true
    while this worktree's OWN ledger view still shows an earlier state (the
    double-dispatch incident this ticket fixes), so both must be checked
    independently of local ticket state. `--steal` (`cfg.ticket_steal`)
    overrides (b) only; (a) has no override, a terminal ticket is never
    restartable."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket start requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="start")
    _refuse_if_terminal(root, cfg.ticket_id, ticket)
    _refuse_if_foreign_live_lease(root, cfg.ticket_id, steal=cfg.ticket_steal)

    if ticket.state == TicketState.IN_PROGRESS:
        _log.error(
            "ticket start failed: %s is already in-progress -- run "
            "`frob ticket sweep %s` to refresh the pre-work sweep instead",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    _refuse_over_broad_scope_on_start(root, ticket)
    _refuse_on_scope_lease_collision(root, cfg.ticket_id, ticket)

    ticket = _auto_plan_if_queued(root, cfg.ticket_id, ticket)

    transitioned = transition(root, cfg.ticket_id, TicketState.IN_PROGRESS)
    if transitioned.is_err:
        _log.error("ticket start failed: %s", transitioned.danger_err)
        sys.exit(1)

    # frob:ticket T-1054
    # `transition` above wrote the queued/planned -> in-progress line into
    # `root`'s tickets.md but never committed it -- commit it NOW, the same
    # way `land` already owns its own ledger commits, so `root` never sits
    # dirty between this `start` returning and the next `frob ticket land`
    # (any worktree) running its DirtyMain check. A commit failure is a
    # hard stop, loudly reported with the exact recovery command, not a
    # silently-swallowed warning -- see `commit_start_transition`'s
    # docstring for the recurring incident this closes.
    from frob.tickets._leases import commit_start_transition

    committed = commit_start_transition(root, cfg.ticket_id)
    if committed.is_err:
        sys.exit(1)

    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="started")

    # frob:ticket T-1645
    _warn_scope_breadth_on_start(root, transitioned.danger_ok)

    # frob:ticket T-0474
    # By default `start` is now just the state transition above -- the
    # pre-work sweep (a synchronous whole-repo dup+xref scan, 57s on this
    # repo's /mnt/c checkout) runs in the BACKGROUND instead of blocking the
    # command. `--foreground` opts back into the old synchronous behavior
    # (useful for a script/test that wants the sweep guaranteed recorded the
    # instant `start` returns). Either way, `frob ticket sweep <id>` remains
    # the always-available, always-synchronous way to (re)record it, so
    # PRE001 stays satisfiable regardless of how `start` recorded it.
    if cfg.ticket_foreground:
        _run_sweep(root, transitioned.danger_ok)
    else:
        _spawn_background_sweep(root, cfg.ticket_id)


def _spawn_background_sweep(root: Path, ticket_id: str) -> None:
    """Launch `frob ticket sweep <ticket_id>` as a detached background
    process against `root` (T-0474) -- `start` returns as soon as this is
    spawned, without waiting for the sweep (dup scan + xref + scope digest)
    to finish. `start_new_session=True` detaches it from this process's
    session so it keeps running after the `start` CLI invocation exits;
    stdout/stderr are discarded (the sweep's own `record_prework` call is
    the durable side effect a caller cares about -- `frob check`'s PRE001
    gate, or a later `frob ticket sweep`/`frob ticket show`, is how a
    caller observes whether it has landed yet, not this process's output).

    Best-effort: if spawning itself fails (e.g. `sys.executable` refused by
    a locked-down sandbox), this logs a warning and falls back to running
    the sweep synchronously right here -- `start` must never silently skip
    recording a sweep at all, only ever trade "instant" for "eventually".

    Honors the repo-wide exec kill switch (`FROB_DISABLE_EXEC`, T-0200):
    when set, no process is spawned at all and the sweep runs
    synchronously in-process, keeping `may "exec"` on the `cli` node a
    genuinely switchable capability (design/frob.strata, T-0474)."""
    if not exec_enabled():
        _log.info(
            "ticket start: %s exec kill switch (%s) set -- running the "
            "pre-work sweep synchronously in-process",
            ticket_id,
            EXEC_KILL_SWITCH_ENV,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    try:
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "frob",
                "ticket",
                "sweep",
                ticket_id,
                "--path",
                str(root),
            ],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _log.warning(
            "ticket start: %s background sweep spawn failed (%s) -- "
            "running it synchronously instead",
            ticket_id,
            exc,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    _log.info(
        "ticket start: %s pre-work sweep launched in the background -- "
        "`frob ticket sweep %s` re-runs it synchronously if needed sooner",
        ticket_id,
        ticket_id,
    )


def _sweep_cmd(root: Path, cfg: AppConfig) -> None:
    """Re-record the pre-work sweep for an in-progress ticket (scope widened)."""
    from frob.tickets import TicketState

    if cfg.ticket_id is None:
        _log.error("frob ticket sweep requires <id>")
        sys.exit(1)
    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="sweep")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error("ticket sweep: %s is not in-progress", cfg.ticket_id)
        sys.exit(1)
    _run_sweep(root, ticket)


# frob:ticket T-1934
def _log_reconcile_intents_and_unlanded_work(report: "ReconcileReport") -> None:
    """The orphaned-land-intent (T-0456) and unlanded-branch-work (T-1934)
    halves of `_reconcile_cmd`'s summary, split out to stay under ARCH001's
    per-function line budget once T-1934 added a fourth anomaly class."""
    if report.orphaned_land_intents:
        intent_verb = "cleared" if report.applied else "would clear"
        _log.info(
            "reconcile: %s %d orphaned land intent(s) (crash/interrupt mid-land): %s",
            intent_verb,
            len(report.orphaned_land_intents),
            list(report.orphaned_land_intents),
        )
    else:
        _log.info("reconcile: no orphaned land intents found")

    # Report-only, always -- no verb heals this anomaly class (see
    # `ReconcileReport.unlanded_branch_work`'s own docstring for why: a
    # dead agent's branch is never landed unattended).
    if report.unlanded_branch_work:
        _log.info(
            "reconcile: %d branch(es) carry unlanded ticket work "
            "(finished on a branch, not terminal on main): %s",
            len(report.unlanded_branch_work),
            list(report.unlanded_branch_work),
        )
    else:
        _log.info("reconcile: no unlanded branch work found")


# frob:ticket T-0476
def _reconcile_cmd(root: Path, cfg: AppConfig) -> None:
    """`frob ticket reconcile [--apply] [--remove-orphans]`: report (and,
    with `--apply`, heal) T-0476's two ticket<->worktree binding anomalies,
    plus T-0456's orphaned-`land`-intent anomaly and T-1934's unlanded-
    branch-work anomaly (the latter two logged by `_log_reconcile_intents_
    and_unlanded_work`). Always logs a human-readable summary; exits 0
    whether or not anomalies were found (finding an anomaly is not itself
    a command failure -- only a real error loading the ledger is)."""
    from frob.tickets import reconcile

    result = reconcile(
        root,
        apply=cfg.ticket_reconcile_apply,
        remove_orphans=cfg.ticket_reconcile_remove_orphans,
    )
    if result.is_err:
        _log.error("ticket reconcile failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    verb = "requeued" if report.applied else "would requeue"
    if report.requeued_tickets:
        _log.info(
            "reconcile: %s %d stale in-progress hold(s): %s",
            verb,
            len(report.requeued_tickets),
            list(report.requeued_tickets),
        )
    else:
        _log.info("reconcile: no stale in-progress holds found")

    if report.orphan_worktrees:
        removed_verb = "removed" if report.removed_orphans else "flagged (not removed)"
        _log.info(
            "reconcile: %s %d orphan worktree(s) (no lease): %s",
            removed_verb,
            len(report.orphan_worktrees),
            list(report.orphan_worktrees),
        )
    else:
        _log.info("reconcile: no orphan worktrees found")

    _log_reconcile_intents_and_unlanded_work(report)


# frob:ticket T-1866
# frob:doc docs/modules/tickets.md#mega-glob-scope-refused-at-start-t-1866
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_refuses_over_broad_scope  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_over_broad_scope_ack_bypasses_refusal  # noqa: E501
def _refuse_over_broad_scope_on_start(root: Path, ticket) -> None:  # noqa: ANN001
    """T-1866: `sys.exit(1)` if `ticket`'s declared scope contains a
    mega-glob (the SAME breadth measure TICK009/`large_glob_warnings`
    already computes -- a glob whose match set exceeds `scope_breadth_
    context`'s threshold, or a chronically-broad literal, never the bare
    presence of `**` in the spelling) and the ticket has not opted out via
    `frob ticket scope-ack` (`ticket.scope_breadth_ack`, T-1484).

    Promotes T-1645's existing `_warn_scope_breadth_on_start` WARN-only
    nudge to a hard refusal at the one point the information exists to
    narrow correctly (the author has the code open) and before the
    damage begins (a mega-glob lease locking out every other agent from
    that tree the instant this ticket transitions to in-progress). This
    ADDS NO NEW MECHANISM: `large_glob_warnings` is unchanged, and
    `scope-ack` (already built for a genuinely broad epic) is the escape
    hatch reused wholesale rather than inventing a second waiver family.
    A `QUEUED` ticket is never checked here (start always transitions OUT
    of queued/planned, so a queued ticket never reaches this call) --
    T-1645's "a queued scope is a prediction, not yet demandable"
    reasoning is preserved unchanged, just by construction rather than by
    a separate state check."""
    if ticket.scope_breadth_ack:
        return
    from frob.tickets import large_glob_warnings

    warnings = large_glob_warnings(ticket, root)
    if not warnings:
        return
    for warning in warnings:
        _log.error("ticket start failed: %s", warning)
    _log.error(
        "ticket start failed: %s carries %d over-broad scope entr%s -- "
        "narrow it (`frob ticket scope %s --remove '<glob>' --add "
        "'<file>' --reason '...'`), or if this ticket's honest scope "
        "really is a package glob (a genuine epic/umbrella), acknowledge "
        "it explicitly: `frob ticket scope-ack %s --reason '...'`",
        ticket.id,
        len(warnings),
        "y" if len(warnings) == 1 else "ies",
        ticket.id,
        ticket.id,
    )
    sys.exit(1)


# frob:ticket T-1880
# frob:ticket T-1894
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_refuses_scope_colliding_with_other_in_progress_lease  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_allows_disjoint_scope  # noqa: E501
# frob:waive AFFECT001 reason="T-1894: fix is a pure type-correctness change (wrap the \
# queue Mapping in dict() before calling scope_lease_conflict, no behavior change) -- \
# docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473 already describes \
# scope_lease_conflict's queue param generically and needs no content update, but \
# re-acking requires writing frob.lock, which T-1883 holds a live lease on for the \
# duration of its own DUP001 work in this same file cluster; remove this waiver and \
# ack normally once that lease clears"
# frob:waive DRIFT001 reason="T-1894: same dict()-wrap type-only fix as the AFFECT001 \
# waiver above; frob.lock is leased by T-1883 for the duration of this ticket, so the \
# body digest cannot be re-acked here without fighting that lease; remove this waiver \
# and ack normally once T-1883 lands"
def _refuse_on_scope_lease_collision(root: Path, ticket_id: str, ticket) -> None:  # noqa: ANN001
    """`sys.exit(1)` if `ticket`'s declared scope (as filed, BEFORE this
    call grants its own lease) overlaps another ALREADY in-progress
    ticket's live lease (T-1880).

    `scope --add` (T-1868) already refuses this shape for a scope WIDENED
    after `start` -- but nothing refused it when the collision was already
    present in the ticket's ORIGINAL FILED scope and the ticket simply ran
    `start`, the door every real dispatch goes through. Confirmed live on
    this repo's own main: T-1851 declared `src/frob/app/config.py` in its
    filed scope and started AFTER T-1870 already held a live lease on the
    same path -- `start`'s guard chain checked whether T-1851 itself held a
    lease elsewhere and whether its OWN scope was over-broad, but never
    whether its scope collided with T-1870's.

    Calls `frob.tickets._scope.scope_lease_conflict` -- the SAME shared
    predicate `mutate_scope`'s `--add` validation now also calls, checked
    via the live cross-worktree lease side-channel (`read_all_leases`, no
    merge needed) with `own_scope=()` (a grant-time check has no
    pre-existing granted subset to exempt against, unlike `--add`'s T-0485
    exemption). Best-effort: a queue-load failure here degrades to no
    refusal rather than blocking `start` on an unrelated I/O problem --
    `_load_ticket_or_exit` above already proved the queue loads at least
    once this invocation, so a failure here would be a genuinely
    unexpected second read, not the common case."""
    from frob.tickets import load_queue
    from frob.tickets._scope import scope_lease_conflict

    queue_result = load_queue(root)
    if queue_result.is_err:
        return
    conflict = scope_lease_conflict(
        ticket_id, ticket.scope, dict(queue_result.danger_ok.tickets), root=root
    )
    if conflict is None:
        return
    holder_id, holder_glob = conflict
    _log.error(
        "ticket start failed: %s's declared scope collides with "
        "in-progress %s's lease on %r -- resolve the collision (narrow "
        "this ticket's scope via `frob ticket scope %s --remove/--add`, "
        "or coordinate with %s) before starting",
        ticket_id,
        holder_id,
        holder_glob,
        ticket_id,
        holder_id,
    )
    sys.exit(1)


# frob:ticket T-1645
# frob:ticket T-1866
# frob:doc docs/modules/gates.md#tick009tick010-t-0714
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_over_broad_scope_ack_bypasses_refusal  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_precise_scope_warns_nothing  # noqa: E501
def _warn_scope_breadth_on_start(root: Path, ticket) -> None:  # noqa: ANN001
    """T-1645: surface TICK009's over-broad-scope nudge directly at `frob
    ticket start` -- "your scope matches N files, narrow it now" is far
    more actionable in the moment the author has the code open (and just
    entered `IN_PROGRESS`, so `_tick009_scope_breadth_nudges` starts
    evaluating this ticket on the very next `frob check` anyway) than a
    warning that accumulates silently in a full-repo check nobody reads
    per-ticket. Purely a disclosure -- never blocks or exits nonzero;
    `TICK009` itself (a WARN-severity gate finding) is the only thing
    that actually gates anything here, and narrowing scope after seeing
    this is `frob ticket scope <id> --add/--remove`, not something this
    function does for the caller."""
    from frob.tickets import large_glob_warnings

    for warning in large_glob_warnings(ticket, root):
        _log.warning("ticket start: %s", warning)


# frob:ticket T-0354
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_foreground_runs_sweep_synchronously  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_spawns_detached_sweep_subprocess  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_popen_failure_falls_back_to_synchronous_sweep  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_exec_kill_switch_forces_synchronous_sweep  # noqa: E501
def _run_sweep(root: Path, ticket) -> None:  # noqa: ANN001
    """Record the pre-work sweep (dup + xref + scope digest) for `ticket`.

    Delegates to `frob.gates.sweep_ticket` (T-0236's flagged follow-up,
    closed by T-0354): this call site used to carry its own copy of the
    xref loop with the same two bugs `sweep_ticket` fixed for T-0240 -- an
    unbounded `xref(symbol, root)` re-walk of the WHOLE tree per scope
    glob regardless of the per-pattern scan path, and a
    `Path(pattern).stem` guess that fed glob syntax (`"**"`, `"__init__"`)
    into xref as if it were a real symbol name. `src/frob/app/**` was out
    of scope for T-0240, so this copy kept both bugs live until now;
    delegating collapses the duplication instead of porting a second copy
    of the same fix.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(root, ticket)
    if swept.is_err:
        _log.error("pre-work sweep recording failed: %s", swept.danger_err)
        sys.exit(1)

    sweep = swept.danger_ok
    _log.info(
        "swept %s: dup_findings=%d xref_hits=%d",
        ticket.id,
        sweep.dup_findings,
        len(sweep.xref_hits),
    )


def _attach(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import AttachmentSource, attach

    if cfg.ticket_id is None:
        _log.error("frob ticket attach requires <id>")
        sys.exit(1)

    # No path means "read from clipboard" -- but a non-interactive agent
    # session has no clipboard to paste from, and would otherwise hang or
    # spawn a clipboard backend that can never produce an image (T-0098).
    if cfg.ticket_attach_path is None and not sys.stdin.isatty():
        _log.error(
            "frob ticket attach %s: no path given and stdin is not a TTY "
            "(non-interactive session cannot paste from the clipboard); "
            "pass an explicit file path: frob ticket attach %s <path>",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    source = AttachmentSource(path=cfg.ticket_attach_path)
    result = attach(root, cfg.ticket_id, source, caption=cfg.ticket_caption)
    if result.is_err:
        _log.error("attach failed: %s", result.danger_err)
        sys.exit(1)
    attachment = result.danger_ok
    _log.info("attached %s (sha256=%s)", attachment.path, attachment.sha256)


# frob:ticket T-0081
# frob:ticket T-1132
def _block(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import _load_one, is_valid_ticket_ref
    from frob.tickets._store import write_ticket

    if cfg.ticket_id is None or cfg.ticket_by is None:
        _log.error("frob ticket block requires <id> and --by")
        sys.exit(1)

    # T-1132: `--by` becomes a `blocked_by` entry via `model_copy` below,
    # which pydantic never re-validates (model_copy is documented to skip
    # validation entirely, unlike `model_validate`/direct construction) --
    # this is the ONE CLI verb that appends to an EXISTING ticket's
    # `blocked_by` post-creation, so it is the exact site the T-0380
    # incident (an empty-string blocked_by entry left a ticket silently
    # undoable for days) can still slip through even with
    # `Ticket`/`TicketSpec`'s own field validators in place. Refuse here,
    # by hand, before the write ever happens.
    if not is_valid_ticket_ref(cfg.ticket_by):
        _log.error(
            "frob ticket block: --by %r is not a valid ticket id "
            "(expected T-#### or T-draft-<8 hex chars>)",
            cfg.ticket_by,
        )
        sys.exit(1)

    loaded = _load_one(root, cfg.ticket_id)
    if loaded.is_err:
        _log.error("block failed: %s", loaded.danger_err)
        sys.exit(1)
    ticket = loaded.danger_ok
    updated = ticket.model_copy(
        update={"blocked_by": ticket.blocked_by + (cfg.ticket_by,)}
    )
    # frob:channel f_cli_tickets
    # design/frob.strata's `flow f_cli_tickets : cli -> tickets_ledger` --
    # this is one of the cli-layer write sites into the ticket ledger.
    written = write_ticket(root, updated)
    if written.is_err:
        _log.error("block failed: %s", written.danger_err)
        sys.exit(1)
    _log.info("%s now blocked by %s", cfg.ticket_id, cfg.ticket_by)


# frob:ticket T-0215
# frob:ticket T-1005
