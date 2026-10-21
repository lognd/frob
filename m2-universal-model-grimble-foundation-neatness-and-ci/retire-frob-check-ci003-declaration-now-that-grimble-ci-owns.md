+++
id = "01M5F0A96X8KCH10HNHTXCDEKR"
title = "Retire frob-check CI003 declaration now that grimble-ci owns CI003"
type = "task"
category = "todo"
priority = "medium"
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:32:37Z"
updated = "2026-10-21T10:32:37Z"
scope = ["crates/frob-check/**"]
+++

docs/reference/rules/CI003.md says the id is declared in frob-check until grimble-ci owns it; reconcile the two declarations (found while working ~8886VJ4).
