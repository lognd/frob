+++
id = "01M4FGZ5X08674W78BEXQG043R"
title = "v1 atom spellings: hyphenated names get one actionable finding and a migration table"
type = "story"
category = "todo"
priority = "low"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:07:57Z"
updated = "2026-10-09T05:07:57Z"
idempotency_key = "logand-gaps-D1"
labels = ["adoption:logand-app", "grimble"]
scope = ["docs/design/migration.md", "docs/design/packs.md", "crates/grimble-model/**", "changelog.d/**"]

[[acceptance]]
text = "Given may net-mutate, when grimble check runs, then exactly one finding names the snake_case spelling net_mutate"
bound = false

[[acceptance]]
text = "Given migration.md, when read, then it lists every v1 atom with its v2 spelling or pack"
bound = false
+++

Repro 02-hyphenated-atom-lexing (~/projects/frob-v2-repros/logand-grimble-20261009/02-hyphenated-atom-lexing): net-mutate is two MDL000 findings (unexpected - then unexpected mutate) instead of a pointer to the snake_case rule (packs.md section 3 notes the rule). Add a migration table of v1 atom names to v2 spellings to migration.md and make the lexer/parser emit one finding naming net_mutate.
