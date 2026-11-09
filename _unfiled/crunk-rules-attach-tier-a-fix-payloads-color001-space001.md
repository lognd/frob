+++
id = "01M54H34N0CPKAZ7TP91EYXGVV"
title = "crunk rules: attach Tier A Fix payloads (COLOR001, SPACE001, TYPE001, RADIUS001, SIZE001), tolerance-gated"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-17T08:54:10Z"
updated = "2026-11-09T03:24:01Z"
persona = "a crunk user"
capability = "apply Tier A fixes for color, space and type findings"
outcome_text = "crunk can repair simple findings automatically"
labels = ["area:crunk"]
scope = ["crates/crunk-rules/**", "crates/gob-rules/src/decl.rs", "crates/gob-rules/tests/located.rs", "docs/reference/rules/**"]

[[links]]
kind = "blocked-by"
target = "01M43ATCQVX9A1TJ6A4AE48FDX"

[[acceptance]]
text = "Given an in-tolerance off-scale value, when `crunk fix` runs, then it is rewritten to the token and a re-check of the site is clean"
bound = true

[[acceptance]]
text = "Given a value outside tolerance, when fix runs, then the finding carries no fix and remains"
bound = true

[[acceptance]]
text = "Given a translucent color in tolerance, when fix runs, then it is rewritten as color-mix(...)"
bound = true
+++

Split from ~AE48FDX: the crunk fix engine (crates/crunk-fix, `crunk fix [--dry-run]`) is landed, but the rules still declare fix = Manual and attach no Fix. Attach Deterministic/Machine Fix payloads gated by fix_tolerance and color_tolerance; translucent colors rewrite as color-mix(...); add INV-FIX-02 (re-check of a fixed site is clean) property test; port tests/unit/test_fixes.py, INT-05, e2e 03.
