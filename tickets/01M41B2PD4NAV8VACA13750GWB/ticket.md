+++
id = "01M41B2PD4NAV8VACA13750GWB"
title = "[pm] strict escalates PM001 and PM002 (and other PM warnings the design names) to Error"
type = "task"
category = "in-progress"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-03T16:55:39Z"
updated = "2026-10-03T17:36:56Z"
scope = ["crates/frob-pm/src/config.rs", "crates/frob-pm/src/rules/**", "docs/reference/config.md", "docs/schemas/config.json", "crates/frob-check/src/product.rs", "crates/frob/tests/cli.rs", "crates/frob/tests/pm_config.rs", "crates/frob/tests/milestone.rs", "changelog.d/*3750GWB*"]

[[acceptance]]
text = "Given [pm] strict = true and a milestone without exit criteria, when frob check runs, then PM001 is an error"
bound = true
+++

~JWAAVRY shipped PM001/PM002 as Warn only because [pm] strict does not exist. Add the knob (default false) and apply it to the rules pm-enforcement.md marks as Error under strict.
