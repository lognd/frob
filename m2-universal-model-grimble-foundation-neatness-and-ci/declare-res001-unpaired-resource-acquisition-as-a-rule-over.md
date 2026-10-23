+++
id = "01M4MGE2XKGBNJEV1AECPBVHQF"
title = "Declare RES001 unpaired resource acquisition as a rule over grimble_lints::res::scan, with page and corpora"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-11T03:34:49Z"
updated = "2026-10-23T11:37:14Z"
scope = ["crates/grimble-lints/**", "crates/grimble-check/src/product_rules.rs", "crates/grimble-check/Cargo.toml", "docs/reference/rules/RES*.md", "docs/design/**", "docs/reference/**", "docs/schemas/**", "Cargo.lock", "crates/grimble-check/**"]

[[links]]
kind = "blocked-by"
target = "01M4MBJ35HGM0P2MH4B7YMB3EQ"

[[acceptance]]
text = "Given a TypeScript file with performance.mark() and no clearMarks, when grimble check runs, then RES001 fires at Warn; given the paired release, then it stays quiet"
bound = false

[[acceptance]]
text = "Given an Unknown site (handle returned from the scope), when grimble check runs, then the finding is Unresolved, not Warn"
bound = false
+++

Split from ~4CESXMT, which landed the table-driven detector. Needed: #[rule] declaration (Unknown sites are Unresolved, Certain ones Warn), rule page with fire and clean mdtest cases for performance.mark, Map.set and setTimeout, product_rules wiring, ramp-in (new_rule_warn_releases), gen all. Follows the pattern of ~7YMB3EQ for ERR001-003.
