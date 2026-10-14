+++
id = "01M4MAPRB2H8WZKJZSH3A9N1B2"
title = "GRL lowering: knobs, side-relation operands, is/in/exists/has attr, defs, count, reaches, snippets"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-11T01:54:42Z"
updated = "2026-10-14T05:19:31Z"
scope = ["crates/gob-plan/src/lower/**", "crates/gob-plan/src/plan/**", "crates/gob-plan/tests/**", "crates/gob-plan/src/exec/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7EKNE5Q0NB0DKCH77AZX"

[[acceptance]]
text = "Given the section 12 fixtures other than the snippet rules, when lowered, then each yields a validated plan and none is refused as Unsupported"
bound = false
+++

Follow-up of ~CH77AZX, which lowers the constructs the plan IR already has. The section 12 rules COV001, DOC002, INV002, NEAT013, NEAT031, SCOPE001, SYS001, TODO001 and NOPE001 are refused as Unsupported: knobs (regex and int operands), side-relation operands (lease.globs, config.lease.shared_files, 3-segment paths), is, in, exists, has attr, kind string arguments, def calls, count, reaches, in unit, under, snippets. Several need new plan ops, so the plan format and executor change with it.
