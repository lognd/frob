---
id: T-2337
title: 'DRIFT002: repoint run_drain_async''s frob:tests edge after T-2324''s watermark
  fix lands'
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
blocked_by:
- T-2324
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_drain.py
evidence_scope:
- tests/unit/verify/test_drain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_green_round_advances_watermark_a_subsequent_round_sees
designated_repro_test: null
acceptance:
- text: given T-2324 has landed, when run_drain_async's frob:tests directive is re-read
    against the current test_drain.py, then it points at a real, resolving test that
    accurately covers the described behavior
  evidence:
  - tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd::test_green_round_advances_watermark_a_subsequent_round_sees
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Residue of T-2330 (deliberately not addressed there): DRIFT002
src/frob/verify/_drain.py::run_drain_async -> tests/unit/verify/
test_drain.py::TestRunDrainAsync.test_runs_one_bounded_round_and_
advances_the_watermark no longer resolves.

T-2330 investigated and found this is a REAL rename/removal, not a false
positive: T-2324 ("the wired drain runs to completion and never advances
the watermark") is live work on this exact function and the exact
watermark-advance behavior this stale test name concerns.
tests/unit/verify/test_drain.py::TestRunDrainAsync no longer has a
method by the old name; the current candidates that look like its
replacement are test_green_round_advances_watermark_a_subsequent_
round_sees and test_unmeasurable_round_leaves_watermark_untouched_not_
corrupt.

Blocked by T-2324 deliberately: src/frob/verify/_drain.py is under
T-2324's live lease, and repointing this frob:tests directive before
T-2324's fix lands risks either colliding with its edits or pointing at
a test whose assertions T-2324's own fix will change again.

REQUIRED once T-2324 lands: read run_drain_async's post-fix body, read
the current TestRunDrainAsync test methods, and either repoint the
frob:tests directive at the real covering test (if the old assertion's
intent survives under a new name) or write a fresh one if none covers
it, then ack.