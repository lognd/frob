---
id: T-0518
title: 'frob.dup._exhaustiveness: add DUP_CLAIMS r5/typescript entry (T-0494 found
  the proof, no claim registered)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_exhaustiveness.py
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 forced a version bump (0.52.0 -> 0.53.0) when DUP_CLAIMS' public
    digest changed; changelog/lock/stamp are the mandated side effects
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 forced a version bump (0.52.0 -> 0.53.0) when DUP_CLAIMS' public
    digest changed; changelog/lock/stamp are the mandated side effects
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 forced a version bump (0.52.0 -> 0.53.0) when DUP_CLAIMS' public
    digest changed; changelog/lock/stamp are the mandated side effects
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 forced a version bump (0.52.0 -> 0.53.0) when DUP_CLAIMS' public
    digest changed; changelog/lock/stamp are the mandated side effects
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires::test_r5_group_fires_at_every_threshold
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_matrix_covers_every_rung_clone_type_and_language
designated_repro_test: null
threat: null
component: null
---
found while working T-0494: tests/test_dup_cross_lang.py now proves R5 fires cross-language for python/typescript (compute_total/computeTotal, similarity=0.88, every threshold 0.9-0.1), mirroring the r5/rust DUP_CLAIMS entry T-0487 already added (frob.dup._exhaustiveness, proof_test=tests/test_dup.py::TestCrossLanguageR5WithLet.test_r5_fires_across_languages_with_a_let_binding). No matching r5/typescript DUP_CLAIMS entry exists yet -- dup_matrix()'s r5/type3/typescript cell presumably still falls through to DUP_MATRIX_EXCUSES' generic non-python language-gap excuse, which is now stale for this cell specifically (rust already closed, typescript has a firing fixture but no registered claim). Add a DUP_CLAIMS entry for rung=r5, clone_type=3, language=typescript, proof_test=tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires.test_r5_group_fires_at_every_threshold, matching the rust entry's shape. Out of T-0494's declared scope (scope=tests/test_dup_cross_lang.py, docs/modules/dup.md -- does not include src/frob/dup/_exhaustiveness.py).