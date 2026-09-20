---
id: T-5110
title: 'migration: split module strata out of design/frob.strata into design/strata.strata
  with its export surface and accepts'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-5125
- T-5104
- T-5102
- T-5087
- T-5114
- T-5091
parent: T-5081
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
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
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: 'DOC006: a rejected CLI form must not appear in backticks in a ticket body;
    the sys-split tool does not exist and was refused by the owner'
  actor: logan
  at: '2026-09-19'
  old_length: 1427
  new_length: 1444
- mode: set
  reason: 'DOC006: planned or rejected CLI forms written as prose so unrelated lands
    are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 1444
  new_length: 1438
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
there is NO a sys-split tool (rejected) tool). Write design/strata.strata with:
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
