+++
id = "01M4FDQ3841JN891PHV248NC9A"
title = "check --ticket defaults its base to the commit where the ticket's work lease started (stacked branches)"
type = "story"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:11:07Z"
updated = "2026-10-09T04:11:07Z"
labels = ["adoption:hullbreach"]
scope = ["crates/frob-check/**", "crates/frob-lease/**", "changelog.d/**"]

[[acceptance]]
text = "Given two tickets worked in sequence on one branch based on a non-main branch, when frob check --ticket runs for the second, then the base is the lease-start commit recorded by work, so the first ticket's files raise no SCOPE001 or TICK002; --base still overrides"
bound = false
+++
