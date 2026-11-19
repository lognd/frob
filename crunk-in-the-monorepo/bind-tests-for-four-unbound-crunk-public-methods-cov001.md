+++
id = "01M7TCKMBT95HKXRACWVH5VVDY"
title = "Bind tests for four unbound crunk public methods (COV001)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-11-19T17:10:29Z"
updated = "2026-11-19T18:49:28Z"
idempotency_key = "cov001-remaining-eight"
labels = ["no-story", "good-first"]
scope = ["crates/crunk-rules/tests/**", "crates/crunk-spec/tests/**", "crates/crunk/tests/**"]

[[acceptance]]
text = "Given Reason.line, load_comments, StampData.lines and StatusError.code, when frob check runs, then each is reached by a test bound with frob:tests and no COV001 finding names any of them"
bound = false
+++

Four public methods, Reason.line in crates/crunk-rules/src/handoff.rs, load_comments in crates/crunk-spec/src/handoff.rs, StampData.lines in crates/crunk/src/stamp.rs and StatusError.code in crates/crunk/src/status.rs, have no test bound to them, so frob check raises COV001 for each.

## Start here
Open crates/crunk/tests/it/stamp.rs, which already holds a test for StampError.code, and copy its shape. Add one small test per method in the matching crate tests directory that calls the method directly, and put a frob:tests comment naming the method on the line above each test. Then run frob check --skip-tools and confirm none of the four is named in a COV001 finding.

no-story: internal engineering task in crunk; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
