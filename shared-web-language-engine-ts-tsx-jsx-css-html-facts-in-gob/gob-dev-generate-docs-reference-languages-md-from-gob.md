+++
id = "01M48FXFZMWWZQ233HYSPZ6PP9"
title = "gob-dev: generate docs/reference/languages.md from gob_symbols::languages_page"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:53Z"
updated = "2026-10-06T11:34:53Z"
scope = ["crates/gob-dev/**"]
+++

~4M1BX5H added gob_symbols::languages_page and a test that keeps docs/reference/languages.md equal to it; gob-dev was leased by another ticket then. Add a Languages kind to cargo dev gen so the page is written and checked there, and let the Gap cells name a ticket (code-model.md section 3).
