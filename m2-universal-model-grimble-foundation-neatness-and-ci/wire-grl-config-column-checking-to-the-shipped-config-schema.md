+++
id = "01M4M5CRRV5A6P5WHHVHXP981B"
title = "Wire GRL config column checking to the shipped config schema"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-11T00:21:52Z"
updated = "2026-10-21T22:08:23Z"
scope = ["crates/grimble/**", "crates/gob-plan/**", "changelog.d/**", "docs/design/cli.md", "docs/schemas/config.json", "changelog.d/01M4M5CRRV5A6P5WHHVHXP981B.added.md"]

[[links]]
kind = "blocked-by"
target = "01M4DGHT8H530QHR7VJPHFBHDJ"

[[links]]
kind = "blocked-by"
target = "01M4M5CQ9529KH526299QXXFVF"

[[acceptance]]
text = "Given a GRL rule with a misspelt config column (f.frm on config.invariants.forbid_imports), when compiled by the shipped binary, then GRL001 names the column"
bound = true

[[acceptance]]
text = "Given a GRL rule using a real config column or a misspelt config table, when compiled by the shipped binary, then the real column passes and the table is reported as an unknown config key"
bound = true

[[acceptance]]
text = "Given a malformed or empty config schema document, when the binary loads it, then config checking is turned off with a warning instead of failing"
bound = false

[[acceptance]]
text = "Given the real docs/schemas/config.json, when gob-plan compiles with it, then ForbidImport columns are typed and a misspelt column is reported only when the schema is supplied"
bound = false
+++

Follow-up of ~41PCRHB. Needs the GRL compile verb and the config schema $defs from ~PHFBHDJ. Load docs/schemas/config.json (ConfigSchema::from_json) and pass it to check_file_with / a compile_report variant.
