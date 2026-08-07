---
id: T-1637
title: Manual draft refile silently discards evidence and Done reports; renumber already
  exists and is undocumented
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
- docs/guides/agent-playbook.md
- docs/modules/tickets.md
- tests/**
- src/frob/_cli_parsers/_ticket/**
- docs/design/ledger-v2.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/**
  reason: frob ticket promote needs CLI parser wiring alongside the library-level
    renumber/finalize_draft it reuses
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/design/ledger-v2.md
  reason: 'AFFECT001: write_ticket''s affects()-closure doc includes this file (section
    3 lock model); the T-1637 content-loss guard needed a short note there too'
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default
- tests/unit/test_ticket_store.py::TestWriteTicketUnchecked::test_skips_the_content_loss_guard_entirely
- tests/unit/test_ticket_store.py::TestWriteTicket::test_keeping_evidence_or_done_report_is_never_refused
- tests/unit/test_ticket_store.py::TestWriteTicket::test_first_write_for_a_new_id_is_never_refused
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promoting_an_already_final_id_is_a_no_op
designated_repro_test: null
threat: null
component: null
---
`frob ticket renumber <old> <new>` already exists and "rewrites one ticket's id everywhere". It is the correct primitive for turning a worktree draft id into a real one. Nothing documents that, so the recipe actually used -- five times on 2026-08-05/06, by the coordinator -- was a hand-rolled sequence:

1. read the draft's body out of the worktree ledger
2. `frob ticket new` on main with that body, capturing the new real id
3. delete the draft's block from the worktree ledger
4. string-swap every citation of the draft id in the ledger and in source

That recipe is lossy and it lost data. Step 3 deletes the block that holds the ticket's EVIDENCE LIST and its DONE REPORT; step 2 creates a fresh ticket that has neither. The land then refuses with "missing evidence or a Done report", and the only way back is `git show <commit>~1:tickets.md` archaeology to recover 12 evidence ids and a 12KB Done report and re-record them by hand. That happened for T-1636. Earlier repeats of the same recipe were survivable only because those tickets' content had already reached main by other means.

The recipe also has a second failure mode already hit twice: a blanket string-swap of the draft id renames the draft's OWN block instead of removing it, producing a duplicate of the real ticket in the worktree ledger.

Deliverables:

1. A first-class promotion path -- `frob ticket promote <draft-id>` (name negotiable) that allocates the next real id and performs the renumber atomically, carrying frontmatter, evidence, Done report, scope, and every citation across in one operation. This is the missing half of T-1622: that ticket asks worktree ids to be real from the start, this one makes existing drafts recoverable either way.

2. Failing that, document `frob ticket renumber` as THE way to refile a draft, in docs/guides/agent-playbook.md next to the existing draft-loss guidance, so the manual recipe stops being reinvented.

3. Make the lossy step impossible to take by accident: removing or overwriting a ledger block that carries a Done report or a non-empty evidence list should refuse, or at minimum warn loudly naming what is about to be discarded. The ledger already has post-splice integrity checks (`_post_splice_integrity_check`, T-1536) that refuse when an id would be LOST -- this is the same class of protection one level down, for a block's contents rather than its existence.

Point 3 is the one that generalises. The ledger is the system of record for work that has already been done; discarding a Done report should be as hard as discarding a ticket.