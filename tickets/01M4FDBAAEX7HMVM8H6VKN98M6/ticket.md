+++
id = "01M4FDBAAEX7HMVM8H6VKN98M6"
title = "P1 grmb planning: grammar, contextual words, MDL022-MDL031, U encoding, fmt, corpus"
type = "story"
category = "todo"
priority = "medium"
points = 13
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T04:04:41Z"
updated = "2026-10-09T04:58:46Z"
labels = ["grimble"]
scope = ["crates/grimble-model/**", "docs/design/rules.md", "docs/design/grmb-spec.md", "docs/design/grmb-planning.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FCWY3H8CRHYYHVQ19SEHXJ"

[[acceptance]]
text = "Given the corpus directories under plan/, when the grimble-model corpus runs, then each of MDL022-MDL031 has a firing and a clean case and the U term of every construct of grmb-planning.md 8.2 matches its expect file"
bound = false

[[acceptance]]
text = "Given the worked examples of grmb-planning.md 12 and 13, when grimble check loads them, then they parse with zero MDL Errors and grimble fmt is a digest-preserving fixed point on them"
bound = false

[[acceptance]]
text = "Given a major-2 model that names a node system or page, when it is parsed after this change, then it loads unchanged (contextual words are additive)"
bound = false
+++

grmb-planning.md 2, 3, 4, 5.1-5.6, 7.1, 8 and 15 row P1. Lexer tokens => -|> -?> * and the contextual planning words (2.1, additive to major 2); parser for system, actor, goal, step, scenario, impl, page; scenario typing (outcome, collected set, error set, retry bound) as MDL022-MDL031; U encoding and facets of 8.2; fmt rules of 8.3; conformance corpus under crates/grimble-model/tests/corpus/plan/ with both worked examples; rules.md MDL range note.
