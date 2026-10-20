+++
id = "01M59K3M7RWJWG4CRXTTDSNXR1"
title = "trust: discover packs awaiting review from the lock for the trust verb"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-19T08:05:36Z"
updated = "2026-10-19T08:05:36Z"
scope = ["crates/frob/src/trust_cmd.rs"]
+++

found while working ~28YRZ8Z: trust_cmd::pending() returns an empty list because no pack source exists; derive ReviewFacts from lock/store state.
