+++
id = "01M50DHQWG0D8CJM84YP4D7209"
title = "docs: regenerate drifted docs/reference/rules (gob-dev gen all)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-15T18:35:17Z"
updated = "2026-10-15T18:45:07Z"
scope = ["docs/reference/rules/**", "docs/schemas/**"]

[[acceptance]]
text = "gob-dev gen --check is clean"
bound = true
+++

gob-dev gen --check reports drift (TOOL001) in docs/reference/rules (MDL019-021, SYS010/011/013 and ~20 others). Run gob-dev gen all, commit, and find why check and committed docs disagree.
