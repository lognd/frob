+++
id = "01M6D6ZWPQF3797CF5YCV4PB87"
title = "grimble-model: distinguish legacy 'requires page' from 'on page' (MDL012) and print r# in fmt"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-02T04:06:30Z"
updated = "2026-11-02T04:49:50Z"
scope = ["crates/grimble-model/src/**", "crates/grimble-model/tests/**"]
+++

found while working ~0Q2TMVM: both spellings parse to PClauseKind::RequiresPage and fmt prints 'requires page'; canonical 'on page' plus MDL012 on the legacy spelling needs a spelling flag (~V82CNAR territory). Ident has no raw flag so fmt cannot print r# for keyword-named identifiers.
