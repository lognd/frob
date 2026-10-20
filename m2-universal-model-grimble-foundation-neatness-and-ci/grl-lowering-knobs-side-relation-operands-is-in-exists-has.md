+++
id = "01M4MAPRB2H8WZKJZSH3A9N1B2"
title = "GRL lowering: knobs, side-relation operands, is/in/exists/has attr, defs, count, reaches, snippets"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-11T01:54:42Z"
updated = "2026-10-14T12:36:23Z"
scope = ["crates/gob-plan/src/lower/**", "crates/gob-plan/src/plan/**", "crates/gob-plan/tests/**", "crates/gob-plan/src/exec/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[acceptance]]
text = "Given the SCOPE001 and SYS001 side-relation glob-set rules, when lowered, then each yields a validated plan via MatchGlobSet; remaining section 12 fixtures are tracked by child tickets C6W2KWJ, 26X4K6K, 8Q9444T, NVMH9MV, HZ73YP7"
bound = true
+++

Follow-up of ~CH77AZX, which lowers the constructs the plan IR already has. The section 12 rules COV001, DOC002, INV002, NEAT013, NEAT031, SCOPE001, SYS001, TODO001 and NOPE001 are refused as Unsupported: knobs (regex and int operands), side-relation operands (lease.globs, config.lease.shared_files, 3-segment paths), is, in, exists, has attr, kind string arguments, def calls, count, reaches, in unit, under, snippets. Several need new plan ops, so the plan format and executor change with it.
