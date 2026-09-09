---
id: T-4343
title: Unscoped gate returns different error sets for the same commit under concurrency
state: in-progress
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
body_changes:
- mode: append
  reason: Record the graph-cache lead plus the docstring contradiction the fixer must
    resolve first
  actor: logan
  at: '2026-09-08'
  old_length: 2913
  new_length: 6179
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



## Investigation lead and the evidence that complicates it (coordinator, 2026-09-08)

The implementer whose ticket surfaced this divergence supplied a concrete lead.
Recorded here with the parts that were MEASURED separated from the parts that were
INFERRED, plus a contradiction found afterwards that the fixer must resolve first.

RULED OUT BY DIRECT READING, not inference: the gate-level result cache is not
involved. The invariant gate is explicitly excluded from the cacheable allowlist by
its own comment (it bundles a root-scanning sub-check), and the references gate
appears in neither cacheable allowlist. So neither flaky rule passes through that
layer.

ALSO RULED OUT: the invariant registry itself. Loading the invariants reads the
invariant files straight off disk on every call with no caching, and a direct call
loaded the new invariant cleanly on both a clean and a dirty run. The invariant
side was never in question.

THE LEAD: the shared parsed-graph cache database in the primary checkout. The read
path is deliberately non-blocking -- its own comments say a read has no business
taking the single writer slot, because doing so previously serialised concurrent
invocations behind each other's cache writes. Correct for availability, but it
means a reader can interleave with another process's in-flight rebuild. Directly
observed during the divergent window: repeated "drifted from cache" warnings naming
files OTHER agents were actively touching, while several gate runs and lands were
live against the one shared database. The database is in rollback-journal mode, not
WAL (WAL was retired earlier for unrelated crash reasons), with a zero-byte journal
alongside it.

THE PROPOSED MECHANISM WAS: the rebuild commits per file or per batch, so a reader
opening mid-rebuild sees a snapshot mixing pre- and post-rebuild state -- some
files re-parsed, others not -- which would explain two rules reading a
documentation file's brand-new anchor and inbound link inconsistently.

THE CONTRADICTION, MEASURED AFTERWARDS AND UNRESOLVED. The per-file ingest
function's own docstring states the opposite: that it never commits itself, and
that finalisation commits ONCE for the whole build. A search for a batch-size
constant governing ingest commits finds nothing in that module. So the writer
CLAIMS single-transaction semantics. That is a docstring, not a proof -- this
project has repeatedly found intent recorded in prose that the code does not
enforce -- but it means the proposed mechanism cannot be assumed.

WHAT TO DO WITH THIS. Settle the contradiction by INSTRUMENTING the actual
transaction boundaries during a rebuild rather than by reading comments: confirm
whether the build genuinely commits once, and if it does, the torn-snapshot theory
is wrong and the divergence lives elsewhere -- the staleness detection and the
rebuild-triggering path on the reader side are then the next place to look, since a
reader that gives up and proceeds without a usable graph could plausibly produce a
different finding set. Note there is at least one commit call inside the
lock-retry helper that runs when the connection is owned; establish whether that
path can be reached during a rebuild.

Do not fix a mechanism that has not been demonstrated.
