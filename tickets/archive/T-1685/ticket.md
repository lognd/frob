---
id: T-1685
title: 'Clear main''s 3-error floor: ty untyped land-report helper, ARCH001 in _evidence.py,
  DOC009 status header'
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_work_and_land_finish.py
- src/frob/tickets/_evidence.py
- docs/audits/docs-completeness-2026-08-06.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_rejects_when_covers_scope_false
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_transition_refuses_close_when_kind_flipped_after_recording
designated_repro_test: null
threat: null
component: null
---
Three errors have been standing on main and are not attributable to any
open ticket. They are the whole of main's error floor as of 0.356.0
(commit 12b45fd4), so clearing them takes the repo to zero and makes any
future non-zero reading meaningful on sight:

1. `ty` unresolved-attribute at tests/test_ticket_work_and_land_finish.py
   :794:22 -- `Object of type object has no attribute final_id`. The
   helper `_land_a_real_ticket` returns an untyped tuple, so
   `real_report` narrows to `object`. Annotate the helper's return type
   rather than casting at the use site.
2. ARCH001: `src/frob/tickets/_evidence.py::_done_transition_structural_
   guard` is 62 lines against a 60-line threshold. Split along an
   existing guard boundary, the same way its siblings in this module
   already are.
3. DOC009: docs/audits/docs-completeness-2026-08-06.md has no dated
   status header in its first 15 lines. Add `Status: 2026-08-06`, or
   `Status: SUPERSEDED (see <path>)` if T-1610's sweep has been
   superseded.

Do all three in one pass; they share no code and none needs design work.