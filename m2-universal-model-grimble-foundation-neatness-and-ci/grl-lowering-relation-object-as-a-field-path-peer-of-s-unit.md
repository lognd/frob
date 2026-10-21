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
updated = "2026-10-21T22:45:33Z"
labels = ["area:grl"]
scope = ["crates/gob-plan/src/lower/roles.rs", "crates/gob-plan/src/lower/mod.rs", "crates/gob-plan/tests/lower.rs", "crates/gob-plan/tests/lower_roles.rs", "changelog.d/01M5ETB7Y10SZTEWWKBR3AHZ1T.added.md", "crates/gob-plan/src/lower/convert.rs", "crates/gob-plan/tests/ten_rules/main.rs", "docs/design/grl-spec.md"]

[[acceptance]]
text = "A relation object written as a field path (p peer of s.unit) lowers"
bound = false

[[acceptance]]
text = "An unbound first segment of a field-path object is an unknown var"
bound = false

[[acceptance]]
text = "A roles snippet that is a branch or loop with an empty or one-call body lowers"
bound = false

[[acceptance]]
text = "A roles snippet with another root, an else, or another body is refused by name"
bound = false
+++

Found while working ~ACSP6CZ. lower/convert.rs with_object rejects a path object with more than one segment ("this relation object", NEAT031 `peer of s.unit`); rust`...` as roles snippet matching is also unverified. Needed for NEAT031 examples; then delete KNOWN_ENGINE_GAPS entries.
