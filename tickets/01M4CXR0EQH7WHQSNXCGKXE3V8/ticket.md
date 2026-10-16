+++
id = "01M4CXR0EQH7WHQSNXCGKXE3V8"
title = "EXPORT001/002 and TOKEN002-009: export drift and parity across targets, token schema, cycles, unused, naming, mode completeness, scopes, near-duplicates, deprecated"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-08T04:53:31Z"
updated = "2026-10-16T05:51:39Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/crunk-tokens/**", "crates/crunk-rules/**", "crates/crunk-spec/**", "docs/crunk/**", "docs/schemas/**"]

[[acceptance]]
text = "Given fire and clean mdtest cases for each rule, when the corpus runs, then each rule fires only on its fire case"
bound = true
+++

docs/design/crunk.md section 6; catalogue in notes/research/crunk-design-2026-10-08.md E3.
