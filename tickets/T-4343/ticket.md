---
id: T-4343
title: Unscoped gate returns different error sets for the same commit under concurrency
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
THE GATE RETURNS DIFFERENT ANSWERS FOR THE SAME COMMIT, SO NO GATE RESULT IS
TRUSTWORTHY IN EITHER DIRECTION.

MEASURED, AT A FIXED COMMIT, BY TWO INDEPENDENT PARTIES. Five full unscoped runs
were made against one unchanged commit while several agents were working
concurrently. Three reported three errors; two reported one. The two extra
findings were a documentation invariant-anchor rule and a documentation
inbound-reference rule, both against the same file. A direct call to the
invariant rule's own violation function against that file returned empty, agreeing
with the clean runs and not the dirty ones -- so the rule logic is right and the
RUN is what varies.

WHY THIS MATTERS MORE THAN THE TWO FINDINGS. Both readings are dangerous. A
spurious error fails the integration run and sends someone chasing a defect that
does not exist -- which is exactly what happened here, costing a round trip
between a coordinator and an implementer who disagreed about whether a landed fix
had worked. A spurious CLEAN is worse: it is the same shape as every silent-zero
defect this project keeps paying for, and it would let a genuinely broken tree
through the release gate. A gate whose answer depends on machine load is not a
gate.

THE SUSPECTED MECHANISM IS CONTENTION, AND IT IS TESTABLE. The runs that
disagreed were made while multiple other gate runs were live. The check reduces
its worker pool under memory pressure and logs when it does -- a run reduced to
two of twelve workers was observed the same day. Both suspect rules read
DERIVED state (the parsed-graph cache and the invariant registry) rather than
scanning source directly, which is the obvious place for a stale or partially
written per-worker snapshot to change an answer. Confirm or refute that
specifically rather than assuming it: determine whether these rules read a cache
that another concurrent run can be writing, and whether a worker can observe it
half-built.

DO NOT FIX THIS BY SERIALISING EVERYTHING. Slowing every run to make it
deterministic trades one problem for another; the parallelism is load-bearing on
a repository this size. Prefer making the read consistent -- a snapshot a worker
cannot see torn, or a cache read that fails loudly rather than returning partial
data.

FAIL LOUDLY IF THE STATE IS NOT USABLE. If a worker cannot get a coherent view,
the honest outcome is an unmeasured result, which this codebase already has
vocabulary for, not a confident finding computed from partial data and not a
silent omission.

VERIFY BY REPRODUCING THE DIVERGENCE FIRST. Run the gate repeatedly against one
fixed commit under deliberate concurrent load until the answer varies, and record
how often. A fix cannot be trusted until the failure has been produced on demand;
this project has repeatedly found that a defect confirmed only by its absence was
never confirmed at all. Then show the same loop returning a stable answer.
