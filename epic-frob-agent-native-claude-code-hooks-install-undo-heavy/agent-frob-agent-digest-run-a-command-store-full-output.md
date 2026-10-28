+++
id = "01M4P2N1Q1F8PKS9FY2MRH4QCR"
title = "agent: frob agent digest (run a command, store full output, print bounded summary)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:26Z"
updated = "2026-10-28T12:55:56Z"
labels = ["no-story"]
scope = ["crates/frob-cli/**"]

[[acceptance]]
text = "digest stores full output as a content-addressed artifact and prints head, tail, error lines and the artifact path"
bound = false

[[acceptance]]
text = "exit status of the wrapped command is preserved"
bound = false
+++

no-story: internal engineering task in frob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
