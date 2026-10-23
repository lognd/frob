+++
id = "01M5F0A96X8KCH10HNHTXCDEKR"
title = "Retire frob-check CI003 declaration now that grimble-ci owns CI003"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:32:37Z"
updated = "2026-10-23T06:34:11Z"
scope = ["crates/frob-check/**", "docs/reference/rules/CI003.md", "crates/gob-check/**", "crates/frob/**", "docs/reference/**", "docs/schemas/config.json", "crates/grimble-check/**", "crates/gob-mdtest/coverage-allowlist.toml"]

[[links]]
kind = "blocked-by"
target = "01M5KDWHPF5YTVP64PYCXX0FRT"

[[acceptance]]
text = "Given the workspace, when CI003 is looked up, then exactly one declaration owns it and the other reference is removed or delegates"
bound = true

[[acceptance]]
text = "Given a workflow that trips CI003, when frob check and grimble check run, then the finding is reported once"
bound = true
+++

docs/reference/rules/CI003.md says the id is declared in frob-check until grimble-ci owns it; reconcile the two declarations (found while working ~8886VJ4).
