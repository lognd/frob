+++
id = "01M5XM07CDFXTTENEEQ156HM4A"
title = "Add not_run to the gob.sibling/1 schema (crunk verbs test fails)"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-27T02:46:01Z"
updated = "2026-10-27T02:46:01Z"
scope = ["docs/schemas/sibling.json", "crates/gob-product/**"]
+++

crunk::verbs check_json_with_a_valid_config_is_a_valid_sibling_document fails on main: the check document now carries not_run (from 08R5Y3H) but docs/schemas/sibling.json does not allow it. Found while working NGXAEYS.
