+++
id = "01M5MK67S8WWDN0CTHMP6P98AB"
title = "Regenerate stale docs/reference/rules/MDL008.md"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-23T14:38:40Z"
updated = "2026-10-23T22:20:39Z"
scope = ["docs/reference/rules/MDL008.md"]

[[acceptance]]
text = "Given the MDL008 rule source, when gob-dev gen all runs, then docs/reference/rules/MDL008.md is regenerated and gen --check is clean"
bound = false
+++

gen all --check reports GEN001 for MDL008.md; found while working 01M4GK56B7ADTTC87X31CR03NE
