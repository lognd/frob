---
id: T-1519
title: 'cache observational-transparency invariant + property harness: cold==warm
  for every persistent cache'
state: done
kind: invariant
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- invariants/INV-050.md
- tests/_cache_transparency.py
- tests/test_cache_transparency.py
- src/frob/gates/_gate_cache.py
- src/frob/graph/cache.py
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: invariants/INV-050.md
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/_cache_transparency.py
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_cache_transparency.py
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/graph/cache.py
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/tickets/_store.py
  reason: cache observational-transparency invariant + harness scope, per T-1519's
    own body
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_cache_transparency.py::TestGraphCacheTransparency::test_cold_warm_agree_across_random_edits
- tests/test_cache_transparency.py::TestPytestCollectCacheTransparency::test_cold_warm_agree_across_random_edits
designated_repro_test: null
threat: null
component: null
---
Correctness criterion for ALL persistent caches is one theorem: for any repo state S and cache state C, check(S, C) == check(S, empty) -- observational equivalence, stronger than INV-003's rebuildability (deleting is safe) because it asserts a STALE-BUT-PRESENT cache never changes results. Today this is tested pointwise only: tests/test_gate_cache.py has the right shape (cold/warm violation-fingerprint equality incl. a randomized multi-round mutate-and-compare walk, plus the T-1454 ack-invalidation regression); tests/unit/test_lang_artifact_cache.py covers hit/miss only, no equivalence sweep; coverage lock/stamp, tickets-archive-cache.json, pytest-collect.json, hotgraph_sketches.db, check-budget-timing.json have no equivalence coverage at all. Deliverables: (1) new invariants/INV-0xx.md stating the transparency theorem with the full cache inventory enumerated; (2) a shared hypothesis-style property harness (arbitrary edit sequences: touch/rename/delete/revert/content-change, assert cold==warm fingerprints after each step) parameterized over each cache, generalizing test_gate_cache.py's rounds; (3) every cache either covered by the harness or carrying a frob:waive naming a ticket.