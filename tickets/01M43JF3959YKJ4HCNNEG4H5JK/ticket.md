+++
id = "01M43JF3959YKJ4HCNNEG4H5JK"
title = "E-FIX-STALE is reported as an internal error instead of a guard refusal"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T13:43:14Z"
updated = "2026-10-04T23:14:48Z"
scope = ["crates/gob-check/src/error.rs", "crates/gob-check/src/fix.rs", "crates/gob-check/src/lib.rs", "crates/frob-check/src/verb.rs", "docs/design/cli.md"]

[[links]]
kind = "blocked-by"
target = "01M42MGNE7XHTT1MR5CA6C2R1C"

[[acceptance]]
text = "Given a file changed between check and --fix, when frob check --fix runs, then the envelope error code is E-FIX-STALE with the guard-refusal exit class and a remedy"
bound = true
+++

~WS4WZBD reports a file changed between check and --fix as CheckError::FixIo with a message prefixed E-FIX-STALE, because crates/frob-check/src/verb.rs was leased by ~A6C2R1C. So the CLI classes a guard refusal as an internal error. Add a dedicated FixStale variant with its own code in the error catalog, map it in verb.rs to the guard-refusal exit class with a remedy (re-run frob check, then --fix), and test the envelope.
