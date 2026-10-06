+++
id = "01M40F7C08S5XXF2AKBHDFYHNJ"
title = "frob-release tests: one dispatching mdtest corpus binary for REL001 and REL002"
type = "chore"
category = "done"
outcome = "wont-fix"
priority = "low"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T08:48:52Z"
updated = "2026-10-06T13:56:17Z"
idempotency_key = "m2-release-corpus-dispatch"
labels = ["milestone:2", "good-first"]
scope = ["crates/frob-release/tests/**"]

[[links]]
kind = "superseded-by"
target = "01M48R05NH09VNCDWSPJHD5710"

[[acceptance]]
text = "Given frob-release, when its tests run, then one corpus binary runs the REL001 and REL002 examples and rel002.rs has no REL001 dispatch"
bound = false
+++

Follow-up of ~PKJ5AVG. ## Start here
The mdtest! macro runs every .md under crates/frob-release/tests/mdtest, so REL001's corpus currently runs inside the rel002 test binary through a dispatch added to rel002.rs. Read crates/frob-obligations/tests (one dispatching corpus binary for several rules) and move frob-release to the same shape: tests/corpus.rs dispatching by rule id to rel001_corpus and rel002 helpers; rel001.rs and rel002.rs keep their Rust tests only. Test: cargo nextest run -p frob-release passes with the same number of corpus cases, and cargo dev gen all --check is clean. Ask the coordinator if unsure.
