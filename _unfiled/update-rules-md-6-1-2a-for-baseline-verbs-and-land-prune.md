+++
id = "01M66JP3NSX2P0M11ZC74NCWPQ"
title = "Update rules.md 6.1.2a for baseline verbs and land prune"
type = "docs"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-30T14:16:11Z"
updated = "2026-11-17T04:22:17Z"
labels = ["good-first"]
scope = ["docs/design/rules.md", "docs/design/shared/rules.md"]

[[acceptance]]
text = "Given docs/design/rules.md 6.1.2a, when a reader looks up baseline handling, then it names baseline adopt/prune, land prune, E-LAND-BASELINE and frob_land::baseline_prune"
bound = false
+++

found while working QJPFKV3: rules.md 6.1.2a still says the baseline verbs and land prune are separate tickets.

## Start here
Open docs/design/rules.md, find section 6.1.2a, and rewrite the paragraph to describe the shipped behavior. See crates/frob-land for baseline_prune.
