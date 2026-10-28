+++
id = "01M5XNNHBSPSM5XFG8FM64HENY"
title = "CAP: honour symbol-granular at selectors (file::Symbol) instead of collapsing to files"
type = "security"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:08Z"
updated = "2026-10-28T15:28:58Z"
idempotency_key = "grimble-expr-symat-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-bind/src/owner.rs", "crates/gob-walk/src/**", "crates/grimble-bind/tests/**", "crates/grimble-bind/src/grants.rs"]

[[acceptance]]
text = "a use in a sibling function of the at-selected symbol fires CAP001; a use inside the selected symbol (and its nested closures) is covered"
bound = false

[[acceptance]]
text = "CAP002 and the grant ratchet measure breadth in units for symbol selectors"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. grmb-spec.md 4.1 shows `may net.connect("api.github.com") at "crates/frob-gh/src/lib.rs::GhClient.*"` but caps.rs:18 states 'a grant's at selector is compared at file granularity' and covers() uses select_files (caps.rs:515-519). Repro: `may fs.read at "src/lib.rs::allowed"`; fn sneaky in the same file reading ~/.ssh/id_rsa is clean. Judge coverage against the unit (the edge's from-symbol) and its enclosing symbols, not its file.
