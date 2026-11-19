+++
id = "01M7TCKMBT95HKXRACWVH5VVDY"
title = "Bind tests for the remaining unbound public methods (COV001)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-11-19T17:10:29Z"
updated = "2026-11-19T17:10:29Z"
idempotency_key = "cov001-remaining-eight"
labels = ["no-story", "good-first"]
scope = ["crates/gob-cli/tests/**,crates/crunk/tests/**,crates/crunk-rules/tests/**,crates/crunk-spec/tests/**"]

[[acceptance]]
text = "Given the eight listed public methods, when frob check runs, then each is reached by a test bound with frob:tests and no COV001 finding names any of them"
bound = false
+++

frob check lists public methods reached only through ambiguous calls: Reason.line in crates/crunk-rules/src/handoff.rs, load_comments in crates/crunk-spec/src/handoff.rs, StampData.lines in crates/crunk/src/stamp.rs, StatusError.code in crates/crunk/src/status.rs, and Env.with, Env.get, Env.is_set_nonempty and Env.path in crates/gob-cli/src/env.rs.

## Start here
Pick one of the listed items, add a test in that crate that calls it directly and asserts its real output, and put a frob:tests comment naming it on the line above the test. Follow the pattern of the existing tests in crates/crunk/tests/it/stamp.rs. Then run frob check --skip-tools and confirm the item is no longer named in a COV001 finding.

no-story: internal engineering task in the crunk and gob-cli crates; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.

## Start here

- Files to read first: <TODO: list the files>
- Test command: <TODO: the command that runs the tests>
- Who to ask: <TODO: a handle or channel>
