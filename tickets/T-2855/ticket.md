---
id: T-2855
title: 'post-land sweep regression from T-2846: 22 new (rule, file) identit(ies),
  172 finding(s) (COV001, DOC006, DRIFT002, REF001)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/dup-sota-survey.md
- docs/modules/dup.md
- frob-core/src/callgraph.rs
- frob-core/src/exact_regions.rs
- frob-core/src/lib.rs
- frob-core/src/r3.rs
- frob-core/src/r4.rs
- frob-core/src/r5.rs
- tests/test_arch_near_duplicate_native.py
- tests/unit/test_dup_core.py
findings:
- - COV001
  - frob-core/src/callgraph.rs
- - COV001
  - frob-core/src/exact_regions.rs
- - COV001
  - frob-core/src/lib.rs
- - COV001
  - frob-core/src/r3.rs
- - COV001
  - frob-core/src/r4.rs
- - COV001
  - frob-core/src/r5.rs
- - DOC006
  - docs/modules/dup-sota-survey.md
- - DOC006
  - docs/modules/dup.md
- - DRIFT002
  - docs/modules/dup.md
- - DRIFT002
  - frob-core/src/lib.rs
- - DRIFT002
  - tests/test_arch_near_duplicate_native.py
- - DRIFT002
  - tests/unit/test_dup_core.py
- - REF001
  - frob-core/src/callgraph.rs
- - REF001
  - frob-core/src/exact_regions.rs
- - REF001
  - frob-core/src/r3.rs
- - REF001
  - frob-core/src/r4.rs
- - REF001
  - frob-core/src/r5.rs
- - TEST001
  - frob-core/src/exact_regions.rs
- - TEST001
  - frob-core/src/lib.rs
- - TEST001
  - frob-core/src/r3.rs
- - TEST001
  - frob-core/src/r4.rs
- - TEST001
  - frob-core/src/r5.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record no-behavior-change rationale before landing (comment/directive-only
    doc-drift fix)
  actor: logan
  at: '2026-08-22'
  old_length: 5202
  new_length: 5699
evidence:
- tests/unit/test_dup_core.py::TestAptedSimilarity::test_identical_trees_similarity_one
- tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2846 at commit 71951858f145ed3f82784c93adccaadf2cb81cfa found 22 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (22), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 172 actual finding(s) across those 22 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  frob-core/src/callgraph.rs
- COV001  frob-core/src/exact_regions.rs
- COV001  frob-core/src/lib.rs
- COV001  frob-core/src/r3.rs
- COV001  frob-core/src/r4.rs
- COV001  frob-core/src/r5.rs
- DOC006  docs/modules/dup-sota-survey.md
- DOC006  docs/modules/dup.md
- DRIFT002  docs/modules/dup.md
- DRIFT002  frob-core/src/lib.rs
- DRIFT002  tests/test_arch_near_duplicate_native.py
- DRIFT002  tests/unit/test_dup_core.py
- REF001  frob-core/src/callgraph.rs
- REF001  frob-core/src/exact_regions.rs
- REF001  frob-core/src/r3.rs
- REF001  frob-core/src/r4.rs
- REF001  frob-core/src/r5.rs
- TEST001  frob-core/src/exact_regions.rs
- TEST001  frob-core/src/lib.rs
- TEST001  frob-core/src/r3.rs
- TEST001  frob-core/src/r4.rs
- TEST001  frob-core/src/r5.rs

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  frob-core/src/callgraph.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/callgraph.rs::arch_sim_build_b2j
- COV001  frob-core/src/exact_regions.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/exact_regions.rs::build_suffix_array
- COV001  frob-core/src/lib.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/lib.rs::frob_core
- COV001  frob-core/src/r3.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r3.rs::is_numeric_literal
- COV001  frob-core/src/r4.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r4.rs::apted_similarity
- COV001  frob-core/src/r5.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r5.rs::AntiUnifyErr
- DOC006  docs/modules/dup-sota-survey.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  docs/modules/dup.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  docs/modules/dup.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  frob-core/src/lib.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/lib.rs::frob_core
- DRIFT002  tests/test_arch_near_duplicate_native.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  tests/unit/test_dup_core.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF001  frob-core/src/callgraph.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/callgraph.rs::arch_sim_build_b2j
- REF001  frob-core/src/exact_regions.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/exact_regions.rs::build_suffix_array
- REF001  frob-core/src/r3.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r3.rs::is_numeric_literal
- REF001  frob-core/src/r4.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r4.rs::apted_similarity
- REF001  frob-core/src/r5.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r5.rs::AntiUnifyErr
- TEST001  frob-core/src/exact_regions.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/exact_regions.rs::build_suffix_array
- TEST001  frob-core/src/lib.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/lib.rs::frob_core
- TEST001  frob-core/src/r3.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r3.rs::is_numeric_literal
- TEST001  frob-core/src/r4.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r4.rs::apted_similarity
- TEST001  frob-core/src/r5.rs  -> attributed to T-2846 (commit 71951858f145, already closed/dropped -- filed below) via frob-core/src/r5.rs::AntiUnifyErr

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="comment/directive-only fix -- repoints frob:describes/frob:tests edge targets and adds frob:doc comments for pub(crate) helpers T-2846's split newly exposed, zero behavior changed. Verified via a full targeted pytest re-run (tests/unit/test_dup_core.py + tests/test_arch_near_duplicate_native.py, 26/26 passed) and frob natives build (frob_core built cleanly). BUG002 designated-repro requirement does not apply: there is no behavior to reproduce a failure for."