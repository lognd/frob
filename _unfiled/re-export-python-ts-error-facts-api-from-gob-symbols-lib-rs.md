+++
id = "01M68YK32M30DKPTJ8XYKHZ9AH"
title = "Re-export Python/TS error-facts API from gob-symbols lib.rs"
type = "chore"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-10-31T12:22:44Z"
updated = "2026-10-31T12:22:44Z"
scope = ["crates/gob-symbols/src/lib.rs", "crates/gob-symbols/src/python.rs", "crates/gob-symbols/src/typescript/fold.rs"]

[[acceptance]]
text = "Given the gob-symbols crate, when built, then python_error_facts, typescript_error_facts and UnitErrorFacts are re-exported and the expect(dead_code) attrs are gone"
bound = false
+++

Found while working ~2J7R2HK (lib.rs leased by another ticket).
