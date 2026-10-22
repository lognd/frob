+++
id = "01M5H85830JZJMYGV53YX6GQNR"
title = "fix_summary_line points users at nonexistent 'frob fix' verb"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T07:28:10Z"
updated = "2026-10-22T20:23:03Z"
scope = ["crates/frob-check/src/summary.rs", "docs/design/diagnostics.md"]

[[acceptance]]
text = "Given the fix summary line, when rendered, then it names only existing frob verbs and flags"
bound = false
+++

Found while working ~M7F4X3Q: siblings remedies::remedies_name_only_existing_commands_and_flags fails because summary.rs:17 says 'frob fix --interactive'; no such verb exists.
