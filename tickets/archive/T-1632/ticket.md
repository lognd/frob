---
id: T-1632
title: 'live-tracker citation regex lacks a left boundary: active_ticket=T-#### reads
  as a citation'
state: dropped
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_live_tracker.py
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`_WAIVER_TICKET_PATTERN` in src/frob/tickets/_live_tracker.py is:

    ticket=\"?{id}\"?\b|ticket\s+\"{id}\"|follow_up=\"?{id}\"?\b

The first and third alternatives have a right-hand word boundary but NO left-hand one, so `ticket=T-1234` matches as a SUBSTRING of any longer identifier ending in `ticket=`. Real false positives this produces:

- `active_ticket=T-1582`  -> matches `ticket=T-1582`
- `landing_ticket=T-1234`, `parent_ticket=T-1234`, and anything else of that shape
- the same for `follow_up=` inside a longer attribute name

Observed 2026-08-06: landing T-1582 was refused with LiveTrackerCited, naming tickets.md:7462. The citing text was ordinary NARRATIVE PROSE in T-1582's own Done report -- a sentence explaining that a scoped run "sets active_ticket=T-1582". Nothing cited T-1582 as a live tracker; the ticket was simply unlandable until the prose was reworded.

Fix: anchor the left side of each attribute alternative, e.g. `(?<![\w.-])ticket=` and `(?<![\w.-])follow_up=`, so only a genuine standalone attribute matches.

Two further hardening points worth doing in the same pass:

1. The scan greps the LEDGER as well as source. A Done report is narrative, and narrative legitimately quotes commands and attributes -- `--ticket T-1234`, `follow_up="T-1234"` shown as an example, a pasted error message. Consider excluding Done-report prose from the waiver-citation grep entirely, or restricting the ledger scan to structured frontmatter. A detector that reads prose as declarations will keep producing this class of refusal no matter how good the regex is. (Precedent in this repo: TICK006 already had to learn that a marker-lookalike inside quoted prose is not a marker, T-1541.)

2. Add the boundary cases to the test suite directly: `active_ticket=T-XXXX` must NOT be a citation, `ticket="T-XXXX"` must be, and the same pair for `follow_up=`.

Note this guard is doing exactly what it should in the general case -- T-1559 added it to stop a closing ticket orphaning waivers that name it, and that is valuable. This is a precision bug in an otherwise correct check, not an argument against the check.

## Drop reason
- 2026-08-06: refiling with placeholder ids: the body quoted a real ticket id inside a pattern example and was itself flagged as a live-tracker citation