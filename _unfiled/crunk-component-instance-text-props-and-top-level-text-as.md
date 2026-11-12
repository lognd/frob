+++
id = "01M5H5P5NTT9XAYR4ZSA4RRB8F"
title = "crunk: component-instance text props and top-level text as literal copy"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T06:44:59Z"
updated = "2026-11-12T08:24:07Z"
scope = ["crates/crunk-rules/src/rules/content001.rs", "crates/crunk-rules/tests/**", "changelog.d/01M5H5P5NTT9XAYR4ZSA4RRB8F.*", "crates/crunk-rules/src/content_files.rs", "docs/reference/rules/CONTENT001.md", "crates/crunk-rules/src/rules/content001.md"]

[[acceptance]]
text = "Given a component instance whose text prop or a top-level text node holds literal copy, when CONTENT001 runs, then it reports the literal as it does for element own-text"
bound = true
+++

found while working ~VAAWD0R: CONTENT001 only sees element own-text and copy attributes.
