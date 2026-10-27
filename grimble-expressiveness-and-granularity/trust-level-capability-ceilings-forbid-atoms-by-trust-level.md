+++
id = "01M5XNNJMSCGPFS84V3PZQKTNC"
title = "Trust-level capability ceilings: forbid atoms by trust level or node kind"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:10Z"
updated = "2026-10-27T03:15:10Z"
idempotency_key = "grimble-expr-trustceil-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/grimble-bind/src/caps.rs", "crates/grimble-model/src/**", "docs/design/grmb-spec.md"]

[[acceptance]]
text = "a grant on a foreign node that exceeds a declared ceiling is an error naming the ceiling"
bound = false

[[acceptance]]
text = "the ceiling syntax is in grmb-spec with examples"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. Node trust (foreign < authenticated < trusted) never enters capability evaluation (caps.rs has no reference to trust). A foreign node can be granted process.spawn or fs.write and nothing objects. Add policy-level ceilings, e.g. `policy { foreign may not process.spawn, fs.write; }` or per-kind ceilings from packs, firing a CAP rule when a grant exceeds the ceiling.
