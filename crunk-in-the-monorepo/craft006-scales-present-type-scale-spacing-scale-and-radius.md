+++
id = "01M5HM3VTW5FAZQ3TXM8XH739S"
title = "CRAFT006 scales present: type scale, spacing scale and radius policy presence paired with SLOP022 and TYPE rules"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXT3N608HMB1A77VTT4YXX"
reporter = "lognd"
created = "2026-10-22T10:57:07Z"
updated = "2026-10-23T00:57:30Z"
scope = ["crates/crunk-rules/**", "docs/reference/rules/**", "crates/crunk/tests/query_parity.rs", "crates/crunk/tests/parity/compare.rs", "tests/crunk-parity/divergences.toml", "docs/crunk/rules/**"]

[[acceptance]]
text = "Given a crunk project with no type scale, spacing scale or radius policy declared, when crunk check runs, then CRAFT006 reports each missing scale and names the paired SLOP022 or TYPE rule"
bound = true

[[acceptance]]
text = "Given a project declaring all three scales, when crunk check runs, then CRAFT006 reports nothing"
bound = true
+++

found while working ~DTBY8Q0; cut from its scope
