+++
id = "01M47YJF46HM8MA5PVWNH92W1H"
title = "GRL printer: print a GRL syntax tree back to canonical text"
type = "story"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T06:31:45Z"
updated = "2026-10-06T14:42:16Z"
scope = ["crates/gob-plan/**"]
+++

found while working ~2JVWF8Y: gob-plan has a GRL lexer and parser but no printer or formatter. build-test-ci.md section 6 (D98) wants parse(print(t)) = t and print(print(t)) = print(t) over every GRL fixture plus a proptest generator with a shrinking self-test; that needs the printer first. Reuse the stability harness in crates/grimble-model/tests/stability.rs as the model.
