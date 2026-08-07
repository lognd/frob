---
id: T-0819
title: gate:WAIVE006 design/frob.strata waivers reference closed ticket T-0803
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
found while working T-0816: frob check gate:WAIVE fires 4x WAIVE006 errors at design/frob.strata:307,370,418,469 -- each waive() references ticket T-0803 which is now closed, but WAIVE006 treats a closed-ticket binding as stale. Re-review whether the underlying gaps these waivers cover are actually resolved by T-0803's landing (in which case remove the waivers) or still open (in which case re-point them at a still-open follow-on ticket, per the T-0803 waiver text's own note 'tracked in T-0803').

## Drop reason
- 2026-07-23: already fixed directly on main (commit re-litigating the LINT004 waivers: kill-switch flags declared on core/fleet/tickets_ledger, vet waiver rewritten to open T-0817); WAIVE006 count is zero on main