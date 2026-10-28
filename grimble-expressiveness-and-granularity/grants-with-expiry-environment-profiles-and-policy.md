+++
id = "01M5XNNJTK08K3CB98MCT14W34"
title = "Grants with expiry, environment profiles and policy composition"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:10Z"
updated = "2026-10-28T12:55:50Z"
idempotency_key = "grimble-expr-expiry-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness", "no-story"]
scope = ["crates/grimble-model/src/**", "crates/grimble-bind/src/**", "docs/design/grmb-spec.md"]

[[acceptance]]
text = "an expired may grant fails check naming the date; a grant scoped to profile test does not cover non-test code"
bound = false

[[acceptance]]
text = "a named policy block can be applied to several nodes and its grants appear in grimble status per node"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. A may grant has no until=, no profile (test-only network, dev-only stdout), and policies cannot be composed beyond packs and include. Temporary grants therefore become permanent and test-only needs (tests spawning processes) are granted to whole trees (design/model.grmb in this repo grants exec at crates/*/tests/**). Add `until=DATE` on may (expired grant is an error), `profile test|prod|NAME` scoping selected by config or selector, and `policy NAME { ... }` blocks a node can `use`.

no-story: internal engineering task in grimble-model; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
