---
id: T-draft-a62505d4
title: 'Registry-file class: append-shared, not whole-file leases'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_registry_files.py
- src/frob/tickets/_land.py
- frob.toml
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml
- docs/modules/tickets.md
- tests/test_tickets_registry_files.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_scope.py
  reason: src/frob/tickets/_scope.py whole-file leased by in-progress T-3412; implement
    part (a) via frob.tickets._models.scope_matches's existing LEDGER_PATH-style implicit-scope
    mechanism instead (no scope_lease_conflict edit needed since an implicitly-in-scope
    path is never declared via --add)
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_models.py
  reason: implement (a) via scope_matches's existing LEDGER_PATH-style always-implicit-scope
    mechanism, avoiding the _scope.py whole-file lease held by T-3412
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: design/frob.strata
  reason: both whole-file leased by in-progress T-4221; land-side collision is the
    exact premise this ticket fixes -- proceed without a via entry, waive SELFAUDIT001
    if it fires citing T-4221, note the collision in the READY report for the coordinator
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: both whole-file leased by in-progress T-4221; land-side collision is the
    exact premise this ticket fixes -- proceed without a via entry, waive SELFAUDIT001
    if it fires citing T-4221, note the collision in the READY report for the coordinator
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given an in-progress ticket with no declared scope over docs/modules/gates.md,
    when it edits that file, then scope_lease_conflict never refuses and no --add
    is required
  evidence: []
- text: Given two in-progress tickets both appending distinct lines to a configured
    registry file, when the second lands, then CrossTicketLeakage does not refuse
    (additive-only diff)
  evidence: []
- text: Given an in-progress ticket whose branch deletes or rewrites a line in a configured
    registry file that it did not itself add, when it lands, then CrossTicketLeakage
    still refuses
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Problem, measured all morning: design/frob.strata,
docs/design/registry/capability-via-ratchet.lock.json,
docs/modules/gates.md (rule table) and
docs/design/registry/check-coverage.yaml are append-shared registries
that nearly every gate ticket must touch by adding a line. The scope
lease treats them as whole-file exclusive: one in-progress ticket
holding any of them makes every sibling's `frob ticket scope --add`
refuse with ScopeLeaseConflict and every sibling's land refuse with
CrossTicketLeakage, so 5-8 agents serialize on one file and the
coordinator lands with --allow-cross-ticket by hand.

Fix: introduce a registry-file class (configured in frob.toml under
[tickets], defaulting to those four paths) that is
(a) always implicitly in scope for any in-progress ticket (no lease
    needed, no ScopeLeaseConflict) -- mirrors the existing
    FROB_MANAGED_SIDE_EFFECT_PATHS precedent in
    frob.tickets._scope.scope_lease_conflict, config-driven instead of
    a hardcoded literal set;
(b) exempt from CrossTicketLeakage when the branch's diff to that file
    is additive lines only (no deletions of other tickets' lines);
(c) still refused when the diff deletes or rewrites lines the branch
    did not add.

Positive controls for a, b and c. Docs: docs/modules/tickets.md plus
the gates.md row (itself a registry file, so this ticket's own change
is the first to use the new rule).
