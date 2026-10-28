+++
id = "01M627BCQ5MSJF9KC2MCYXF9A0"
title = "Zero DOC006 findings (stale code citations)"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-28T21:41:08Z"
updated = "2026-10-28T23:53:18Z"
idempotency_key = "b755-doc006"
scope = ["crates/frob-doc/**", "crates/frob-obligations/**", "crates/gob-text/**", "crates/gob-packs/**", "crates/gob-ir/src/symref.rs", "crates/gob-cli/src/explain.rs", "docs/design/build-test-ci.md", "notes/**"]

[[acceptance]]
text = "frob check reports zero DOC006 findings"
bound = false
+++

Split from ~B755NCR (mis-scoped to docs/design/docs.md). Fix citations in crates/frob-doc, frob-obligations, gob-text, gob-plan, gob-packs, gob-ir symref.rs, gob-cli explain.rs, docs/design/build-test-ci.md 179-180, notes/. Widen lease as needed.
