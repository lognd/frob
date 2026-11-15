+++
id = "01M7EX7Z2EZ1CS5N1X4GXBA9WG"
title = "land candidate: fail closed when the post-drop git reset --hard fails"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:10:19Z"
updated = "2026-11-15T06:10:19Z"
labels = ["no-story"]
+++

Source: frob-audit-core.md L1, frob-audit-meta.md M1. Evidence: crates/frob-land/src/candidate.rs:275-284 logs reset.ok() but ignores a failed reset, leaving the dropped merge in the candidate. Remedy: propagate the reset failure as an error and abort the candidate. Add negative tests for hunk-drop handling. Files: crates/frob-land/src/candidate.rs.
