---
id: T-4646
title: over_broad_literal_globs re-reads pyproject.toml uncached per doable() lease
  check, blowing TICK008 real-repo budget
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/lang/_nodes.py
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
Found while working T-4649 (memoize _store_mode). After that fix, tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean still exceeds 150s on this repo's real ledger (measured real=2m9s, unchanged from before the _store_mode fix). Faulthandler dump shows the NEW dominant cost is a DIFFERENT instance of the same per-call-re-scan class: doable() -> leased_by() -> _leased_by_one_holder() (src/frob/tickets/_doable.py:671) calls over_broad_literal_globs(root) (src/frob/tickets/_models.py:829) -> declared_source_prefixes(root) (src/frob/lang/_nodes.py:125) -> declared_project_package_name(root) (src/frob/lang/_nodes.py:97), which does tomllib.load() on pyproject.toml FRESH on every call. _leased_by_one_holder's own docstring in _doable.py claims 'literal_globs itself is still cheap to derive once per call site (one pyproject.toml read), unlike files' -- true per call, but this runs once per candidate ticket x lease holder pair inside doable(), same O(tickets x leases) shape as the _store_mode defect T-4649 just fixed. Fix: memoize declared_project_package_name/declared_source_prefixes/over_broad_literal_globs per root the same way (pyproject.toml mtime as the cheap invalidation signal), or hoist the one-time computation out of the per-holder loop in doable()/leased_by() and thread it through as a precomputed argument (same pattern _over_broad_scope_entries's own 'files' parameter already uses per its T-0453 comment). Verify with the same real-repo TICK008 timing test.