+++
id = "01M43ARY26XF7A4MSRAZ8V73JM"
title = "gob-symbols: CSS adapter with declarations, at-rules, custom properties and waivers"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-06T09:25:37Z"
idempotency_key = "crunk-plan-css"
labels = ["area:crunk", "creates:crates/gob-symbols/src/css/**", "creates:crates/gob-symbols/tests/css*.rs", "creates:changelog.d/*Z8V73JM*"]
scope = ["crates/gob-symbols/src/css/**", "crates/gob-symbols/tests/css*.rs", "docs/reference/fidelity.md", "crates/gob-symbols/src/typescript/style.rs", "crates/gob-symbols/src/typescript/fold/jsx.rs", "crates/gob-symbols/src/registry.rs", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/src/pipeline.rs", "changelog.d/*Z8V73JM*", "crates/gob-symbols/src/view.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARXDXMJ99H23MV17ZVW3R"

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[links]]
kind = "blocked-by"
target = "01M47QKDM2J0EKW2TYH4N35GSV"

[[acceptance]]
text = "Given a stylesheet with nested media queries, when indexed, then each declaration reports property, value text, selector and at-rule chain with spans"
bound = true

[[acceptance]]
text = "Given `color: var(--x)` and `--x: #fff`, when indexed, then the def and use are linked and an undefined var has no definition edge"
bound = true

[[acceptance]]
text = "Given a file with a syntax error, when indexed, then a PARSE diagnostic is emitted and other files are unaffected"
bound = true
+++

Replace tinycss2 (ingest/parse.py, jsx/_style.py, rules/_org.py, _layers.py) with a CSS adapter over the tree-sitter css grammar: Decl{property, value tokens, selector context, at-rule context}, custom-property definitions and var() uses, @media preludes, attached crunk:waive comments; unparseable CSS is a per-file PARSE diagnostic and the run continues. Blocked by tssym only for the shared gob-symbols registry edits (same files in registry.rs and lib.rs). OPEN DESIGN POINT: universal-model.md has no Decl or AtRule kind (lint-requirements R36 lists them); record in the ticket which U kinds carry declarations (key/literal in unit containers is the proposal) and get the owner decision before coding the mapping.
