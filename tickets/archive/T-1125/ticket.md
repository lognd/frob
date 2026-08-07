---
id: T-1125
title: 'land/renumber: rewrite draft-id references in ledger prose during renumbering'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- tests/test_tickets.py
- docs/modules/tickets.md
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_tiers.py
  reason: T-1125 scope's src/frob/tickets/** glob pulls in __init__.py::transition,
    whose frob:tests target lives in test_tickets_tiers.py -- SCOPE002 flags it as
    outside declared scope
  actor: logan
  at: '2026-07-28'
- op: remove
  glob: tests/test_tickets_tiers.py
  reason: 'revert: scope closure debt across src/frob/tickets/** is pre-existing (548
    SCOPE002 warnings unrelated to T-1125''s diff), not something this ticket should
    chase; filed as follow-up instead'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: docs/modules/tickets.md carries the public-api doc anchor renumber/renumber_one
    affects() closes over (T-1125's fix must update it, per playbook section 6); tests/test_tickets_collision.py
    is where T-1125's own new coverage (TestRenumberRewritesLedgerProse) lives, alongside
    the pre-existing renumber_one incident-reproduction tests it belongs next to
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_collision.py
  reason: docs/modules/tickets.md carries the public-api doc anchor renumber/renumber_one
    affects() closes over (T-1125's fix must update it, per playbook section 6); tests/test_tickets_collision.py
    is where T-1125's own new coverage (TestRenumberRewritesLedgerProse) lives, alongside
    the pre-existing renumber_one incident-reproduction tests it belongs next to
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_renumber_one_rewrites_a_sibling_ticket_done_report_prose
- tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_finalize_draft_rewrites_a_sibling_ticket_done_report_prose
designated_repro_test: null
acceptance:
- text: GIVEN a worktree ledger whose done-report prose cites T-draft-X WHEN frob
    ticket land renumbers T-draft-X to T-#### THEN every prose reference to T-draft-X
    in tickets.md is rewritten to the final id in the same splice, and a post-land
    full check reports zero TICK006 for it
  evidence:
  - tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_finalize_draft_rewrites_a_sibling_ticket_done_report_prose
- text: GIVEN frob ticket renumber OLD NEW WHEN prose elsewhere in the ledger references
    OLD THEN those references are rewritten too (or the command errors listing them),
    never silently left stale
  evidence:
  - tests/test_tickets_collision.py::TestRenumberRewritesLedgerProse::test_renumber_one_rewrites_a_sibling_ticket_done_report_prose
threat: null
component: null
---
The dominant wave-17 fallout class (4 incidents in one wave): land renumbers draft BLOCKS but never rewrites prose citing them, so done reports either go TICK006-phantom (T-1077/T-1084/T-1095 reports citing drafts that died) or -- worse and invisible to TICK006 -- cite a WRONG real id (T-0668's agent wrote T-1109 guessing its draft's final id; real id was T-1113; 8 prose sites hand-repaired by the coordinator). renumber already computes the old->new mapping; apply it to prose occurrences of the draft id across tickets.md/tickets-archive.md in the same transaction. Coordinators should never hand-grep real ids again; agents should be free to cite draft ids in prose and have land fix them.