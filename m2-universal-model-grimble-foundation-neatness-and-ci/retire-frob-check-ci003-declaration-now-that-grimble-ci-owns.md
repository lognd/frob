+++
id = "01M5F0A96X8KCH10HNHTXCDEKR"
title = "Retire frob-check CI003 declaration now that grimble-ci owns CI003"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:32:37Z"
updated = "2026-10-23T03:45:18Z"
scope = ["crates/frob-check/**"]

[[acceptance]]
text = "Given the workspace, when CI003 is looked up, then exactly one declaration owns it and the other reference is removed or delegates"
bound = false

[[acceptance]]
text = "Given a workflow that trips CI003, when frob check and grimble check run, then the finding is reported once"
bound = false
+++

docs/reference/rules/CI003.md says the id is declared in frob-check until grimble-ci owns it; reconcile the two declarations (found while working ~8886VJ4).
