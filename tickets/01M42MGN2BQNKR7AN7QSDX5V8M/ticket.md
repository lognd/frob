+++
id = "01M42MGN2BQNKR7AN7QSDX5V8M"
title = "A field line equal to the frontmatter fence (+++) makes a ticket unreadable; it vanishes on index rebuild and doctor --fix cannot repair it"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
reporter = "lognd"
created = "2026-10-04T04:59:48Z"
updated = "2026-10-04T05:45:28Z"
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "Given any field text containing a line +++, when the ticket is written, rebuilt and read, then it round-trips and doctor reports nothing"
bound = false
+++

Reproduced against the v2 binary: a title, persona or acceptance line '+++' corrupts ticket.md (v1 T-1536 class). Render so no field line can equal the fence (escape or quote multi-line fields) and make doctor --fix re-render ticket.md from the events. Evidence and repro: notes/review/v1-gap/D-incidents.md (P-01).
