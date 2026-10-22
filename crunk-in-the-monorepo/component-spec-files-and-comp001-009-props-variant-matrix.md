+++
id = "01M4CXR7CHD30VMWHMRD6TTN3F"
title = "Component spec files and COMP001-009: props, variant matrix, states, token bindings, a11y contract, code mapping"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-08T04:53:38Z"
updated = "2026-10-22T05:36:46Z"
scope = ["changelog.d/**", "crates/crunk-spec/**", "crates/crunk-check/**", "crates/crunk-rules/**", "docs/**", "Cargo.lock"]

[[acceptance]]
text = "Given a component spec missing a required state or with an unbound literal, when crunk check runs, then COMP and STATE findings fire with the node id"
bound = true
+++

docs/design/crunk.md sections 2 and 6.
