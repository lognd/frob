+++
id = "01M7TBK44G9J6HCMEXFWA6AW81"
title = "Bind tests for crunk Standing.word and StampError.code (COV001)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-11-19T16:52:44Z"
updated = "2026-11-19T17:10:14Z"
idempotency_key = "cov001-crunk-standing-stamp"
labels = ["no-story", "good-first"]
scope = ["crates/crunk-rules/tests/**,crates/crunk/tests/**"]

[[acceptance]]
text = "Given the public methods Standing.word and StampError.code, when frob check runs, then each is reached by a test bound with frob:tests and no COV001 finding names either method"
bound = false
+++

Two public methods, Standing.word in crates/crunk-rules/src/handoff.rs and StampError.code in crates/crunk/src/stamp.rs, had no test bound to them, so frob check raised COV001 for each.

## Start here
Open crates/crunk-rules/tests/it/handoff.rs and crates/crunk/tests/it/stamp.rs, add one small test per method that calls it directly, and put a frob:tests comment naming the method on the line above each test. Then run frob check --skip-tools and confirm neither method is named in a COV001 finding.

no-story: internal engineering task in crunk; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
