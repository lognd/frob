+++
id = "01M67VEKBESFK2C23JMXV82RW9"
title = "Link and orphan check tooling for docs"
type = "docs"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T02:08:37Z"
updated = "2026-10-31T02:45:55Z"
idempotency_key = "docs-ovh-linkcheck"
scope = ["crates/frob-doc/**", "crates/frob-obligations/src/rules/doc007.md", "crates/frob-obligations/src/rules/doc007.rs", "crates/frob-obligations/src/rules/mod.rs", "crates/frob-obligations/src/docstatus.rs", "crates/frob-obligations/src/lib.rs"]

[[acceptance]]
text = "A frob verb or rule reports broken relative links, broken anchors and orphan pages across docs/ and root md; wired into frob check; tests added; documented"
bound = false
+++

Extend frob-doc; keep logging and Result idioms. Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
