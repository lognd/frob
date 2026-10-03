+++
id = "01M4069XB9N36CQGEBNPKJ5AVG"
title = "REL001 release-without-cut: tag not created by release cut (Error)"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:58Z"
updated = "2026-10-03T06:12:58Z"
idempotency_key = "m2-rel-rel001"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-release/src/rel001.rs", "docs/reference/rules/rel/**"]

[[links]]
kind = "blocked-by"
target = "01M4069X6S9RJWRXX3YBZ9EG10"

[[acceptance]]
text = "Given a frob-v0.0.1 tag made by git tag, when frob check runs, then REL001 fires"
bound = false

[[acceptance]]
text = "Given a tag made by release cut, when frob check runs, then REL001 is silent"
bound = false
+++

Fires for a frob-v* tag with no recorded cut event for the same commit and version (or whose commit has versions or changelog disagreeing). The rule page states that the v1 meaning was retired (exceptions.md 6). Tags before the first cut (none) are not special-cased.
