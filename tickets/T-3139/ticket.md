---
id: T-3139
title: frob ops process reap and fleet_status disagree about orphaned forkservers;
  the reap verb is right
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured disagreement, the /proc ground truth, and that two deliberate
    copies of the liveness rule desynced within hours
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3856
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27, by running both tools against the same live host state.

    $ uv run frob ops process reap
    frob ops process reap: nothing to reap (no orphaned forkserver found ...)

    $ uv run python scripts/fleet_status.py
    ORPHANED FORKSERVERS: 5 do not have a live `frob check` anywhere in their
    ancestry (T-2443/T-2818 leak signature -- SIGTERM them or wait ...)

Two tools, same machine, same moment, opposite answers about the same five
processes.

GROUND TRUTH, established by reading /proc directly rather than trusting either
tool. All five forkservers have LIVE parents:

    fs=2556879 ppid=2551575   fs=2557141 ppid=2551558
    fs=2557317 ppid=2551586   fs=2557461 ppid=2551696
    fs=2557646 ppid=2551621

and every one of those parents is a pytest-xdist worker:

    /home/logan/projects/frob/.claude/worktrees/series-t3136-t3086/.venv/bin/python
    -u
    -c
    import sys;exec(eval(sys.stdin.readline()))

That is the execnet/xdist remote-exec bootstrap. It is alive, it is legitimate,
and its cmdline contains NO `frob` token at all.

SO THE REAP VERB IS RIGHT AND fleet_status IS WRONG. These are forkservers
spawned under a pytest run (an agent running `frob test` / pytest in its
worktree), not leaked ones. `frob ops process reap` correctly declined to kill
them -- its must-stay-quiet property held under real conditions, which is
exactly what it was built for. `fleet_status.py`'s predicate is too narrow: it
asks for a live `frob check` ANCESTOR, but a forkserver legitimately parented by
an xdist worker under a pytest run has a live parent that is not `frob check`
and never will be.

WHY THIS IS THE IMPORTANT PART: THE TWO COPIES DESYNCED WITHIN HOURS.
T-3072 fixed the ancestry logic in `src/frob/process/_reap.py`. T-3093 fixed the
same class of bug separately in `scripts/fleet_status.py`, DELIBERATELY as a
second copy, because that script has a documented "no frob import" contract and
cannot reuse the module. Both landed today. They already disagree. The T-3072
work itself found THREE copies of a broken cmdline regex in this codebase; this
is the same hazard reasserting itself immediately after being fixed.

So the fix is not only "correct the predicate". It is: decide how these two
liveness rules stay in agreement, given that fleet_status genuinely cannot
import frob. Options worth weighing rather than assuming: generate the script's
copy from the module at build/sync time; have fleet_status shell out to
`frob ops process reap --dry-run --json` and render that; or accept two copies
but add a cross-check test that runs BOTH against a constructed process tree and
FAILS if they disagree. The third is the cheapest and would have caught this.

BLAST RADIUS: this is the fourth measurement-integrity defect found in
`fleet_status.py` today (the cmdline regex that never matched `python -m frob
check`; the LAND LOCK line reporting fd-open waiters as holders; a live
registered worktree reported as a leaked lease, T-3128; and now this). I
personally relayed the forkserver false alarm to the owner several times before
it was diagnosed. That file is the first thing consulted when the fleet looks
wrong, so a wrong line there propagates into every subsequent decision.

ACCEPTANCE
- A forkserver whose live parent is an xdist worker under a pytest run is NOT
  reported as orphaned. Must-stay-quiet fixture built from a real process tree,
  not a mocked one.
- A genuinely orphaned forkserver IS still reported. Must-fire fixture.
- `frob ops process reap` and `scripts/fleet_status.py` agree on the same host
  state. Add a cross-check that fails when they diverge, and state which
  mechanism you chose for keeping them in agreement and why.
- Report whether the other fleet_status predicates have the same too-narrow
  shape (STALE FORKSERVERS and CONCURRENT CHECKS share the substrate).
