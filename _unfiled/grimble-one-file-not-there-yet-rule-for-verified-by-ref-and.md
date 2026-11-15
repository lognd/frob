+++
id = "01M7EXV0XPHS7T0P2N7DB4NZH3"
title = "grimble: one 'file not there yet' rule for verified_by, ref and shape (SPEC 8.3)"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:44Z"
updated = "2026-11-15T06:20:44Z"
labels = ["no-story"]

[[acceptance]]
text = "All four constructs handle a missing file by one documented rule"
bound = false

[[acceptance]]
text = "SPEC 8.3 states the rule and a test per construct passes"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md M5. Evidence: verified_by on a scenario is planned, on a claim MDL005; vmodel ref to a missing file silent; contract shape to a missing file MDL005. Remedy: one rule per SPEC 8.3 line 1318 and decide ref and shape. Crates: grimble-model, grimble-check.
