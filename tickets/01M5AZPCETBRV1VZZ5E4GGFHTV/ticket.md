+++
id = "01M5AZPCETBRV1VZZ5E4GGFHTV"
title = "Frob rule corpora: add the polarity-shaped unresolved case for 39 rules (see coverage-allowlist.toml kind=unresolved)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T21:04:48Z"
updated = "2026-10-20T02:08:01Z"
scope = ["crates/frob-check/tests/mdtest/**", "crates/*/tests/mdtest/**"]

[[acceptance]]
text = "TICK010 has a polarity-shaped unresolved corpus case and rule_coverage passes for it"
bound = true
+++

Burn down the [[gap]] kind=unresolved entries for product frob in crates/gob-mdtest/coverage-allowlist.toml; found while working ~WPZC326.
