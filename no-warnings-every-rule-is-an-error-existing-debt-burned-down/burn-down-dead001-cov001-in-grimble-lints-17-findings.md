+++
id = "01M61CD7F8DW1JVZ73RXVC7KX6"
title = "Burn down DEAD001/COV001 in grimble-lints (~17 findings)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XMF3XC9ZD6FPZ59ECWJCJ4"
reporter = "lognd"
created = "2026-10-28T13:50:17Z"
updated = "2026-10-28T13:50:17Z"
scope = ["crates/grimble-lints/**"]

[[acceptance]]
text = "frob check --only DEAD001,COV001 reports zero findings under crates/grimble-lints; each is deleted, tested, bound or waived with a reason"
bound = false
+++

Split from ECWJCJ4. Per-crate burn-down; prefer deleting dead code and binding tests over waivers.
