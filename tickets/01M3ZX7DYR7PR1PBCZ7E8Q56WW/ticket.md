+++
id = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"
title = "GRL name and type checks: GRL001, GRL003, GRL004, GRL005, GRL013"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-08T09:56:19Z"
idempotency_key = "m2-grl-check-names"
labels = ["milestone:2", "area:grl", "creates:crates/gob-plan/src/check/render.rs", "creates:crates/gob-plan/src/check/vocab.rs", "creates:crates/gob-plan/tests/check_names.rs", "creates:crates/gob-plan/tests/grl_errors/cases/GRL017.*", "creates:crates/gob-plan/tests/grl_errors/cases/GRL018.*", "creates:changelog.d/01M3ZX7DYR7PR1PBCZ7E8Q56WW.added.md"]
scope = ["crates/gob-plan/src/check/names.rs", "crates/gob-plan/src/check/mod.rs", "crates/gob-plan/src/lib.rs", "crates/gob-plan/tests/grl_errors/main.rs", "crates/gob-plan/src/check/render.rs", "crates/gob-plan/src/check/vocab.rs", "crates/gob-plan/tests/check_names.rs", "crates/gob-plan/tests/grl_errors/cases/GRL017.*", "crates/gob-plan/tests/grl_errors/cases/GRL018.*", "changelog.d/01M3ZX7DYR7PR1PBCZ7E8Q56WW.added.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7D9CT156TR8J4YTQ622S"

[[links]]
kind = "blocked-by"
target = "01M3ZX7DCQGFR0761QHY8NPAQE"

[[acceptance]]
text = "Given `where not d inside tset`, when compiled, then GRL001 points at `tset` with help `did you mean test` and the catalog command, byte-equal to its golden"
bound = true

[[acceptance]]
text = "Given a variable bound twice, used only inside `no`, compared across types, or bound and never used, when compiled, then GRL004, GRL003, GRL005 and warning GRL013 are emitted with their goldens"
bound = true
+++

Implements grl-spec.md sections 7.1 and 10.

Every name is checked at compile time against the catalog with did-you-mean; binding rules for find/some/no; type mismatches. A typo is a compile error, never a silent no-match.
