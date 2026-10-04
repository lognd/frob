+++
id = "01M2Y1SS01VNZN6PBX91RWZ0CN"
title = "TICK rule: requeue an in-progress ticket whose recorded worktree or branch is dead"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5121"]
labels = ["milestone:0.533.0"]
scope = ["src/frob/gates/_tickets_gate.py", "src/frob/tickets/_leases.py", "tests/gates_suite/test_tick_dead_worktree.py", "src/frob/gates/_waive.py", "docs/modules/gates.md"]

[[links]]
kind = "blocked-by"
target = "01M2Y1SS00E8EC6M51GZ44WG71"
+++

Measured 2026-09-20 (scratchpad/STRANDED.md): 38 of 54 in-progress tickets were abandoned by dead agents while their worktree directories survived; orphaned_leases in src/frob/tickets/_leases.py returned 0 because liveness is tested by directory existence, not by process or branch activity. Fix: add the next free TICK0xx rule in src/frob/gates/_tickets_gate.py that, for every in-progress ticket, resolves the worktree and branch recorded on the ticket (depends on the start-transition ticket filed alongside this one) and errors when the path is absent, the branch is absent, or no live process holds it (reuse the process-presence verdict in src/frob/tickets/_worktree_sweep.py near line 351), then flips the ticket back to queued through the ledger commit path with a fail-log entry naming the dead worktree. Positive control: a fixture ticket started in a worktree whose directory is then deleted is reported by the rule and is queued again after frob check; a ticket with a live holder is untouched.
