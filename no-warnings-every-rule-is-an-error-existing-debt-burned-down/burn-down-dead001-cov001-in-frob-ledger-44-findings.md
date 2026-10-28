+++
id = "01M61CD75V1DGJD15DNRFX8QWR"
title = "Burn down DEAD001/COV001 in frob-ledger (~44 findings)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M5XMF3XC9ZD6FPZ59ECWJCJ4"
reporter = "lognd"
created = "2026-10-28T13:50:16Z"
updated = "2026-10-28T15:06:24Z"
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "frob check --only DEAD001,COV001 reports zero findings under crates/frob-ledger; each is deleted, tested, bound or waived with a reason"
bound = true
+++

Split from ECWJCJ4. Per-crate burn-down; prefer deleting dead code and binding tests over waivers.
