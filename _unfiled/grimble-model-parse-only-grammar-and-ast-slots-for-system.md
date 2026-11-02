+++
id = "01M6CFZKEKAJM0YF9FB5820W3Y"
title = "grimble-model: parse-only grammar and AST slots for system ambient/non_goal, one_of groups, sorry holes, actor 'in node', impl chain, multi-node lines"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-01T21:24:23Z"
updated = "2026-11-01T23:18:54Z"
scope = ["crates/grimble-model/src/parse/plan.rs", "crates/grimble-model/src/parse.rs", "crates/grimble-model/src/plan.rs", "crates/grimble-model/src/keywords.rs", "crates/grimble-model/tests/corpus/**", "crates/grimble-model/src/fmt/plan.rs", "crates/grimble-model/src/fold/plan.rs", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/src/plan_index.rs"]

[[acceptance]]
text = "Parser accepts ambient, non_goal, one_of group, sorry because=, actor 'in node REF', impl 'chain', and 'node a : t; node b : t;' multi-node lines, with AST slots in src/plan.rs and no MDL000 on them"
bound = false

[[acceptance]]
text = "Corpus cases under tests/corpus cover each new construct (parse + round-trip); no rule or mockup-loads criterion (moved to the rule-family tickets)"
bound = false
+++

found while working ~ZP5KR2Q. Loading notes/research/grmb-corpus/domains d01..d11 yields MDL000: 'unexpected ambient, expected an item' (system body), 'non_goal', 'in node' on actor, 'chain' impl clause, 'one_of' groups (MDL031 one_of cannot name variant), 'sorry because=' hole, 'node a : trusted; node b : trusted;' multi-decl, 'producer'/'consumer' reserved. AST in src/plan.rs has no slots for these.
