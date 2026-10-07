+++
id = "01M4A12XB7EDWJ1FX8BN9XHZS1"
title = "ticket doable (and board NEXT) order ignores priority: low-priority August imports lead today's high-priority work"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-07T01:54:10Z"
updated = "2026-10-07T02:25:26Z"
scope = ["crates/frob-lease/**", "crates/frob-pm/**", "crates/frob-ledger/**", "docs/design/tickets.md", "changelog.d/01M4A12XB7EDWJ1FX8BN9XHZS1.*"]

[[acceptance]]
text = "a fixture with low-priority old and high-priority new todo tickets lists the high-priority ones first in ticket doable and board NEXT"
bound = false

[[acceptance]]
text = "expedite and fixed-date tickets lead regardless of priority, fixed-date ordered by due"
bound = false

[[acceptance]]
text = "doable and board NEXT share one ordering function (test)"
bound = false
+++

Seen 2026-10-06 in the first real frob board --brief: NEXT starts with ~49P22KK, ~Y18T290, ~GVGDB1W (low priority, created 2026-08) ahead of open high-priority tickets, so the dispatch queue agents read is effectively creation order. pm-enforcement.md 4 (cycle plan) and releases.md define the order: expedite lane, fixed-date by due, then rank; tickets here carry priority but no rank. Order doable and NEXT by class (expedite, fixed-date by due), then priority (critical, high, medium, low), then rank when set, then age; document the order where doable is defined and make board NEXT use the same function so they cannot diverge.
