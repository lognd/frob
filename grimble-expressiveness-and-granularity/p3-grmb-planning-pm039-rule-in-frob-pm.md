+++
id = "01M6PJTS0C0E4G01XPY5JKQ2BP"
title = "P3 grmb planning: PM039 rule in frob-pm"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-05T19:26:35Z"
updated = "2026-11-05T19:26:35Z"
scope = ["crates/frob-pm/src/rules/**", "crates/frob-pm/tests/**", "docs/design/pm-enforcement.md", "changelog.d/**"]

[[acceptance]]
text = "Given PM039 per grmb-planning.md 10, when its condition holds, then it is reported with a remedy"
bound = false
+++

Split from ~5952RXW, which delivered PM037 only. PM038 is emitted by the design_bound guard (~D4WAD09). Follows the PM037 pattern in crates/frob-pm/src/rules/pm037.rs and eval/design.rs.
