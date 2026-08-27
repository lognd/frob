---
id: T-3072
title: 'Forkserver orphans persist after T-2880: 23 detected with no live check ancestry,
  and no command reaps them'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the measured orphan count, the missing-reaper gap, and why T-2880's
    fix appears not to reach the leaking spawn path
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 3526
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-26 via `uv run python scripts/fleet_status.py`:

    ORPHANED FORKSERVERS: 23 do not have a live `frob check` anywhere in their
    ancestry (T-2443/T-2818 leak signature)
    STALE FORKSERVERS: 0
    SWAP HELD BY FORKSERVERS: 0.0GB

T-2880 is DONE and diagnosed this exact signature -- an already-started helper
that never sees the PDEATHSIG arming env var, so T-2849's fix does not reach
it. The leak is still producing orphans at roughly the same rate T-2880
measured (it recorded 27 new orphans in the 49 minutes after the fix landed;
23 are live now under a six-agent fleet). So either the fix did not cover the
real spawn path, or a second spawn path exists that T-2880 never identified.
Establish WHICH before changing anything -- "fix it again" without knowing why
the first fix missed is how this becomes a third ticket.

SEPARATE AND INDEPENDENTLY WORTH FIXING: there is NO command that reaps them.
`fleet_status.py` detects the condition precisely and then tells the operator
to "SIGTERM them or wait for the next `frob check`'s own startup reaper". That
is a hand-rolled process kill, which is exactly the class of friction the
owner has standing instructions to systematize rather than repeat. I declined
to hand-roll it today for that reason.

    frob process reap   -- does not exist (`frob` has no `process` subcommand)
    frob clean          -- filesystem artifacts only, no process reaping
    fleet_status.py     -- detects, never remediates; has no reap flag

WHY THE IMPACT LOOKS SMALL BUT IS NOT: swap held is currently 0.0GB, so today
this is cheap. But the same leak previously presented as 94 orphaned
forkservers holding 17GB of swap, and it was diagnosed at the time as "no
progress for N minutes" across the whole fleet -- the symptom is agent stalls,
not an obvious process-count alarm. A detector with no remediation means the
condition is only ever cleared by a human who happens to run fleet_status and
then improvises a kill.

WHAT IS WANTED
- Determine why T-2880's fix does not reach the spawn path that is still
  leaking, and fix THAT path. Report the spawn site.
- A first-class reaper: reaping orphans should be an invocable frob command,
  not an improvised `ps | grep | kill` pipeline. Reuse the ancestry test
  fleet_status.py already implements rather than writing a second one -- two
  copies of a liveness rule is a bug waiting to desync.
- The reaper must be SAFE under concurrency: a forkserver whose parent check
  is alive must never be killed. Under a six-agent fleet there are always live
  ones. Note that `frob check` already has a startup reaper -- extend or expose
  that rather than adding a parallel mechanism.

NOTE ON PORTABILITY: `arm_parent_death_signal` returns False on non-Linux
(src/frob/process/_reap.py, `if sys.platform != "linux"`), so orphan reaping is
disabled entirely on Windows and macOS. T-2916 owns that silent degradation --
do not solve it here, but do not write a reaper that assumes Linux without
declaring the boundary.

ACCEPTANCE
- The still-leaking spawn path is identified by name and fixed; report orphan
  count before and after under a comparable multi-agent load.
- A frob command reaps orphaned forkservers, reusing the existing ancestry
  test rather than duplicating it.
- Must-stay-quiet fixture: a forkserver with a LIVE parent check is never
  reaped.
- Must-fire fixture: a genuinely orphaned forkserver is reaped.
- The command declares its platform boundary loudly rather than silently
  no-opping off Linux.
