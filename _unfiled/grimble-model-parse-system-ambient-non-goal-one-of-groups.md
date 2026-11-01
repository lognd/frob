+++
id = "01M6CFZKEKAJM0YF9FB5820W3Y"
title = "grimble-model: parse system ambient/non_goal, one_of groups, sorry holes, actor 'in node', impl chain, 'node X;' markers so corpus mockups d01..d11 load"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-01T21:24:23Z"
updated = "2026-11-01T21:24:33Z"
scope = ["crates/grimble-model/src/parse/plan.rs", "crates/grimble-model/src/parse.rs", "crates/grimble-model/src/plan.rs", "crates/grimble-model/src/keywords.rs", "crates/grimble-model/tests/corpus/**"]
+++

found while working ~ZP5KR2Q. Loading notes/research/grmb-corpus/domains d01..d11 yields MDL000: 'unexpected ambient, expected an item' (system body), 'non_goal', 'in node' on actor, 'chain' impl clause, 'one_of' groups (MDL031 one_of cannot name variant), 'sorry because=' hole, 'node a : trusted; node b : trusted;' multi-decl, 'producer'/'consumer' reserved. AST in src/plan.rs has no slots for these.
