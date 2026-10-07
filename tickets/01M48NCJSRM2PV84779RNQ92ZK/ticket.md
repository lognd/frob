+++
id = "01M48NCJSRM2PV84779RNQ92ZK"
title = "frob test: vitest and jest runner and evidence provider for TypeScript tests"
type = "story"
category = "in-progress"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T13:10:30Z"
updated = "2026-10-07T02:28:08Z"
scope = ["crates/frob-tests/**", "crates/frob-evidence/**", "crates/gob-symbols/src/typescript/mod.rs", "crates/gob-symbols/src/lib.rs", "crates/gob-testsupport/src/lib.rs", "docs/reference/config.md", "docs/schemas/config.json", "docs/design/code-model.md"]

[[acceptance]]
text = "frob test runs the vitest file of the web conformance fixture and records per-test evidence"
bound = false

[[acceptance]]
text = "a missing node or vitest install is refused with a named reason, not skipped"
bound = false

[[acceptance]]
text = "jest is detected and run in a jest fixture"
bound = false
+++

After ~97A7SXX, TS test calls are units that COV001 and frob test recognise, but frob-tests has no TypeScript runner, so a touched TS test is named and never run (select.rs yields no run target). Add a vitest and jest Framework (detected per workspace member through gob-frameworks / package.json), node ids that map back to the test units, junit or json result parsing into evidence, and a missing-node/missing-runner case that is refused with a named reason, never skipped (code-model.md 3 runner; tickets.md evidence).
