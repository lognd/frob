+++
id = "01M7DKEF5H542R72Z6VGQF7ZAJ"
title = "gob-macros: rule id validator rejects digits in family (blocks I18N001/I18N002)"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T17:59:52Z"
updated = "2026-11-14T18:00:07Z"
scope = ["crates/gob-macros/**"]
+++

found while working ~4RY4M26: #[rule] valid_id (crates/gob-macros/src/lib.rs:95 and rule_attr.rs:550) requires an all-uppercase-letter family, but crunk family I18N (family.rs) contains a digit, so I18N001/I18N002 fail to compile. Allow ASCII digits after the first letter in the family prefix, and update the error text.
