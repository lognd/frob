---
id: T-3477
title: 'PERF005/PERF008/PERF014: burn down remaining findings after T-2376''s partial
  pass'
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/capability_python.rs
- strata-core/src/graph/model.rs
- src/frob/gates/_rule_id_scan.py
- src/frob/vet/_capability_scan.py
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
T-2376 fixed the 9 Python-file PERF005 unproven-recursion findings via
frob:invariant terminates directives (src/frob/gates/_dead_symbols.py,
src/frob/gates/_walk_lint.py, src/frob/graph/summary.py,
src/frob/vet/_supplychain.py). Measured remaining via
frob check --only perf --json 2026-08-30:

PERF005 (6): frob-core/src/capability_python.rs (5 sites:
collect_target_names:241, resolve_expr:344/380/404, collect_candidates:760),
strata-core/src/graph/model.rs::new:257 -- Rust files, same fix shape (a
termination justification) but needs the Rust-side directive-comment
mechanics confirmed (frob:invariant syntax in // comments) before applying.

PERF008 (83): calls-in-a-loop-with-loop-invariant-arguments across ~35 files
(hooks, scripts, src/frob, tests) -- NOT mechanically fixable in bulk;
several sampled findings (e.g. scripts/fleet_status.py's per-entry
fd.resolve()/iterdir() inside a per-process loop) look like they may be
false positives (the loop variable IS the effective argument, not
invariant) rather than genuine hoist-out-of-loop opportunities -- needs a
per-finding read before fixing or waiving, not a blanket sweep.

PERF014 (2): src/frob/gates/_rule_id_scan.py:389,
src/frob/vet/_capability_scan.py:1228 -- both are single-pattern-per-line
loops the detector flags as pattern-list-shaped; a real fix means
restructuring to one whole-text finditer() call per pattern with line
numbers computed from string offsets, preserving today's per-line
comment-stripping behavior -- a real algorithmic rewrite, not a one-line
change, and risky to get right without dedicated attention.

Severity was NOT promoted to error in frob.toml -- the family is not at
zero. Promote only once every code above is at zero, per T-2376's/the
epic's own acceptance criteria.
