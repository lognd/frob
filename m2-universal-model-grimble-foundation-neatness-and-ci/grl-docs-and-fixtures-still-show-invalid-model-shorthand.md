+++
id = "01M5GAT99HX9VW1S0MEFKKYQ41"
title = "GRL docs and fixtures still show invalid model shorthand (node app owns, may because=)"
type = "docs"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T22:55:22Z"
updated = "2026-10-26T04:18:52Z"
scope = ["docs/design/grl-spec.md", "crates/gob-plan/src/grl/**"]

[[acceptance]]
text = 'grl-spec.md and the CAP001 and SYS001 fixtures use only the model syntax grmb parses (node app { owns ".."; } and excuses ATOM because="..")'
bound = false

[[acceptance]]
text = "the CAP001 hint text no longer mentions because"
bound = false
+++

Found while working ~WHEVEHY. docs/design/grl-spec.md and crates/gob-plan/src/grl/parse/tests/fixtures/{CAP001,SYS001}.grl show 'node app owns ".."' and 'may ... because=', which grmb does not parse; use 'node app { owns ".."; }' and 'excuses ATOM because=".."'. CAP001.grl hint text mentions because. Also: examples/cells.rs names_callee duplicates grimble-bind; scoped (may ... at) grants are ignored.
