+++
id = "01M4069WHH6KXYWDAJD3TXB8SR"
title = "land writes the changelog fragment skeleton from the ticket title"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T13:34:27Z"
idempotency_key = "m2-rel-land-fragment"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-land/src/**", "crates/frob-release/src/skeleton.rs", "crates/frob-release/src/fragment.rs", "crates/frob-release/src/lib.rs", "crates/frob-release/tests/skeleton.rs", "crates/frob-evidence/src/done.rs", "crates/frob/src/ticket/fragment_cmd.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/tests/fragment.rs", "docs/design/documentation.md", "docs/reference/cli/frob.md"]

[[links]]
kind = "blocked-by"
target = "01M4069WD4P8ZZ5HGQ5HE2EX99"

[[acceptance]]
text = "Given a feature ticket with no fragment, when land runs, then the land commit includes a skeleton fragment titled from the ticket"
bound = false

[[acceptance]]
text = "Given an existing fragment, when land runs, then it is not overwritten"
bound = false
+++

When REL003 would refuse for lack of a fragment, land writes changelog.d/<ulid>.<type>.md with the product prefix and the ticket title (type from the ticket type), stages it into the land commit and prints it, so the agent edits a sentence instead of inventing a file.
