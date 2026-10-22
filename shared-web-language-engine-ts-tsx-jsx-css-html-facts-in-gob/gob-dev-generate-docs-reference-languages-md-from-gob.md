+++
id = "01M48FXFZMWWZQ233HYSPZ6PP9"
title = "gob-dev: generate docs/reference/languages.md from gob_symbols::languages_page"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:34:53Z"
updated = "2026-10-22T01:45:23Z"
scope = ["crates/gob-dev/**", "docs/reference/languages.md", "changelog.d/01M48FXFZMWWZQ233HYSPZ6PP9.added.md", "Cargo.lock", "crates/gob-symbols/src/languages_page.rs", "crates/gob-symbols/tests/it/web_corpus.rs"]

[[acceptance]]
text = "gob-dev gen emits docs/reference/languages.md from gob_symbols::languages_page and --check detects drift"
bound = true

[[acceptance]]
text = "gob-dev gen languages writes the page exactly as gob_symbols::languages_page renders it"
bound = true

[[acceptance]]
text = "gen --check reports drift or a missing languages page without writing"
bound = true

[[acceptance]]
text = "regenerating the languages page twice is idempotent and an already-equal page is not rewritten"
bound = true

[[acceptance]]
text = "the languages page carries a GEN001-valid marker naming cargo dev gen languages"
bound = true
+++

~4M1BX5H added gob_symbols::languages_page and a test that keeps docs/reference/languages.md equal to it; gob-dev was leased by another ticket then. Add a Languages kind to cargo dev gen so the page is written and checked there, and let the Gap cells name a ticket (code-model.md section 3).
