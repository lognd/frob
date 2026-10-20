+++
id = "01M492EQCRNEW2YFYESHABQ4YY"
title = "rule_attr compile errors still name the stub caps.rs path"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-06T16:58:52Z"
updated = "2026-10-06T16:58:52Z"
scope = ["crates/gob-macros/**"]
+++

found while working ~HQ6B02X: rule_attr.rs messages and the trybuild stderr files say 'matrix: crates/gob-rules/src/rule_spike/caps.rs (stub for gob-caps)'. gob-caps now exists; point them at crates/gob-caps/src/matrix.rs and regenerate the stderr snapshots.
