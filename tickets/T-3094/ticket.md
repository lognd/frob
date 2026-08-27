---
id: T-3094
title: 'T-2221 fleet xdist bound never reaches pytest: 0 of 40 running workers carry
  PYTEST_XDIST_AUTO_NUM_WORKERS'
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
- src/frob/tickets/_worktree_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the 0-of-40 measurement, the four candidate broken links, and the
    requirement to verify in running workers rather than by asserting the export was
    printed
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3646
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27 under a live three-agent fleet with three live leases:

    LOAD 41.9   MEM 11.3GB avail   3 live lease(s)
    guidance is 1 agent (SWAP 1.4GB in use)
    37+ concurrent python processes at ~0.6GB RSS each

Then, inspecting `/proc/<pid>/environ` for every running python process:

    python procs inspected = 40
    with PYTEST_XDIST_AUTO_NUM_WORKERS set = 0

ZERO of forty. The T-2221 fleet-aware xdist bound is not reaching a single
actual test run.

THE MACHINERY EXISTS AND LOOKS CORRECT. `src/frob/tickets/_worktree_guard.py`
defines `PYTEST_XDIST_AUTO_NUM_WORKERS_ENV` and `_bounded_xdist_workers(root)`,
and `agent_env_exports` is documented to set it "only when
`_bounded_xdist_workers` detects other live agent leases". Three live leases
were present, so the precondition was satisfied and the bound SHOULD have been
applied. It was not present in any running worker.

This is the shipped-but-not-reachable class, which this repo has hit repeatedly:
a function exists, is exported, is tested, and nothing in the real path calls
it -- or calls it somewhere the value cannot survive to the process that needs
it. Note the mechanism is inherently fragile: the bound is delivered as an
ENVIRONMENT EXPORT that an agent must actually source into the shell that later
invokes pytest. Any step that re-execs, spawns a fresh shell, or runs pytest
through a wrapper that does not inherit that environment silently drops it, and
the failure is invisible -- `-n auto` simply falls back to the machine's core
count, which is exactly what "works fine, just slow" looks like.

DIAGNOSE BEFORE FIXING. The interesting question is WHICH link is broken:
  (a) `agent_env_exports` is not being invoked at all in the current agent
      flow;
  (b) it is invoked and prints the export, but nothing sources it;
  (c) it is sourced, but the pytest invocation happens in a different process
      tree that does not inherit it;
  (d) `_bounded_xdist_workers` returned None despite live leases (a detection
      bug rather than a delivery bug).
Report which, with evidence. Do not fix (b) if the real defect is (d).

WHY THIS MATTERS BEYOND TIDINESS. Load 41.9 on a box whose own fleet tool
advises "1 agent" is the condition that precedes OOM kills here -- this session
has previously lost agents to the WSL OOM killer, and an OOM kill mid-land is
how partial ledger state gets created. The bound is the designed defence and it
is currently inert. It also means every measurement taken under a multi-agent
fleet today was taken under more parallelism than intended.

CONSIDER A LOUDER MECHANISM. An env var that must survive an unknown number of
process hops to take effect is a silent-failure design. A bound that is applied
where pytest is actually invoked -- or a startup assertion that FAILS LOUDLY
when a fleet is detected and no bound is in effect -- would make this class of
regression impossible to ship again. Declaring the boundary rather than
degrading silently is the standing doctrine here.

ACCEPTANCE
- The broken link is identified by name, with evidence, before any fix.
- Under a multi-agent fleet, the bound is verifiably present in the actual
  pytest worker processes. Prove it the way this ticket was measured: inspect
  `/proc/<pid>/environ` (or the equivalent) of RUNNING workers, not by asserting
  that the export was printed.
- Must-stay-quiet: a single agent with no sibling leases is NOT bounded, and
  full-machine parallelism is still available to it.
- If the delivery mechanism is changed, a fleet with no effective bound is
  detected and reported loudly rather than silently falling back to `-n auto`.
