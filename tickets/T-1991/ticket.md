---
id: T-1991
title: DSL001 fires 105 unscoped errors repo-wide on main -- floor is not zero
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured 2026-08-10 while landing T-1982: 'frob check --only gates' on main HEAD (6f14eae64) reports gate:DSL 105 errors, 0 warnings -- e.g. CHANGELOG.md:1853 (verb=waive malformed), docs/commands/sys.md:139 (verb=claims), many docs/design/*.md (verb=doc/ticket/used-by 'nothing reads it'). This makes gate-summary FAIL with 105 errors on main HEAD, contradicting the standing ZERO floor. Not caused by T-1982/T-1983/T-1986 (confirmed: none of those tickets touch any of the flagged files). Likely fallout from a recently-landed directive-parsing change (T-1970 landed frob:quote(...) parsing around this same window) that now flags markdown directive forms across docs/ that previously parsed silently. Needs investigation: either these docs directives are genuinely malformed and need fixing, or the DSL001 detector regressed and is over-firing on previously-valid forms.