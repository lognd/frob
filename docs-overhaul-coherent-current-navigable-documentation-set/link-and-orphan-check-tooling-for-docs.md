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
updated = "2026-10-31T03:22:06Z"
idempotency_key = "docs-ovh-linkcheck"
scope = ["crates/frob-doc/**", "crates/frob-obligations/src/rules/doc007.md", "crates/frob-obligations/src/rules/doc007.rs", "crates/frob-obligations/src/rules/mod.rs", "crates/frob-obligations/src/docstatus.rs", "crates/frob-obligations/src/lib.rs", "crates/frob-obligations/Cargo.toml", "crates/frob-obligations/src/doc_orphan.rs", "crates/frob-obligations/tests/doc_orphan.rs", "crates/frob/src/explain_cmd.rs", "frob.toml", "docs/design/documentation.md", "docs/reference/rules/DOC007.md", "docs/reference/rules/README.md", "crates/frob-obligations/tests/mdtest/doc007.md", "docs/README.md"]

[[acceptance]]
text = "A frob verb or rule reports broken relative links, broken anchors and orphan pages across docs/ and root md; wired into frob check; tests added; documented"
bound = true
+++

Extend frob-doc; keep logging and Result idioms. Follow docs/design/documentation.md; keep frob:doc bindings and run frob ack for drift; never hand-edit docs/reference or docs/schemas; ASCII only. Each page gets a status header and stays current or is marked superseded via docs/MOVED.toml.
