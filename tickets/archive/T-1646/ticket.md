---
id: T-1646
title: 'LARGE001 remainder: 52 oversized files T-1420 disclosed but did not attempt'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- design/frob.strata
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1646's own gates/_fix_engine.py split moved fix_fmt001/fix_reg010/fix_rel002/fix_sys104/fix_sys100/fix_e501/fix_cov002/fix_waive004/fix_suppress001
    to new sibling modules; this doc's frob:describes anchors for those symbols must
    follow the move or they drift
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression
- tests/test_gates.py::TestAutofixManifest::test_apply_tier_a_fixes_clears_manifest_on_clean_finish
- tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip
designated_repro_test: null
threat: null
component: null
---
T-1420 closed having split ONE file (src/frob/vet/_capability_typescript.py, 1275 lines, by pipeline phase). Its Done report honestly disclosed that 52 files still exceed the LARGE001 threshold and were not attempted. That remainder was never filed, so closing T-1420 removed it from the queue entirely -- 54 warnings with no owner.

This ticket is that owner. Named in T-1420's report as still needing a seam read:
- src/frob/gates/__init__.py (7627 lines)
- src/frob/tickets/_land.py (2688)
- src/frob/tickets/_store.py (2260)
- src/frob/tickets/_models.py (2063)
- src/frob/strata/_selfconform.py (1911)
- two Rust natives files
- ~45 more

Method, carried forward from T-1420 because it worked: a split is only worth doing when the pieces have a coherent reason to be separate. Splitting to get under a line count produces two arbitrary halves and makes the code harder to follow -- worse than the warning. For each file either find the real seam (a cohesive responsibility, a pipeline phase) or state plainly that no honest seam exists and waive with that reasoning.

Prioritise by edit frequency, not by size: a 7627-line file nobody touches costs less than a 900-line file three agents edit every wave. `git log --format=%H --name-only` over the last few hundred commits gives the ranking.

Watch for the two side effects T-1420's split produced, both of which turned main red after it landed:
- a new module outside every strata node's code= glob (SELFAUDIT001, SYS102)
- prose separated from its frob:invariant anchor, so the half carrying the narrative trips INV006

Both are cheap to fix if anticipated and annoying if discovered at land time. Bind the new file into the self-model and check where the invariants live BEFORE finishing each split.