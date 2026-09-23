---
id: T-4869
title: 'migration: split module strata out of design/frob.strata into design/strata.strata
  with its export surface and accepts'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-5125
- T-4864
- T-4862
- T-4849
- T-4873
- T-4853
parent: T-4844
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
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
- design/strata.strata
- design/frob.strata
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
  at: '2026-09-20'
body_changes:
- mode: set
  reason: 'DOC006: unbacktick the rejected frob sys split spelling (D-M6)'
  actor: logan
  at: '2026-09-19'
  old_length: 1427
  new_length: 1425
designated_repro_test: null
acceptance:
- text: Given the land, when it completes, then design/strata.strata exists with its
    module header, a hand-written export surface, its imports, and its `accepts` clauses.
  evidence: []
- text: Given design/frob.strata after the land, when compared with before, then exactly
    this module's declarations are removed and the duplicate declaration lines among
    them are dropped -- no other module's text moved.
  evidence: []
- text: 'Given the repository at this commit, when the strata checker runs, then it
    is green: the design is in a coherent, fully-split-so-far state, never half-split.'
  evidence: []
- text: Given every cross-module flow involving strata, when the linker runs, then
    each is declared on both sides, or is recorded as a module-owned specific assume
    with owner and expiry naming the concrete mechanism or evidence gap.
  evidence: []
- text: Given the templated-assume gate, when it runs against design/strata.strata,
    then it is green (no assume is a template of another after node/module substitution,
    and expiry dates are not shared across more than N modules).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Migration leaf for module `strata` (members: stratamod). Hub-adjacent: bidirectional with gates, platform, tickets and vet.

One-time reviewed rewrite, by hand, module by module (owner decision D-M6:
there is NO frob sys split tool). Write design/strata.strata with:
  - `module strata` header (dotted path form);
  - an explicit, HAND-WRITTEN export surface: only the names other modules
    actually need. An export list derived mechanically from the tangle is
    refused -- the friction is the feature;
  - `import` lines for exactly the modules this one names, aliased;
  - `accepts <flow> from <module>` on every exported node that receives a
    cross-module flow, per D-M3 and the D-M9 decision on direction;
  - assumes that are module-owned and SPECIFIC (D-M8): the reason text names the
    concrete mechanism or evidence gap for THIS module. Boilerplate CWE assumes
    from SF-08 are NOT carried over; the templated-assume gate must stay green
    on the new file.
Remove exactly the corresponding declarations from design/frob.strata in the
SAME land, dropping the duplicate declaration lines (SF-10, 111 across the
monolith) as they are encountered. The monolith shrinks by exactly this module.
NO half-split state may land on dev: the checker is green before and after.
Any cross-module flow that cannot be made two-sided is recorded as an owned,
specific assume with owner and expiry -- never a bulk waiver.
