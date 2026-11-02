+++
id = "01M6C52KX8TM6CC38XZDK583KA"
title = "grimble-model: carry cycle 1 spellings and facts in the planning AST (open, idempotent, within, arm arrow, use, verified_by)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M69AHE03R04HDKKDT03B2YRN"
reporter = "lognd"
created = "2026-11-01T18:13:48Z"
updated = "2026-11-02T07:54:51Z"
labels = ["grimble"]
scope = ["crates/grimble-model/src/plan.rs", "crates/grimble-model/src/ast.rs", "crates/grimble-model/src/fmt.rs", "crates/grimble-model/src/fmt/**", "crates/grimble-model/src/fold/plan.rs", "crates/grimble-model/src/plan_check.rs", "crates/grimble-model/src/plan_index.rs", "crates/grimble-model/src/parse/plan.rs", "crates/grimble-model/src/parse.rs", "crates/grimble-model/src/text.rs", "crates/grimble-model/src/fold.rs", "crates/grimble-model/src/check.rs", "crates/grimble-bind/src/model.rs", "crates/grimble-model/tests/cycle1_spellings.rs", "changelog.d/01M6C52KX8TM6CC38XZDK583KA.fixed.md"]

[[acceptance]]
text = "The AST records step open/closed and idempotent, retry within and an omitted step (Option), the arm arrow spelling, use vs include, and verified_by vs evidence tests; fmt round-trips each cycle 1 spelling unchanged."
bound = true
+++

found while working ~M7Y61ZQ: the parser accepts these forms but drops open, idempotent and within (tracing debug only), defaults an omitted retry step in the parser, and fmt rewrites use to include and entity verified_by to evidence tests. plan.rs was leased by ~2QQ6V9H so it was not edited there.
