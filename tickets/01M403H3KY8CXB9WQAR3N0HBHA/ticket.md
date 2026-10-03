+++
id = "01M403H3KY8CXB9WQAR3N0HBHA"
title = "Add gob-plan to the boundaries.md crate table and the lexer additions to grl-spec 3"
type = "docs"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:24:28Z"
updated = "2026-10-03T10:50:41Z"
idempotency_key = "m2-boundaries-gob-plan"
labels = ["milestone:2", "area:grl", "good-first"]
scope = ["docs/design/boundaries.md", "docs/design/grl-spec.md"]

[[acceptance]]
text = "Given boundaries.md and grl-spec.md 3, when read, then gob-plan is listed and the lexer additions are specified"
bound = false
+++

Follow-up of ~DP3BZJZ. ## Start here
Read docs/design/boundaries.md (the crate table: name, owns, used by) and crates/gob-plan/README.md. Add a gob-plan row (owns: GRL lexer, parser, catalog checks, plan format, executor, codegen; used by frob, grimble, crunk). In docs/design/grl-spec.md section 3, add the string escapes \{ and \}, note that regex literals are ASCII-only with \uXXXX escapes and cannot span lines, and that list<T>= needs a space before the equals sign. Test: frob check --ticket passes (SYNC is not built yet; read the diff once against the crate's README). Ask the coordinator if unsure.
