+++
id = "01M43ARY26XF7A4MSRAZ8V73JM"
title = "gob-symbols: CSS adapter with declarations, at-rules, custom properties and waivers"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-04T11:28:48Z"
idempotency_key = "crunk-plan-css"
labels = ["area:crunk"]
scope = ["crates/gob-symbols/src/css/**", "crates/gob-symbols/tests/css*.rs", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARXDXMJ99H23MV17ZVW3R"

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[acceptance]]
text = "Given a stylesheet with nested media queries, when indexed, then each declaration reports property, value text, selector and at-rule chain with spans"
bound = false

[[acceptance]]
text = "Given `color: var(--x)` and `--x: #fff`, when indexed, then the def and use are linked and an undefined var has no definition edge"
bound = false

[[acceptance]]
text = "Given a file with a syntax error, when indexed, then a PARSE diagnostic is emitted and other files are unaffected"
bound = false
+++

Replace tinycss2 (ingest/parse.py, jsx/_style.py, rules/_org.py, _layers.py) with a CSS adapter over the tree-sitter css grammar: Decl{property, value tokens, selector context, at-rule context}, custom-property definitions and var() uses, @media preludes, attached crunk:waive comments; unparseable CSS is a per-file PARSE diagnostic and the run continues. Blocked by tssym only for the shared gob-symbols registry edits (same files in registry.rs and lib.rs). OPEN DESIGN POINT: universal-model.md has no Decl or AtRule kind (lint-requirements R36 lists them); record in the ticket which U kinds carry declarations (key/literal in unit containers is the proposal) and get the owner decision before coding the mapping.
