+++
id = "01M4HT2BSXCN48AG9Z18GC1GYM"
title = "CI frob check step skips stages already run as dedicated steps"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-10T02:25:28Z"
updated = "2026-10-10T02:25:28Z"
scope = ["crates/gob-dev/src/ci.rs"]

[[acceptance]]
text = "Given a CI run, when the check step runs, then no tool stage already run as a dedicated step runs again"
bound = false
+++

found while working ~BN7DCP3: audit M18, the check step re-runs fmt, clippy, gen, zizmor, actionlint, deny, shear and typos (about 135 s). Needs a stage-skip flag or ci_dedicated tag in frob-check, then the check step passes it. Also move cargo-deny, shear, insta, typos installs to a prebuilt installer.
