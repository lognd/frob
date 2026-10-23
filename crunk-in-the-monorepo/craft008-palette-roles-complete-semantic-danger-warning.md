+++
id = "01M5HM3W18AJZET52BZBEJFYD4"
title = "CRAFT008 palette roles complete: semantic danger/warning/success roles in [palette.roles]"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXT3N608HMB1A77VTT4YXX"
reporter = "lognd"
created = "2026-10-22T10:57:08Z"
updated = "2026-10-23T01:12:11Z"
scope = ["crates/crunk-rules/**", "docs/reference/rules/**", "crates/crunk/tests/query_parity.rs", "crates/crunk/tests/parity/compare.rs", "crates/crunk-check/tests/color001.rs", "crates/crunk-check/tests/waive001.rs"]

[[acceptance]]
text = "Given a palette with no danger, warning or success role in [palette.roles], when crunk check runs, then CRAFT008 reports each missing semantic role"
bound = false

[[acceptance]]
text = "Given a palette declaring danger, warning and success roles, when crunk check runs, then CRAFT008 reports nothing"
bound = false
+++

found while working ~DTBY8Q0; cut from its scope
