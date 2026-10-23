+++
id = "01M4MBJ35HGM0P2MH4B7YMB3EQ"
title = "Declare ERR001-ERR003 as rules over grimble_lints::err::scan, with pages and corpora, and run them in grimble check"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-11T02:09:38Z"
updated = "2026-10-23T11:26:34Z"
scope = ["crates/grimble-lints/**", "crates/grimble-check/src/product_rules.rs", "crates/grimble-check/Cargo.toml", "docs/reference/rules/ERR*.md", "docs/design/**", "docs/reference/**", "docs/schemas/**", "Cargo.lock", "crates/grimble-check/**"]

[[acceptance]]
text = "Given ERR001-ERR003 declared as rules, when grimble check runs on a corpus with certain error-handling defects, then Certain sites warn and Unknown sites are Unresolved"
bound = true

[[acceptance]]
text = "Each ERR rule has a docs page with a fire case and a clean case, and appears in the rules index"
bound = false
+++

found while working ~K4B9CKF: the detectors landed; still needed: #[rule] declarations (Unknown sites are Unresolved, Certain ones Warn), rule pages with fire and clean mdtest cases, product_rules wiring, ramp-in (new_rule_warn_releases), depends on the FileCx language ticket
