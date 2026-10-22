+++
id = "01M5H85830JZJMYGV53YX6GQNR"
title = "fix_summary_line points users at nonexistent 'frob fix' verb"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-22T07:28:10Z"
updated = "2026-10-22T07:28:10Z"
scope = ["crates/frob-check/src/summary.rs"]
+++

Found while working ~M7F4X3Q: siblings remedies::remedies_name_only_existing_commands_and_flags fails because summary.rs:17 says 'frob fix --interactive'; no such verb exists.
