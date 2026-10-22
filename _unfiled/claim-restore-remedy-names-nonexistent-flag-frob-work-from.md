+++
id = "01M5JMG3QGMK2QGCTYQ5TB9ZM4"
title = "claim_restore remedy names nonexistent flag frob work --from"
type = "bug"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-22T20:23:03Z"
updated = "2026-10-22T20:45:18Z"
scope = ["crates/frob-worktree/src/claim_restore.rs"]

[[acceptance]]
text = "Given the claim_restore remedy text, when checked by the remedies sibling test, then it names only existing frob verbs and flags"
bound = false
+++

Found while working YX6GQNR: remedies::remedies_name_only_existing_commands_and_flags still fails at claim_restore.rs:54 ('frob work {handle} --from <parked branch>'; frob work has no --from). Reword to a real remedy.
