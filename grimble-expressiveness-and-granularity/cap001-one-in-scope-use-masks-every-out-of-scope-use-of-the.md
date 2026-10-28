+++
id = "01M5XNNH8ZMXDQJWNZBDK5702P"
title = "CAP001: one in-scope use masks every out-of-scope use of the same atom in a node"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-28T12:54:34Z"
idempotency_key = "grimble-expr-mask-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-capabilities/src/lib.rs", "crates/grimble-bind/tests/**"]

[[acceptance]]
text = "a regression test with one covered and one uncovered use of the same atom in one node fires CAP001 for the uncovered use only"
bound = false

[[acceptance]]
text = "the cell computation is per use (or per unit) as binding.md 7.2 item 3 states"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. matrix_undeclared (crates/grimble-bind/src/caps.rs:551-564) builds ONE NodeInput per node and language and inserts the atom into input.grants when ANY use of it is covered at its file; cap001 (caps.rs:597-599) then only flags a Must/certain use when the matrix cell is Undeclared, which it no longer is. binding.md 7.2 item 3 requires the decision per identity. Repro: node app owns src/**, grants `may fs.write at "src/wrap.rs"`; src/wrap.rs and src/broken.rs both call std::fs::write; zero CAP001. Delete the wrap.rs use and CAP001 fires for broken.rs.
