---
id: T-5102
title: 'strata elaborator: per-module elaboration, private-by-default, imports bind
  exports only (no wildcard, no re-export, no global fallback)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-draft-1f0f55cb
- T-5104
parent: T-5081
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_resolve.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_multifile.py
- src/frob/strata/_design_load.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given module B importing `a.b as c` where a.b exports Store, when elaborated,
    then `c.Store` resolves and bare `Store` in B does not resolve.
  evidence: []
- text: Given module B referencing a name a.b declares but does not export, when elaborated,
    then elaboration fails naming the private id, its owning module and the reference
    site.
  evidence: []
- text: 'Given a design with no imports at all, when elaborated, then no cross-module
    name resolves by global fallback -- positive control: a file that relies on today''s
    global uniqueness now fails with a named refusal rather than silently resolving.'
  evidence: []
- text: Given a cross-module reference written as a string path inside an attr or
    glob, when elaborated, then it is refused rather than resolved.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Per-module elaboration (Option D's vehicle). Today src/frob/strata/_multifile.py
merges all parsed Modules into one flat bag and _elaborate.py runs ONCE over the
union, with global name uniqueness as the only rule (_elaborate.py:420-436
_validate_no_duplicates). Replace that with:
  - a new src/frob/strata/_resolve.py that resolves names per module BEFORE any
    merge: alias-qualified cross-module references only, bare names never
    resolve across a module boundary;
  - private-by-default: an id not in the module's export surface is unnameable
    outside it;
  - imports bind only exports, no wildcard, no transitive re-export (importing A
    does not give you A's imports);
  - no global name fallback -- that is today's semantics wearing a module
    keyword, and it must not survive;
  - string-path cross-module references (a dotted name inside an attr or a glob)
    are refused, not silently resolved.
_multifile.py's merge becomes the post-resolution union; _design_load.py feeds
per-module units instead of one bag.
