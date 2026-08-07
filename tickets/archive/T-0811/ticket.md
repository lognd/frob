---
id: T-0811
title: 'land: draft renumbering must rewrite draft-id references in Done-report prose
  (recurring TICK006 after every draft-filing land)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_own_draft_id_reference_in_done_report
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ledger whose Done reports reference T-draft ids WHEN land
    renumbers those drafts to real ids THEN every reference to the old draft id anywhere
    in the spliced ledger text is rewritten to the new id and no TICK006 fires post-land;
    a regression test lands a draft-referencing Done report and asserts zero stale
    draft ids
  evidence:
  - tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::test_land_rewrites_own_draft_id_reference_in_done_report
threat: null
component: null
---
Recurred 3x this drive (T-0778/T-0797, T-0745/T-0764 pairs): land renumbers T-draft blocks to real ids but leaves Done-report prose citing the old draft id, so TICK006 reds main after every draft-filing land until the coordinator hand-retargets. The renumber step already knows the old->new id mapping; apply it as a text substitution across the spliced ledger (and archive) before the integrity check.