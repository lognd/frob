---
id: T-0517
title: dup.db fingerprint cache lacks version/algorithm invalidation key -- stale
  caches silently change find_clones results
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_cache.py
- tests/unit/test_dup_cache.py
- tests/test_dup_cross_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_cache.py
  reason: declared scope was empty at close time; back-filling so SCOPE001's cross-ticket
    exemption (T-0108) recognizes these commits for sibling tickets sharing this worktree
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_dup_cache.py
  reason: declared scope was empty at close time; back-filling so SCOPE001's cross-ticket
    exemption (T-0108) recognizes these commits for sibling tickets sharing this worktree
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_dup_cross_lang.py
  reason: declared scope was empty at close time; back-filling so SCOPE001's cross-ticket
    exemption (T-0108) recognizes these commits for sibling tickets sharing this worktree
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_dup_cache.py::TestFingerprintInvalidation::test_stale_fingerprint_row_is_not_served
- tests/unit/test_dup_cache.py::TestFingerprintInvalidation::test_matching_fingerprint_row_still_served
designated_repro_test: null
threat: null
component: null
---
Incident (2026-07-21): tests/fixtures/dup_cross_lang/.frob/dup.db, an untracked leftover from a pre-T-0487 run, made the landed T-0494 cross-lang R5 tests fail on main while passing in fresh worktrees -- find_clones served 6 stale cache hits and verified 0 pairs. The graph cache.db keys its schema on a frob+grammar version fingerprint (T-0243 pattern) but dup.db does not, so any algorithm change (e.g. _KEYWORDS, r3 canonicalization) silently keeps old fingerprints. Fix: (1) key dup.db rows on the same version fingerprint and invalidate on mismatch; (2) tests must not leak dup.db into tracked fixture dirs -- point find_clones at an isolated cache in tmp_path or clean up. Scope: src/frob/dup/_legacy.py, src/frob/dup/_pipeline.py, tests/test_dup_cross_lang.py.