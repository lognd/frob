+++
id = "01M3ZX7X7WYFHA4QXZ2YMHHCQZ"
title = "check --base: fail on new Unresolved for P+ rules in changed files"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX76WPYZQ4Q5WDQ72AWMZQ"
reporter = "lognd"
created = "2026-10-03T03:34:36Z"
updated = "2026-10-03T03:34:36Z"
idempotency_key = "m2-sec-no-new-unknowns"
labels = ["milestone:2", "area:security"]
scope = ["crates/gob-check/src/base_unknowns.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7X3RQTTR7V8JFRN8TQEK"

[[acceptance]]
text = "Given a changed file whose edit makes a P+ rule Unresolved where base was decided, when check --base runs, then it fails and names the file and rule"
bound = false

[[acceptance]]
text = "Given an Unresolved that existed at base, when check --base runs, then it does not fail"
bound = false
+++

Implements security.md section 2.7 (no new unknowns).

Existing Unresolved stay non-failing so adoption is never blocked; only a change that adds one on a P+ rule in a file it touches fails.
