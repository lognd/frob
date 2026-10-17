+++
id = "01M55ZW4P41ES0N6HBZ9TQ01YC"
title = "List gob_check and gob_directives marker-host rules in frob-check product_rules!"
type = "task"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-17T22:31:44Z"
updated = "2026-10-17T23:44:27Z"
idempotency_key = "jbd7std-product-rules"
scope = ["crates/frob-check/**", "crates/gob-directives/src/lib.rs"]
+++

found while working ~JBD7STD: the new gob-check and gob-directives declared rules are not listed in crates/frob-check/src/product_rules.rs (that file was under ~MXXGNZ3 lease). Add them and verify frob check output unchanged.
