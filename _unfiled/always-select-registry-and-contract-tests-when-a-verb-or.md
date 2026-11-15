+++
id = "01M7EX90AHPP4MYSMJYHJB23XZ"
title = "always select registry and contract tests when a verb or rule is added"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:53Z"
updated = "2026-11-15T06:10:53Z"
labels = ["no-story"]
+++

Source: frob-audit-meta.md M4. Evidence: touched-set selection can miss registry/contract tests. Remedy: add always-select globs in frob test selection. Files: crates/frob-test*, frob.toml.
