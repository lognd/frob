+++
id = "01M59QKE60PDB1GDWTDEBAQ4JG"
title = "NEAT remaining rules and [neat] config after the first two"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-19T09:24:08Z"
updated = "2026-10-28T12:55:52Z"
labels = ["no-story"]
scope = ["crates/grimble-lints/**", "crates/gob-ir/**"]

[[acceptance]]
text = "NEAT001-009, NEAT011-013, NEAT030 have detectors with fire/clean corpora"
bound = false

[[acceptance]]
text = "The [neat] config table is materialized (guard_weight, effects vocabulary, core paths)"
bound = false

[[acceptance]]
text = "NEAT010 and NEAT031 also cover Python and TypeScript"
bound = false
+++

Follow-up to ~GFWC6QP, which shipped NEAT010 and NEAT031 for Rust only. Deferred: NEAT003 call-site part, NEAT030 sandwich check, NEAT012 captured reads, other languages, BOUND_TOOLS entries for NEAT001/005/009, grimble check wiring.

no-story: internal engineering task in grimble-lints; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
