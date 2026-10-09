+++
id = "01M4FDBBXG990QVX35HERF5VCQ"
title = "P2 grmb planning: realization and verified_by binding, status, obligations, PLAN rules, graph JSON"
type = "story"
category = "todo"
priority = "medium"
points = 8
parent = "01M4FDAD29CBF7S4EM2FKR5TXQ"
reporter = "lognd"
created = "2026-10-09T04:04:42Z"
updated = "2026-10-09T04:04:42Z"
labels = ["grimble"]
scope = ["crates/grimble-bind/**", "crates/grimble/**", "crates/grimble-check/**", "docs/schemas/sibling.json", "docs/design/rules.md", "docs/design/sibling-contract.md", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4FDBAAEX7HMVM8H6VKN98M6"

[[acceptance]]
text = "Given the web example of grmb-planning.md 12, when grimble graph --json runs, then every planning entity carries status, status_hi and level, the obligations array lists the documented PLAN001, PLAN003 and PLAN005 entries, and the document validates against the strict sibling.json schema"
bound = false

[[acceptance]]
text = "Given an impl whose realization selector matches nothing, when grimble check runs, then SYS004 is reported once and the obligation unbound_impl is listed without a second finding"
bound = false
+++

grmb-planning.md 5.7, 5.8, 6.1, 7.2 and 9, row P2. Realization and verified_by rows in B; status and status_hi per entity; obligations list; PLAN family registered in rules.md 3 with PLAN001-PLAN005 and PLAN007-PLAN010; graph JSON and check --json additions as optional keys under grimble.graph/1; sibling.json defs and strict schema.
