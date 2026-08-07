---
id: T-1739
title: 'frob worktree sweep would delete LIVE agents'' worktrees: keep-criteria have
  no liveness check and are exactly inverted'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/worktree_runner.py
- src/frob/tickets/_leases.py
- tests/test_worktree_guard.py
- docs/modules/tickets.md
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001: frob worktree sweep --force/--dry-run CLI doc summary in docs/modules/app.md#runners
    must move with worktree_runner.py::run in the same diff'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess::test_clean_no_lease_recent_head_live_process_kept
- tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess::test_force_overrides_the_live_process_keep
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_none_when_no_process_matches
designated_repro_test: null
threat: null
component: null
---
`frob worktree sweep` would delete the worktree of a LIVE, ACTIVELY
RUNNING agent. Verified by dry-run on 2026-08-07 with four agents
dispatched:

    removed(dry-run) .../agent-a479da6576b368606      <- live agent
    kept:lease(T-1720 1970s) .../agent-ac2dad95d0b2b8809  <- RETIRED agent
    removed(dry-run) .../agent-ad4d34f749af9b292      <- LIVE, mid-ticket
    removed(dry-run) .../agent-aed9d6ca739be6ba6      <- live agent
    swept 5 worktree(s): 4 removed, 1 kept:lease, 0 kept:dirty

The verdicts are exactly inverted. The one worktree it KEEPS belongs to a
retired agent holding a stale lease that is currently blocking two
tickets. The three it would REMOVE belong to agents that are running.

This is T-1715 (`land --finish` deleting the caller's own worktree) at
fleet scale. That bug destroyed one agent permanently, context and all,
and it destroyed exactly one because `--finish` targets a single path.
`sweep` targets every path at once. Running it during a normal
multi-agent drive would have killed three agents simultaneously,
including one mid-implementation on a critical ticket.

ROOT CAUSE: the keep-criteria (lease / dirty / age) have no notion of
"a process is alive in here". They were designed for cleaning up after
agents, and they cannot tell "after" from "during".

- LEASE is unreliable as a liveness signal in both directions. It
  outlives the agent (the retired agent's T-1720 lease has persisted, and
  the doable filter still reports T-1720 as in-progress while the ledger
  says queued -- the lease and the ticket state disagree, which is its
  own bug). And it under-covers: an agent between tickets, or one whose
  start transition has not landed to main, holds no lease at all while
  being entirely alive.
- DIRTY under-covers by design. It reported `0 kept:dirty` for three live
  worktrees, because a well-behaved agent COMMITS ITS WORK to its own
  branch -- which this drive explicitly instructs agents to do as
  stall insurance. Following the guidance makes an agent MORE likely to
  be swept, not less. That inversion is the sharpest edge here.
- AGE keys on HEAD commit time, so an agent that just committed looks
  young and one thinking hard for an hour looks old. It measures the
  wrong thing.

REQUIRED:

1. A LIVENESS CHECK that is actually about processes, not proxies. The
   machinery already exists and is already used for exactly this shape:
   `frob.tickets._leases._proc_cwd` / `_scan_for_live_land_process`
   (T-1619's belt-and-braces scan) answer "is a live process sitting in
   this directory". Reuse it -- do not add a fourth heuristic. If any
   live process has the worktree as its cwd, KEEP, and say which pid.
2. REFUSE-BY-DEFAULT on anything it cannot prove is dead. Sweep is an
   irreversible bulk delete; "I could not determine liveness" must mean
   keep, never remove. `--force` may override for a genuinely wedged
   tree.
3. `--dry-run` MUST STAY the documented first step, and the verdict lines
   must name WHY -- `removed` with no reason is what makes this
   dangerous to trust. `kept:lease(...)` already does this well; the
   removals must too.
4. Reconcile the lease/state disagreement surfaced here: a lease naming
   T-1720 as in-progress while the ledger has it queued means
   `doable --show-blocked` blocks work on a ticket nobody is doing. Either
   the lease is authoritative and the state must follow, or the reverse --
   but they cannot silently disagree, because both are consulted.

REGRESSION COVERAGE must include the real shape: a worktree that is
CLEAN, holds NO lease, has a recent HEAD commit, and has a live process
cwd'd into it -- today's "remove" verdict, and the one that would have
killed three agents. Assert it is kept and the pid is named.