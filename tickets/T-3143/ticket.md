---
id: T-3143
title: refactor split leaves type-annotation-only import sites unrepointed
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
- src/frob/refactor/_transaction.py
- src/frob/refactor/_split.py
- src/frob/refactor/_alias_policy.py
- tests/test_refactor_corpus.py
- docs/commands/refactor.md
- tests/test_refactor.py
evidence_scope:
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/refactor/_scan.py
  reason: reference-collection pass this ticket investigates/widens
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/refactor/_transaction.py
  reason: 'MEASURED: the reference scanner''s per-symbol architecture cannot correctly

    merge a shared "from X import A, B" import line when A and B are both

    being moved together in the same split batch -- scan_references has no

    visibility into sibling symbols in the same operation (documented already

    in _split.py''s _dedupe_equivalent_import_ops docstring). The real fix

    requires _scan.py''s scanner to accept the set of symbols moving together

    in this operation, and _transaction.py/_split.py to actually pass it

    through -- otherwise the scanner-only fix has no live caller and the

    measured defect (25/28 import sites unrepointed) is not actually closed.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/refactor/_split.py
  reason: 'MEASURED: the reference scanner''s per-symbol architecture cannot correctly

    merge a shared "from X import A, B" import line when A and B are both

    being moved together in the same split batch -- scan_references has no

    visibility into sibling symbols in the same operation (documented already

    in _split.py''s _dedupe_equivalent_import_ops docstring). The real fix

    requires _scan.py''s scanner to accept the set of symbols moving together

    in this operation, and _transaction.py/_split.py to actually pass it

    through -- otherwise the scanner-only fix has no live caller and the

    measured defect (25/28 import sites unrepointed) is not actually closed.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/refactor/_alias_policy.py
  reason: 'MEASURED: the reference scanner''s per-symbol architecture cannot correctly

    merge a shared "from X import A, B" import line when A and B are both

    being moved together in the same split batch -- scan_references has no

    visibility into sibling symbols in the same operation (documented already

    in _split.py''s _dedupe_equivalent_import_ops docstring). The real fix

    requires _scan.py''s scanner to accept the set of symbols moving together

    in this operation, and _transaction.py/_split.py to actually pass it

    through -- otherwise the scanner-only fix has no live caller and the

    measured defect (25/28 import sites unrepointed) is not actually closed.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_refactor_corpus.py
  reason: 'Coordinator directive: extend the existing corpus regression guard

    (T-3110/T-3119) with a multi-symbol-same-line usage shape and prove it

    catches the also-moving-sibling-import defect before the fix.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: docs/commands/refactor.md
  reason: 'Closing SCOPE001/SCOPE002 findings from the real fix: the changed public

    functions'' own frob:doc anchors live in docs/commands/refactor.md

    (already edited), and the repro/regression tests live in

    tests/test_refactor.py (already edited) alongside the pre-existing

    scan_references/build_plan test coverage that doc anchor''s own

    scope-closure pulls in.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_refactor.py
  reason: 'Closing SCOPE001/SCOPE002 findings from the real fix: the changed public

    functions'' own frob:doc anchors live in docs/commands/refactor.md

    (already edited), and the repro/regression tests live in

    tests/test_refactor.py (already edited) alongside the pre-existing

    scan_references/build_plan test coverage that doc anchor''s own

    scope-closure pulls in.

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_refactor.py::TestScanReferences::test_also_moving_sibling_on_same_line_is_folded_into_rewrite
- tests/test_refactor.py::TestScanReferences::test_also_moving_sibling_plus_genuinely_untouched_name_still_blocks
- tests/test_refactor.py::TestScanReferences::test_mixed_moved_and_untouched_names_leaves_import_alone
- tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim
designated_repro_test: tests/test_refactor.py::TestScanReferences::test_also_moving_sibling_on_same_line_is_folded_into_rewrite
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED during T-3086 (frob refactor split frob.gates._models --symbols
Severity,WaiverRef,DebtEntry,Violation --into frob.findings): the split
applied cleanly, both modules import correctly, and all three verify
post-conditions passed. But of ~28 non-gates source files that import one
of the four moved value types from frob.gates._models, only 3
(src/frob/vet/_models.py, src/frob/app/vet_runner.py,
src/frob/tickets/_land.py) were repointed to `from frob.findings import
...` directly. The other ~25 (src/frob/dup/_rules.py, fuzz/_rules.py,
perf/_advisories.py and siblings, policy/__init__.py, vet/_ecosystem.py,
vet/_scan.py, etc.) still read `from frob.gates._models import Severity,
Violation` (or similar) unchanged.

This is NOT a correctness bug -- gates/_models.py re-exports the moved
names (the same T-1201 backward-compat pattern already used elsewhere in
that file), so every one of those imports still resolves and every test
still passes. It IS an incompleteness relative to what a full "these
importers now import the leaf" migration would look like.

SUSPECTED ROOT CAUSE (not confirmed -- worth verifying first): the files
that DID get repointed have a `from frob.gates._models import Violation`
line whose ONLY name is a moved symbol used in a real expression context
(a function call or attribute access). The files that did NOT get
repointed appear to use the moved names only as TYPE ANNOTATIONS (e.g.
`def f(v: Violation) -> str:`), which src/frob/refactor/_scan.py's
reference-collection pass may not be counting as call sites at all.

Verify this hypothesis against src/frob/refactor/_scan.py's reference
collection, then widen it to catch type-annotation-only usages of a moved
symbol so a future split's reference-rewrite actually reaches every real
consumer, not just the ones using the symbol in an expression position.
