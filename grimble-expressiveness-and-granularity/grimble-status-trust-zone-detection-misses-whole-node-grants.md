+++
id = "01M5XNP8HP847DC163G53K097K"
title = "grimble status: trust-zone detection misses whole-node grants without at and grants carrying arguments"
type = "bug"
category = "todo"
priority = "low"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:32Z"
updated = "2026-10-27T03:15:32Z"
idempotency_key = "grimble-expr-zones-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/grants.rs", "crates/grimble-bind/tests/**"]

[[acceptance]]
text = 'a node with owns "**" granting every atom without at is reported as a trust zone'
bound = false

[[acceptance]]
text = "adding a string argument to a blanket grant does not hide it from the trust-zone list while arguments are unenforced"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. trust_zones (crates/grimble-bind/src/grants.rs:360-366) only groups grants that have an `at` selector and no string arguments. A node `owns "**"` that grants every atom with no `at` (the grant then covers the node owns set) is not listed as a zone, and `may fs("x") at "**"` escapes because arguments are assumed narrowing although caps.rs ignores them. Treat a grant without `at` as scoped to the node owns selectors, and ignore arguments for breadth until they are enforced (~5X9CAQE).
