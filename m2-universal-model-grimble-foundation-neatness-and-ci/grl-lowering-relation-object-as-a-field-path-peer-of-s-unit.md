+++
id = "01M5ETB7Y10SZTEWWKBR3AHZ1T"
title = "GRL lowering: relation object as a field path (peer of s.unit) and as roles snippets (NEAT031)"
type = "task"
category = "in-progress"
priority = "low"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T08:48:17Z"
updated = "2026-10-21T22:38:17Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/lower/roles.rs", "crates/gob-plan/src/lower/mod.rs", "crates/gob-plan/tests/lower.rs", "crates/gob-plan/tests/lower_roles.rs", "changelog.d/01M5ETB7Y10SZTEWWKBR3AHZ1T.added.md"]
+++

Found while working ~ACSP6CZ. lower/convert.rs with_object rejects a path object with more than one segment ("this relation object", NEAT031 `peer of s.unit`); rust`...` as roles snippet matching is also unverified. Needed for NEAT031 examples; then delete KNOWN_ENGINE_GAPS entries.
