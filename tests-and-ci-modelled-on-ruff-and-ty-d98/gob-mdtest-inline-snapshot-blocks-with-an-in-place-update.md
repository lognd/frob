+++
id = "01M48PC0TZ7MHW4KA89V6ZFY72"
title = "gob-mdtest: inline snapshot blocks with an in-place update env"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T13:27:40Z"
updated = "2026-10-28T12:57:44Z"
labels = ["no-story"]
scope = ["crates/gob-mdtest/**", "crates/gob-dev/src/ci.rs"]

[[links]]
kind = "blocked-by"
target = "01M48PBYN43QPHGAF7Y14C4ZGJ"

[[acceptance]]
text = "self-tests cover insert, rewrite, remove and the three failures"
bound = false

[[acceptance]]
text = "FORMAT.md documents it"
bound = false

[[acceptance]]
text = "cargo dev ci fails if the update env is set"
bound = false

[[acceptance]]
text = "the update mode never changes a case's outcome class without a second explicit switch"
bound = false

[[acceptance]]
text = "an Unresolved snapshot shows the reason in words and its remedy"
bound = false
+++

Add a `snapshot` fence after a case (and a section directive) holding the rendered diagnostics; FROB_MDTEST_UPDATE=1 inserts, rewrites or removes the block in the markdown, with three failures otherwise (missing, stale, orphan), like ty's inline snapshots. External insta stays only for snapshot-diagnostics. cargo dev ci proves update mode is off. Source: notes/research/rule-testing.md (D103).

no-story: internal engineering task in gob-mdtest; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
