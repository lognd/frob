+++
id = "01M4CTE8SH7DZ2R7T086T3ZQX6"
title = "Verbs declare flags once: clap derive for every frob, grimble and crunk verb (audit M15)"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:46Z"
updated = "2026-10-08T03:55:46Z"
scope = ["changelog.d/**", "crates/frob/**", "crates/grimble/**", "crates/crunk/**", "crates/gob-cli/**", "crates/frob-*/src/cli.rs"]

[[acceptance]]
text = "Given every verb, when inspected, then no flag is looked up by string name (lint)"
bound = false

[[acceptance]]
text = "Given the generated CLI reference, when regenerated, then it is unchanged"
bound = false
+++

notes/review/audit-2026-10-07.md M15: 72 verbs declare each flag twice (builder plus string lookups). Keep generated CLI docs byte-identical (GEN001).
