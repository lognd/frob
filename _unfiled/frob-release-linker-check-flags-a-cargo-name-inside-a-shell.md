+++
id = "01M5GVVC0TQ7P19386NP6ZWMEM"
title = "frob-release linker check flags a cargo name inside a shell comment"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T03:53:03Z"
updated = "2026-10-22T04:34:55Z"
scope = ["crates/frob-release/tests/it/release_workflow.rs"]

[[acceptance]]
text = "frob-release linker workflow test passes against the current ci.yml"
bound = true
+++

every_job_that_compiles_rust_on_linux_installs_the_linker_first matches LINKING_CARGO by substring over the whole run script, so the comment mentioning cargo dev changes in the changes job of ci.yml counts as compiling Rust before the linker setup; ignore full-line shell comments
