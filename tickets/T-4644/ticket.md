---
id: T-4644
title: touched-set test selection misses tests that fake a changed function signature
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Systemic gap found while burning down CI run 35448990233: T-4550 changed _shared_check_spawn_fn's signature (added files=/timeout=) and T-4556 changed _probe_land_once's signature (added whole_land=), and BOTH landed cleanly with green touched-set tests -- but each landing broke a DIFFERENT test file (test_ticket_runner_base_forward_t4105.py, tests/unit/verify/test_drain.py respectively) that monkeypatches/fakes that exact function with a hardcoded local stub signature. Neither breakage surfaced until the next full CI run, because frob's touched-set test selection (the pre-land gate) selects tests that CALL a changed symbol (via frob:tests bindings plus call-graph reachability) but has no mechanism to select tests that FAKE/monkeypatch-replace a changed symbol with a same-named local double whose signature can silently drift out of sync. A land whose diff changes a function's signature must also run every test that monkeypatches that same symbol (by grepping for a monkeypatch.setattr call naming that module and symbol, or a lighter heuristic: any local def whose name starts with _fake_ or _stub_ or mock and references the changed symbol's module), not just tests reachable via the call graph. Recommend extending the touched-set selector (or a new gate) to flag or require running tests containing a monkeypatch/setattr target matching a changed function's module+qualname pair whenever that function's signature (not just its body) changes.
