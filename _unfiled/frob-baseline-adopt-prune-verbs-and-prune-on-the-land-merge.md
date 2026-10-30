+++
id = "01M66G70CZQMQ6Y55Y5QJPFKV3"
title = "frob baseline adopt/prune verbs and prune on the land merge tree"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-30T13:32:59Z"
updated = "2026-10-30T21:17:12Z"
scope = ["crates/frob/**", "crates/frob-land/**", "docs/reference/**", "docs/schemas/**"]

[[acceptance]]
text = "frob baseline adopt/prune exist and land prunes on the merge tree"
bound = true
+++

Follow-up of ~7FDF275. Quoted scope cut: the CLI verbs 'frob baseline adopt <RULE> --reason R --ticket T' and 'frob baseline prune', 'check --fix' prune, and 'frob land' pruning on the merge tree, built on gob_rules::Baseline (adopt, prune, intersect_base).
