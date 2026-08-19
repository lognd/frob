---
id: T-2667
title: 'Owner decision needed: break the remaining stats-independent serve/tickets/testing/app
  import cycle (candidates 1/3/4/5 + a missed sixth edge)'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_tools.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-2583. The owner picked candidate 2 (`stats/__init__.py`'s
`from frob.tickets import TicketQueue, TicketState, load_queue`) to break
the 160-node serve/stats/tickets/testing/app CYCLE001 SCC. That edge is now
broken and verified: `frob.stats` no longer appears anywhere in the SCC's
node list on any of the three path shapes (`frob cycle src/frob`, `frob
cycle src`, `frob cycle .` all agree).

**The SCC itself is still there, at the same size (160 nodes).** It is now
closed entirely by edges that never route through frob.stats -- confirmed
by re-measurement, not assumed. T-2583's own contingency text anticipated
only ONE possible holdout (candidate 5, `app/_daemon_proxy.py -> frob.
serve`). That assumption was wrong: measuring the actual current source
(not the original ticket's description) after candidate 2 landed shows the
remaining SCC is closed by AT LEAST FOUR edges, not one:

1. **candidate 1** -- `serve/_tools.py:24`, top-level
   `from frob.tickets import doable, load_queue`. MCP tools would need
   ticket data injected rather than self-loading it (same shape of fix as
   candidate 2, but on a much larger call surface -- `_tools.py` calls
   `load_queue`/`doable` in at least two more places, lines ~110/124/128
   and ~178).
2. **candidate 3** -- `tickets/_land.py`, function-local
   `from frob.testing._models import CollectedTests`. A genuine runtime
   need in land's orphaned-evidence check, not an accidental import --
   noted in the original T-2363 analysis as deliberate.
3. **candidate 4** -- `testing/_coverage_wait.py:163`, function-local
   `from frob.app._daemon_proxy import release_daemon_lease,
   try_daemon_lease`. The daemon-lease fast path, deliberately deferred
   already.
4. **candidate 5** -- `app/_daemon_proxy.py`, several function-local
   `from frob.serve import ...` (socket_path/send_request/DaemonError/
   etc.). The daemon proxy's whole job is talking to frob.serve's socket
   daemon -- this edge is closer to inherent than accidental. The honest
   fix (per the repo owner, noted on T-2583) is extracting shared
   daemon-protocol primitives into a neutral module both `app` and `serve`
   import, mirroring T-2358's own `deploy/_generate_common.py`
   extraction -- not inversion.

**A sixth edge the original T-2363 analysis missed entirely:**
`serve/_tools.py:606`, a second, independent function-local
`from frob.testing import SelectConfig, load_runners, run_selected,
select_tests`. This is a second serve -> testing edge alongside candidate
1's serve -> tickets edge; it was never enumerated as one of the five
original candidates.

**The corrected picture, and why it matters for the next decision:**
candidates 1/3/4/5(+the sixth edge above) are NOT independent, pick-any-one
fixes the way the original five-candidate framing implied. They form a
cycle among `frob.serve`, `frob.tickets`, `frob.testing`, and
`frob.app._daemon_proxy` that is entirely independent of `frob.stats` --
breaking any single one of them might collapse that particular cycle path,
but with this many cross-edges among the same four packages there is no
guarantee doing so collapses the whole 160-node SCC (T-2363's own found-a-
second-edge history on this exact package pair is a direct precedent: a
"the smallest-looking edge is sufficient" assumption has already been
falsified once). Evaluate the remaining edges AS A SET, not one at a time,
before picking the next cut -- re-measure `frob check --only cycle` /
`frob cycle` after any candidate pick, the same way T-2583's own
re-measurement is what surfaced this.

The `frob:waive CYCLE001` declaration at `src/frob/__init__.py` (T-2363)
stays as-is: the SCC is still real and unwaived-live (frob-cycle's own
tool never consults the waiver pipeline, T-2584), but its premise --
"cutting only the smallest-looking edge (stats -> tickets) would not
collapse it" -- needs updating to reflect this ticket's corrected,
measured picture rather than the original five-candidate guess.

Per the repo owner's standing instruction on this SCC ("if that decision
is not obvious, stop and tell me rather than guessing"): this ticket does
NOT pick a candidate. It restates the problem with the corrected, measured
set of remaining edges for the owner to decide from.
