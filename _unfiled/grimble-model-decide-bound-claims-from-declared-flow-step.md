+++
id = "01M7EXV13KRR0GC1AX0XRZXC2Z"
title = "grimble-model: decide bound claims from declared flow/step quantities; fix CLAIM003 message"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:44Z"
updated = "2026-11-15T06:20:44Z"
labels = ["no-story"]

[[acceptance]]
text = "The example yields REFUTED"
bound = false

[[acceptance]]
text = "A passing bound yields PROVED"
bound = false

[[acceptance]]
text = "A claim with no quantity gives a correct Unresolved message"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md M6. Evidence: flow f { age 2 s; } claim c { bound age f <= 1 s; } gives CLAIM003 Unresolved with the wrong text 'declares no measured age'. Files: crates/grimble-model/src/claim.rs, SPEC 4.4 line 579. Remedy: compare against the declared quantity (REFUTED or PROVED at L1) and fix the message.
