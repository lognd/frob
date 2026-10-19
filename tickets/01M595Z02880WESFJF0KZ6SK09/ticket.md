+++
id = "01M595Z02880WESFJF0KZ6SK09"
title = "Regenerate stale docs/reference/grl/catalog.md (class_selector missing; GEN001 fails frob check cargo stage)"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "high"
reporter = "lognd"
created = "2026-10-19T04:15:52Z"
updated = "2026-10-19T04:17:34Z"
scope = ["docs/reference/grl/catalog.md"]
+++

Found while working PWS7RWW: gob-dev gen all --check reports docs/reference/grl/catalog.md stale at base b3a8620cb; the generated output adds a class_selector entry (style rule selector) that the committed doc lacks. Run cargo dev gen all in a ticket that owns docs/reference and commit the regenerated file. Blocks frob check --ticket on this base via TOOL001/GEN001.
