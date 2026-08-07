---
id: T-0485
title: ticket scope --add refuses narrowing inside a ticket's own pre-existing broad
  overlap (ScopeLeaseConflict)
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets_scope_mutation.py
- docs/modules/tickets.md
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: shared _glob_is_subset helper lives alongside scope_overlap_globs in _models.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_subset_of_own_leased_overlap_is_accepted
- tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_beyond_own_leased_overlap_still_rejected
- tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_concrete_path_under_double_star_is_subset
- tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_wildcard_bearing_narrow_is_never_subset
- tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_concrete_path_outside_broad_glob_is_not_subset
designated_repro_test: null
acceptance:
- text: given a queued ticket whose existing scope glob already overlaps an in-progress
    ticket's lease, when frob ticket scope --add adds a strict subset of that overlap
    (net overlap shrinks or stays equal), then the change is accepted instead of failing
    ScopeLeaseConflict
  evidence: []
threat: null
component: null
---
Found during the 2026-07-21 doable-warning scope-narrowing sweep. frob ticket scope --add checks every added glob against in-progress leases, but queued tickets ALREADY hold broad globs that overlap those same leases (grandfathered at creation). Narrowing 'src/frob/strata/**' down to 'src/frob/strata/_host.py' is refused (ScopeLeaseConflict, e.g. vs T-0263's strata lease) even though the change strictly SHRINKS the overlap. Because scope changes are atomic, the whole narrowing fails and the chronically-over-broad glob (and its doable WARNING) cannot be cleared until the leaseholder lands. Fix: when validating --add, subtract the ticket's own existing scope coverage first -- an add that is a subset of what the ticket already covers can never create NEW contention and must be allowed. Related interplay: ScopeRemoveOrphansEvidence forces a covering --add for recorded evidence, so a ticket whose evidence lies under another ticket's leased tree (T-0160: tests/unit/strata/test_native_staleness.py under T-0263's lease) is fully wedged: cannot remove tests/** without an add, cannot add the evidence path. Tickets left un-narrowed by the sweep, to re-narrow once T-0263/T-0423/T-0460 land: T-0235 T-0261 T-0339 T-0341 T-0383 T-0384 T-0392 T-0393 T-0394 T-0395 T-0401 T-0410 T-0428 T-0439 T-0440; partial leftovers: T-0160 (tests/** stays), T-0461 (add src/frob/render/ post-T-0460).