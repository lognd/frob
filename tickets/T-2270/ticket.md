---
id: T-2270
title: frob ticket evidence silently drops the Done report body when re-serializing
  ticket.md -- hit twice in one ticket, survived only because the agent noticed
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_store.py
evidence_scope:
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
- tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
designated_repro_test: tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
acceptance:
- text: Recording evidence on a ticket that HAS a Done report body preserves it byte-for-byte
    (fails today)
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- text: 'MUST-STILL-PASS: a ticket with no report body still records evidence cleanly;
    set_done_report still replaces the body as today'
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
  - tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
- text: Every ticket.md writer audited for the same round-trip loss; state which were
    checked and which were affected
  evidence:
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- text: Any writer that legitimately must drop the body says so loudly -- silence
    is the defect
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# `frob ticket evidence` silently drops the Done report body when it re-serializes `ticket.md`

## Measured evidence (2026-08-17)

Reported unprompted by the implementer that landed T-2256:

> the ticket-store's evidence-write path re-serializes `ticket.md` and silently
> dropped my Done report body **twice**; I re-added it each time before the
> final land committed.

Twice, in one ticket, in one session. The Done report survived on main (132
lines) ONLY because the agent noticed and manually restored it both times. An
agent that did not check its own file after recording evidence would have
landed with the body gone -- and the land would have succeeded, because a
missing report body is not something any gate refuses.

The write path is under `src/frob/tickets/_store.py`, which already knows about
this content explicitly (`_find_done_report_heading`,
`_done_report_section_end`, `replace_done_report_section`, all imported at
:45-47) and serializes under the lock described at :204 ("`add_evidence`,
`set_done_report`, ... acquires this BEFORE its own"). So the machinery to
preserve the section exists and the evidence path is not using it correctly.

## Why this is worse than it looks

- **It is silent.** No warning, no refusal, no diff the agent is prompted to
  review. The only signal is the body being gone if you happen to look.
- **It destroys the one artifact that explains the work.** A Done report is the
  reviewable record of what was changed and why; the ledger keeps the state
  transition either way, so the loss is invisible in every status view.
- **It lands.** Nothing gates on report-body presence, so a dropped body is
  published permanently.
- **The recovery is manual and undocumented.** This agent knew to re-add it.
  Nothing told it to.

## Do NOT fix it this way

- **Do NOT make it a land-time gate ("refuse a land whose report body is
  empty").** That catches the symptom one step too late, punishes tickets that
  legitimately have no report yet, and leaves the data loss intact for every
  non-landing path.
- **Do NOT have the caller re-write the body after every evidence call.** That
  is the manual workaround this agent had to invent; pushing it onto callers
  guarantees the next one forgets.
- **Do NOT reconstruct the body by re-reading and string-splicing the file.**
  `_store.py` already has `replace_done_report_section` /
  `_find_done_report_heading` for exactly this. Use the existing structured
  path -- do not add a second, text-based one. Standing user directive:
  token/grammar, never lexical.
- **Do NOT fix only `add_evidence`.** Identify every writer that
  re-serializes `ticket.md` and confirm which of them round-trip the body.
  State the full list; if only one is broken, say so and prove it.

## Acceptance criteria

1. (MUST FAIL FIRST) Recording evidence on a ticket that HAS a Done report body
   preserves that body byte-for-byte. Fails today -- reproduce with the real
   shape: a ticket with a committed report, then
   `frob ticket evidence <id> <node> --accepts N`.
2. MUST-STILL-PASS CONTROLS: a ticket with NO report body still records
   evidence cleanly (no fabricated empty section), and `set_done_report`
   continues to replace the body as it does today.
3. Every `ticket.md` writer is audited for the same round-trip loss; state
   which were checked and which were affected.
4. If any writer legitimately must drop the body, it says so loudly rather
   than silently -- silence is the defect, not the rewrite.

## Scope note

`src/frob/tickets/_store.py` owns the serializer and already imports the
done-report section helpers. The evidence entry point may live elsewhere in
`src/frob/tickets/`; trace it rather than guessing from module names, and widen
scope with a measured reason if the real writer is a sibling.