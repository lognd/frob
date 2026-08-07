---
id: T-0812
title: 'land: extend draft-id renumber substitution to .strata waive clauses and frob:waive
  comments + unrelated-draft survival test'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched
designated_repro_test: null
acceptance:
- text: GIVEN a worktree whose design/frob.strata or source frob:waive comments cite
    a draft id that land renumbers WHEN the land completes THEN those refs are rewritten
    to the final id (no permanently-invisible dangling draft ref under WAIVE007's
    exemption); GIVEN an UNRELATED draft id in ledger prose THEN it survives the rewrite
    untouched (negative test)
  evidence:
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_strata_waive_clause_draft_id_reference
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_frob_waive_comment_draft_id_reference
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_leaves_unrelated_draft_id_reference_untouched
threat: null
component: null
---
Combined follow-up from the T-0808 and T-0811 reviews: T-0811's rewrite covers ledger+archive prose only, so a .strata waiver or frob:waive comment citing a renumbered draft (the ORIGINAL T-draft-8cd37914 incident class) stays dangling forever and is unconditionally exempt from WAIVE007 -- the exemption becomes load-bearing instead of safe. Extend the land's old->new mapping substitution to tracked files containing waive sites (grep-scoped, per-id-keyed regex like the T-0811 mechanism). Also add the T-0811 reviewer's missing negative test: an unrelated draft id in prose survives the ledger rewrite untouched (separate test; the existing blanket zero-T-draft assertion conflicts with planting one).