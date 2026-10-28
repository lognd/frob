+++
id = "01M48R06SBXJZJ79GB8R20ASKS"
title = "cargo dev new-rule --universal|--lang: two files, no registration step, compiled in CI"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:10Z"
updated = "2026-10-28T12:57:42Z"
labels = ["no-story"]
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml"]

[[links]]
kind = "blocked-by"
target = "01M48R01QSDTBKNPREQPBJ6GPZ"

[[links]]
kind = "blocked-by"
target = "01M48R05NH09VNCDWSPJHD5710"

[[acceptance]]
text = "the scaffold builds and passes unedited for --universal and --lang"
bound = false

[[acceptance]]
text = "a cargo dev ci step proves it in a temporary copy"
bound = false
+++

M11: writes src/rules/<id>.rs and .md in the owning crate, regenerates the index, runs the rule's test; CI scaffolds into a temporary copy. Supersedes ~0H3WYTR. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.

no-story: internal engineering task in gob-dev; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
