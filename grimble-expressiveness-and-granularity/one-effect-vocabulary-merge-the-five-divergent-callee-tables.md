+++
id = "01M5XNNJC7TZQ6988T8P8A3N49"
title = "One effect vocabulary: merge the five divergent callee tables into the shared registry"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-27T03:15:09Z"
updated = "2026-10-27T03:15:09Z"
idempotency_key = "grimble-expr-unify-2026-10-26"
labels = ["grimble", "audit:grimble-expressiveness"]
scope = ["crates/gob-ir/src/registry.rs", "crates/gob-symbols/src/ambient.rs", "crates/grimble-check/src/effects.rs", "crates/grimble-lints/src/neat/**", "crates/grimble-model/src/atoms.rs"]

[[acceptance]]
text = "NEAT, COH002, gob-symbols ambient and CAP read callee names from gob_ir::registry only; a test fails if a second table appears"
bound = false

[[acceptance]]
text = "frob:effects claim words are registry atoms (with the old words as aliases)"
bound = false
+++

Audit report: /tmp/claude-1000/-home-logan-projects-frob/9dfed69c-963b-4123-8ee8-0030bb0775b3/scratchpad/grimble-audit.md. grimble-model.md 9.6 says 'There is one callee-vocabulary table per language; the NEAT [neat.effects] tables and grimble's detectors are views over it'. In fact there are five: gob-ir registry + grimble-model atoms (CAP), gob-symbols/src/ambient.rs (clock, rng, env, stdio, exit), grimble-check/src/effects.rs (COH002, the only one with TypeScript), grimble-lints/src/neat/mod.rs:107-122 plus the closed Atom enum in neat/effects.rs (frob:effects claims use words net/env/stdio that are not CAP atoms), and gob-trust/src/effects (pack broker). They disagree (NEAT knows TcpStream::connect as net; CAP detects no network). Make the registry the single source and derive the others from it. Related: ~T28A73Q (COH002 tables into gob-caps) and ~WNH8N7X (vocab classes for NEAT013); this ticket is the umbrella merge and must not duplicate their acceptance.
