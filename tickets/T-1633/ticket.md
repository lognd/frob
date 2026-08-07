---
id: T-1633
title: live-tracker scan reads narrative prose as declarations (and its regex lacked
  a left boundary)
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_live_tracker.py
- tests/test_tickets_live_tracker.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: TICK009 pre-dispatch narrowing
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: docs/**
  reason: TICK009 pre-dispatch narrowing
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: TICK009 pre-dispatch narrowing
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: TICK009 pre-dispatch narrowing
  actor: logan
  at: '2026-08-07'
designated_repro_test: null
threat: null
component: null
---
`_WAIVER_TICKET_PATTERN` in src/frob/tickets/_live_tracker.py is:

    ticket=\"?{id}\"?\b|ticket\s+\"{id}\"|follow_up=\"?{id}\"?\b

The first and third alternatives have a right-hand word boundary but NO left-hand one, so `ticket=T-12NN` matches as a SUBSTRING of any longer identifier ending in `ticket=`. Real false positives this produces:

- `active_ticket=T-15NN`  -> matches `ticket=T-15NN`
- `landing_ticket=T-12NN`, `parent_ticket=T-12NN`, and anything else of that shape
- the same for `follow_up=` inside a longer attribute name

Observed 2026-08-06: landing T-15NN was refused with LiveTrackerCited, naming tickets.md:7462. The citing text was ordinary NARRATIVE PROSE in T-15NN's own Done report -- a sentence explaining that a scoped run "sets active_ticket=T-15NN". Nothing cited T-15NN as a live tracker; the ticket was simply unlandable until the prose was reworded.

Fix: anchor the left side of each attribute alternative, e.g. `(?<![\w.-])ticket=` and `(?<![\w.-])follow_up=`, so only a genuine standalone attribute matches.

Two further hardening points worth doing in the same pass:

1. The scan greps the LEDGER as well as source. A Done report is narrative, and narrative legitimately quotes commands and attributes -- `--ticket T-12NN`, `follow_up="T-12NN"` shown as an example, a pasted error message. Consider excluding Done-report prose from the waiver-citation grep entirely, or restricting the ledger scan to structured frontmatter. A detector that reads prose as declarations will keep producing this class of refusal no matter how good the regex is. (Precedent in this repo: TICK006 already had to learn that a marker-lookalike inside quoted prose is not a marker, T-1541.)

2. Add the boundary cases to the test suite directly: `active_ticket=T-XXXX` must NOT be a citation, `ticket="T-XXXX"` must be, and the same pair for `follow_up=`.

Note this guard is doing exactly what it should in the general case -- T-1559 added it to stop a closing ticket orphaning waivers that name it, and that is valuable. This is a precision bug in an otherwise correct check, not an argument against the check.

NOTE ON THIS TICKET'S OWN TEXT: the examples above deliberately use non-existent placeholder ids (T-15NN, T-12NN). The first revision of this ticket quoted the real id, and the body itself was then flagged as a live-tracker citation, blocking the very land it describes -- a self-demonstrating instance of the prose-read-as-declaration problem this ticket exists to fix.