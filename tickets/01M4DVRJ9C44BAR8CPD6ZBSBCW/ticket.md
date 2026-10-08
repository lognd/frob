+++
id = "01M4DVRJ9C44BAR8CPD6ZBSBCW"
title = "Backlog sweep: re-scope or drop native rule tickets that reimplement a rule a bound tool ships (D122)"
type = "chore"
category = "todo"
priority = "medium"
points = 2
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T13:38:06Z"
updated = "2026-10-08T13:38:06Z"
scope = ["changelog.d/**", "tickets/**"]

[[acceptance]]
text = "Given the sweep, when done, then each touched ticket has a comment naming the bound tool rule or the reason it stays native"
bound = false
+++

docs/design/tool-binding.md section 5. Check the WEBSEC, A11Y, SEO, UNITY, NEAT and SYSDESIGN rule tickets against the bind list in notes/research/lint-catalogue-2026-10-08.md and the per-tool rule lists in notes/research/lint-reuse-research-2026-10-08.md; re-scope to a binding plus id map, or drop with a reason naming the tool and rule.
