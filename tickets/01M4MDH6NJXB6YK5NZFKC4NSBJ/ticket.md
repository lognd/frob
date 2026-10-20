+++
id = "01M4MDH6NJXB6YK5NZFKC4NSBJ"
title = "gob-symbols: tree-sitter-yaml F2 adapter with anchors and aliases as references"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-11T02:44:06Z"
updated = "2026-10-20T14:26:44Z"
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/frob-check/tests/it/tool_bind.rs"]

[[acceptance]]
text = "Given a workflow with a frob:accept CI001 directive above one '- uses:' step, when frob check runs with the zizmor stage, then only that step's CI001 finding is suppressed and a sibling step's finding is not"
bound = true

[[acceptance]]
text = "Given a YAML file with an anchor and an alias, when gob-symbols folds it, then the alias is a reference edge to the anchored key unit"
bound = true
+++

Split from ~WHCDCMG. YAML directives and exceptions already work through the F1 line-based adapter (gob-symbols yaml.rs) and hash-comment scanning. Remaining: tree-sitter-yaml behind a gob-languages feature (crate must be vendored or fetched from crates.io; not in the offline registry cache), an F2 adapter with sequence-item keys (for example '- uses:' step lines) as units, and anchors and aliases as references.
