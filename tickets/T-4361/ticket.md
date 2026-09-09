---
id: T-4361
title: Derive _CACHEABLE_PROCESS_GATES completeness check
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
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
Found while working T-4333 (survey of hand-maintained membership lists).

src/frob/gates/__init__.py's _CACHEABLE_PROCESS_GATES (a frozenset naming
which _build_process_jobs entries are safe to serve from the whole-tree
gate cache, per T-1445) has no completeness check against
_build_process_jobs/_ALL_GATES anywhere in the codebase or test suite --
confirmed by exhaustive grep for any assert, set-comparison, or test
mentioning both. Contrast with the immediately adjacent _CANONICAL_GATE_ORDER
and _GATE_STAGE_GROUPS, which both carry an import-time
`assert set(...) == _ALL_GATES` right next to their declaration (the T-4336
model this ticket's parent survey is measuring against).

CONSEQUENCE OF DRIFT: a new _build_process_jobs entry that is cacheable
(reads only the tracked tree plus at most a short hashable scalar tuple, per
_CACHEABLE_PROCESS_GATES's own docstring) but is not added to this frozenset
silently never gets served from the whole-tree gate cache -- it always
re-runs in full. This is NOT a correctness bug (the gate still produces a
correct result) and produces no red CI, no test failure, and no log line --
it is a pure, permanent, invisible perf regression for that one gate on
every check run. Exactly the "silent gap, not merely tested-for" shape named
in T-4333, just landing on perf instead of correctness.

PLAN (not built here -- this ticket is filed by a survey, kind=docs, that
does not refactor): add an import-time assert (or equivalent) binding
_CACHEABLE_PROCESS_GATES's membership decision to _build_process_jobs's own
entries -- e.g. require every _build_process_jobs key to appear in exactly
one of _CACHEABLE_PROCESS_GATES or a small explicit
_KNOWN_UNCACHEABLE_PROCESS_GATES allowlist with a documented reason per
entry (mirroring _COMMITTED_DIFF_GUARDS's exemption_reason field, which is
enforced by tests/ticket_land_suite/test_verify_reset.py's
TestCommittedDiffGuardRegistryCompleteness) -- so a new process-job gate
cannot silently land uncached without an explicit, reviewed decision either
way.
