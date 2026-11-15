+++
id = "01M5XM07CDFXTTENEEQ156HM4A"
title = "Add not_run to the gob.sibling/1 schema (crunk verbs test fails)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-27T02:46:01Z"
updated = "2026-11-15T08:53:51Z"
scope = ["docs/schemas/sibling.json", "crates/gob-product/**"]

[[acceptance]]
text = "crunk verbs check_json_with_a_valid_config_is_a_valid_sibling_document passes: the sibling schema accepts the not_run section"
bound = true
+++

crunk::verbs check_json_with_a_valid_config_is_a_valid_sibling_document fails on main: the check document now carries not_run (from 08R5Y3H) but docs/schemas/sibling.json does not allow it. Found while working NGXAEYS.
