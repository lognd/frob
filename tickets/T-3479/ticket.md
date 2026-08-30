---
id: T-3479
title: 'PERF005 false positive: bare-short-name match on unrelated ''new'' fns (strata-core/src/graph/model.rs:257)'
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
- src/frob/perf/_recursion.py
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
found while working T-3477: strata-core/src/graph/model.rs:257 (Graph::new) is flagged PERF005 'recursive call to new with no provable termination measure', but Graph::new is not recursive at all -- its body calls BTreeMap::new()/Vec::new(), unrelated external types. _recursive_pairs's mutual-recursion check (src/frob/perf/_recursion.py) matches candidate callees by bare short name only within (path, enclosing_scope); '::'-qualified paths like BTreeMap::new()/Vec::new() are not receiver-aware-excluded the way '.'-qualified self/super calls are (_is_receiver_aware_call only checks the token before an identifier is '.', not '::'), so a free-standing Rust fn named 'new' at file scope gets falsely paired with GraphSchema::new in the same file (both file-scope 'new' fns, same (path, scope)=='' key) via the ::-qualified stdlib new() calls inside its own body reading as a same-name callee. Fix: treat '::' the same as '.' in _is_receiver_aware_call (or otherwise exclude qualified-path calls from the bare-name candidate set) so a Type::method() call is never mistaken for a same-file recursive/mutual-recursion callee. Left un-annotated in T-3477 rather than adding a dishonest frob:invariant terminates directive to a non-recursive function.