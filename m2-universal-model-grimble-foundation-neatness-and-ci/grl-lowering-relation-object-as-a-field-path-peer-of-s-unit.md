+++
id = "01M5ETB7Y10SZTEWWKBR3AHZ1T"
title = "GRL lowering: relation object as a field path (peer of s.unit) and as roles snippets (NEAT031)"
type = "task"
category = "todo"
priority = "low"
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T08:48:17Z"
updated = "2026-10-21T08:48:17Z"
labels = ["area:grl"]
+++

Found while working ~ACSP6CZ. lower/convert.rs with_object rejects a path object with more than one segment ("this relation object", NEAT031 `peer of s.unit`); rust`...` as roles snippet matching is also unverified. Needed for NEAT031 examples; then delete KNOWN_ENGINE_GAPS entries.
