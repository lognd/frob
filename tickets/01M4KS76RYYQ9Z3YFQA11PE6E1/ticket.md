+++
id = "01M4KS76RYYQ9Z3YFQA11PE6E1"
title = "Satisfy the changelog_fragment guard for test and chore tickets whose diff touches only tests, via a [pm] knob"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "Claude"
created = "2026-10-10T20:49:07Z"
updated = "2026-10-10T20:49:07Z"
scope = ["crates/frob-evidence/**", "crates/frob-pm/**", "crates/frob-release/**", "docs/reference/config.md", "docs/schemas/config.json", "changelog.d/**"]

[[acceptance]]
text = "Given a ticket of type test or chore whose diff touches only tests, when it lands, then the changelog fragment guard is satisfied without --no-changelog, per a [pm] done knob"
bound = false
+++

split from ~0SDR858 criterion 2 (logand.app-v2 F-551): the pytest node-id half landed there; this needs a new config knob, the diff classification and docs
