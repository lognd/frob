+++
id = "01M5XNNJXHY369P16NZJMQ3SX6"
title = "CAP diagnostics: anchor at the call site, suggest the narrowest grant, explain a decision, test policies"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:10Z"
updated = "2026-10-27T03:15:10Z"
idempotency_key = "grimble-expr-diag-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble/src/**", "crates/grimble-bind/src/rules/cap001.md"]

[[acceptance]]
text = "CAP001 findings carry the code location of each use and a suggested narrowest grant"
bound = false

[[acceptance]]
text = "grimble why on a call site prints the atom, covering grants or the missing grant, any exception, and the verdict"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. CAP001 is anchored at the node declaration in the .grmb (caps.rs:588), lists at most 3 example sites (EXAMPLES, caps.rs:45) and its remedy is 'Grant the atom with may on the node, or remove the use' (docs/reference/rules/CAP001.md), which nudges toward broad grants. There is no way to ask why a given call is allowed or denied, and no policy test harness (expected allow/deny cases next to the model). Emit one finding per call site (located in code), include a copy-pasteable narrowest grant (`may fs.write("<observed path>") at "<file>::<symbol>"`), add `grimble why <file:line|symref>` printing the matching grants/exceptions and the cell computation, and a `grimble test-policy` over declared allow/deny cases. Matrix output is ~N8ZASNE; do not duplicate it.
