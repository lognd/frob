---
id: T-0673
title: 'registry: cross-file concept dedup - link cross_refs for the 10+ known-duplicate
  concepts, extend to a full pairwise scan'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0346
tier: ticket
sprint: null
scope:
- docs/design/registry/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_group_id_exists
- tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_member_cross_refs_every_other_member
- tests/unit/strata/test_registry_cross_refs.py::TestRejectedPairsStayUnlinked::test_rejected_pairs_not_cross_linked
- tests/unit/strata/test_registry_cross_refs.py::TestReconciliationSplitSectionFullyLinked::test_finding_b_ids_all_linked
designated_repro_test: null
acceptance:
- text: Given the 10 named concepts, when the registry is queried, then each has a
    reviewed cross_refs linkage (either merged to one canonical id or explicitly justified
    as distinct)
  evidence:
  - tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_group_id_exists
  - tests/unit/strata/test_registry_cross_refs.py::TestLinkedGroupsResolveAndAreNavigable::test_every_member_cross_refs_every_other_member
- text: Given a full pairwise scan over all 1950 entries, when it completes, then
    any newly found split is either linked or recorded as a residual finding, not
    silently dropped
  evidence:
  - tests/unit/strata/test_registry_cross_refs.py::TestRejectedPairsStayUnlinked::test_rejected_pairs_not_cross_linked
  - tests/unit/strata/test_registry_cross_refs.py::TestReconciliationSplitSectionFullyLinked::test_finding_b_ids_all_linked
threat: null
component: null
---
RECONCILIATION.md finding (b): Circuit Breaker, Bulkhead, Idempotent Receiver, Anti-Corruption Layer, Value Object, Repository, Timeout, Singleton, Anemic Domain Model, Saga each currently exist as 2-4 unlinked file-local ids (cross_refs: []) across arch-checks.yaml/patterns.yaml/system-design.yaml/supply-chain.yaml. Make a reviewer judgment call per concept (one canonical id with facets, vs genuinely distinct checkable claims that share a name) and wire cross_refs accordingly. Then extend the spot-check to a full pairwise name-similarity scan over all 1950 entries (the prior pass explicitly did not do this) to surface additional splits beyond the 10 named.