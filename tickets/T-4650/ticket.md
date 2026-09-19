---
id: T-4650
title: 'Registry-file class: append-shared, not whole-file leases'
state: done
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
- docs/modules/tickets.md
- tests/test_tickets_registry_files.py
- src/frob/tickets/_models.py
- docs/modules/gates.md
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
- op: remove
  glob: docs/modules/gates.md
  reason: whole-file leased by in-progress T-4116; same premise collision as design/frob.strata/capability-via-ratchet.lock.json
    above
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: docs/design/registry/check-coverage.yaml
  reason: whole-file leased by in-progress T-4112/T-4113; same premise collision
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/modules/gates.md
  reason: leases released (T-4116 landed); dogfood the additive-only registry-file
    rule on this file now (check-coverage.yaml still leased by T-4112)
  actor: logan
  at: '2026-09-19'
evidence:
- tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_empty_scope
- tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_unrelated_scope
- tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_additive_registry_change_is_exempt
- tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_destructive_registry_change_is_not_exempt
- tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_root_returns_default
- tests/test_tickets_registry_files.py::TestRegistryFiles::test_no_frob_toml_returns_default
- tests/test_tickets_registry_files.py::TestRegistryFiles::test_configured_override_replaces_default
- tests/test_tickets_registry_files.py::TestRegistryFiles::test_malformed_value_falls_back_to_default
- tests/test_tickets_registry_files.py::TestRegistryFiles::test_is_registry_file_membership
- tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_non_registry_file_still_requires_declared_scope
- tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_non_registry_path_is_never_exempt
- tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_pure_append_is_additive
- tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_deleted_line_is_not_additive
- tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_file_header_dashes_are_not_removed_lines
- tests/test_tickets_registry_files.py::TestIsAdditiveDiffText::test_empty_diff_is_additive
- tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_pure_append_is_additive
- tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_deleted_line_is_not_additive
- tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_bad_ref_fails_closed
designated_repro_test: null
acceptance:
- text: Given an in-progress ticket with no declared scope over docs/modules/gates.md,
    when it edits that file, then scope_lease_conflict never refuses and no --add
    is required
  evidence:
  - tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_empty_scope
  - tests/test_tickets_registry_files.py::TestScopeMatchesRegistryImplicit::test_registry_file_matches_with_unrelated_scope
- text: Given two in-progress tickets both appending distinct lines to a configured
    registry file, when the second lands, then CrossTicketLeakage does not refuse
    (additive-only diff)
  evidence:
  - tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_additive_registry_change_is_exempt
- text: Given an in-progress ticket whose branch deletes or rewrites a line in a configured
    registry file that it did not itself add, when it lands, then CrossTicketLeakage
    still refuses
  evidence:
  - tests/test_tickets_registry_files.py::TestRegistryLeakageExemptPaths::test_destructive_registry_change_is_not_exempt
evidence_changes:
- old_node: tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff::test_bad_ref_fails_closed
  new_node: ''
  reason: class renamed to TestIsAdditiveDiffText (pure)/TestRegistryFileDiffIsAdditive
    (git spawn) when the subprocess call moved out of _registry_files.py into _land.py
    for SELFAUDIT001
  actor: logan
  at: '2026-09-19'
- old_node: tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff::test_pure_append_is_additive
  new_node: ''
  reason: class renamed to TestIsAdditiveDiffText/TestRegistryFileDiffIsAdditive
  actor: logan
  at: '2026-09-19'
- old_node: tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff::test_deleted_line_is_not_additive
  new_node: ''
  reason: class renamed to TestIsAdditiveDiffText/TestRegistryFileDiffIsAdditive
  actor: logan
  at: '2026-09-19'
- old_node: tests/test_tickets_registry_files.py::TestAdditiveOnlyDiff::test_deleted_line_is_not_additive
  new_node: tests/test_tickets_registry_files.py::TestRegistryFileDiffIsAdditive::test_deleted_line_is_not_additive
  reason: class renamed to TestRegistryFileDiffIsAdditive when subprocess call moved
    to _land.py; duplicate node also exists under TestIsAdditiveDiffText
  actor: logan
  at: '2026-09-19'
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