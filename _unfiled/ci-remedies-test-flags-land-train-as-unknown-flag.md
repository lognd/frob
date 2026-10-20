+++
id = "01M50C2K05GD8CMSG4HFE7C4ZC"
title = "ci: remedies test flags 'land --train' as unknown flag"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-15T18:09:32Z"
updated = "2026-10-15T18:50:54Z"
scope = ["crates/frob-land/src/candidate.rs", "crates/frob/tests/siblings/remedies.rs"]

[[acceptance]]
text = "siblings remedies test passes"
bound = true
+++

frob-cli siblings remedies_name_only_existing_commands_and_flags fails: crates/frob-land/src/candidate.rs:285 names 'frob land --train' which does not exist. Fix the remedy text to an existing flag/command (or add the flag if train is intended).
