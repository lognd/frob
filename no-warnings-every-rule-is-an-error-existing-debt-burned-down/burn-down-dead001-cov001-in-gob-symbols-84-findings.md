+++
id = "01M61CD6Q7ZBB2B4YDXST6JQTK"
title = "Burn down DEAD001/COV001 in gob-symbols (~84 findings)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M5XMF3XC9ZD6FPZ59ECWJCJ4"
reporter = "lognd"
created = "2026-10-28T13:50:16Z"
updated = "2026-10-28T13:50:21Z"
scope = ["crates/gob-symbols/**"]

[[acceptance]]
text = "frob check --only DEAD001,COV001 reports zero findings under crates/gob-symbols; each is deleted, tested, bound or waived with a reason"
bound = false
+++

Split from ECWJCJ4. Per-crate burn-down; prefer deleting dead code and binding tests over waivers.
