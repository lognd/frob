+++
id = "01M48R06SBXJZJ79GB8R20ASKS"
title = "cargo dev new-rule --universal|--lang: two files, no registration step, compiled in CI"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:10Z"
updated = "2026-11-06T09:48:15Z"
labels = ["no-story"]
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml", "docs/design/shared/rules.md", "changelog.d/01M48R06SBXJZJ79GB8R20ASKS.added.md"]

[[links]]
kind = "blocked-by"
target = "01M48R01QSDTBKNPREQPBJ6GPZ"

[[links]]
kind = "blocked-by"
target = "01M48R05NH09VNCDWSPJHD5710"

[[acceptance]]
text = "the scaffold builds and passes unedited for --universal and --lang"
bound = true

[[acceptance]]
text = "a cargo dev ci step proves it in a temporary copy"
bound = true
+++

M11: writes src/rules/<id>.rs and .md in the owning crate, regenerates the index, runs the rule's test; CI scaffolds into a temporary copy. Supersedes ~0H3WYTR. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.

no-story: internal engineering task in gob-dev; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
