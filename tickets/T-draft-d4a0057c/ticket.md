---
id: T-draft-d4a0057c
title: 'migration: split module graph out of design/frob.strata into design/graph.strata
  with its export surface and accepts'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-draft-1f0f55cb
- T-draft-a693d397
- T-draft-9d041fdf
- T-draft-27d3ece1
- T-draft-f3b28013
- T-draft-d97a3de1
parent: T-draft-0a0c7b43
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/graph.strata
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the land, when it completes, then design/graph.strata exists with its
    module header, a hand-written export surface, its imports, and its `accepts` clauses.
  evidence: []
- text: Given design/frob.strata after the land, when compared with before, then exactly
    this module's declarations are removed and the duplicate declaration lines among
    them are dropped -- no other module's text moved.
  evidence: []
- text: 'Given the repository at this commit, when the strata checker runs, then it
    is green: the design is in a coherent, fully-split-so-far state, never half-split.'
  evidence: []
- text: Given every cross-module flow involving graph, when the linker runs, then
    each is declared on both sides, or is recorded as a module-owned specific assume
    with owner and expiry naming the concrete mechanism or evidence gap.
  evidence: []
- text: Given the templated-assume gate, when it runs against design/graph.strata,
    then it is green (no assume is a template of another after node/module substitution,
    and expiry dates are not shared across more than N modules).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Migration leaf for module `graph` (members: graphlang, refactor, mutate). Hub: fan-in 8; bidirectional with gates, platform, tickets and vet.

One-time reviewed rewrite, by hand, module by module (owner decision D-M6:
there is NO `frob sys split` tool). Write design/graph.strata with:
  - `module graph` header (dotted path form);
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
