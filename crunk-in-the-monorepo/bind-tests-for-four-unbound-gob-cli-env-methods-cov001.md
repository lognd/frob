+++
id = "01M7TJ8WDCE6AZPP9AGQRV4RWY"
title = "Bind tests for four unbound gob-cli Env methods (COV001)"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-11-19T18:49:28Z"
updated = "2026-11-20T07:05:48Z"
idempotency_key = "cov001-gob-cli-env"
labels = ["no-story", "good-first"]
scope = ["crates/gob-cli/tests/**"]

[[acceptance]]
text = "Given Env.with, Env.get, Env.is_set_nonempty and Env.path, when frob check runs, then each is reached by a test bound with frob:tests and no COV001 finding names any of them"
bound = true
+++

Four public methods on Env in crates/gob-cli/src/env.rs, namely with, get, is_set_nonempty and path, have no test bound to them, so frob check raises COV001 for each.

## Start here
Open crates/gob-cli/src/env.rs and read the four methods, then add one small test per method under crates/gob-cli/tests that calls it directly on an Env and asserts the value it returns. Put a frob:tests comment naming the method on the line above each test. Then run frob check --skip-tools and confirm none of the four is named in a COV001 finding.

no-story: internal engineering task in gob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
