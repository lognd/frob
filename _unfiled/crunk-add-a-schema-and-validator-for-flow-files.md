+++
id = "01M5JHRGCES4BCHCNBCB7WWZ9F"
title = "crunk: add a schema and validator for flow files"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T19:35:13Z"
updated = "2026-10-22T20:17:04Z"
scope = ["crates/crunk-spec/**", "crates/crunk/src/new.rs", "crates/crunk/tests/new.rs", "docs/crunk/README.md"]

[[acceptance]]
text = "Given a valid flow file, when validated by crunk-spec, then it passes"
bound = false

[[acceptance]]
text = "Given a flow file with a missing or unknown key or a dangling step reference, when validated, then a coded error names the location"
bound = false

[[acceptance]]
text = "Given crunk new flow, when it writes a flow file, then the output passes the validator"
bound = false
+++

found while working 76STB57: crunk new flow can only validate TOML syntax
