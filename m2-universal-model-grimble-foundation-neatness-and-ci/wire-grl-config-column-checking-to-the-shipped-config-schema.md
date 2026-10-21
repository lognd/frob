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
updated = "2026-10-21T21:34:38Z"
scope = ["crates/grimble/**", "crates/gob-plan/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4DGHT8H530QHR7VJPHFBHDJ"

[[links]]
kind = "blocked-by"
target = "01M4M5CQ9529KH526299QXXFVF"

[[acceptance]]
text = "Given a GRL rule with a misspelt config column (f.frm on config.invariants.forbid_imports), when compiled by the shipped binary, then GRL001 names the column"
bound = false
+++

Follow-up of ~41PCRHB. Needs the GRL compile verb and the config schema $defs from ~PHFBHDJ. Load docs/schemas/config.json (ConfigSchema::from_json) and pass it to check_file_with / a compile_report variant.
