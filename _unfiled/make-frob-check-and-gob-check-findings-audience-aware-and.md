+++
id = "01M66JFKH9C5P32RFS1WPV35JV"
title = "Make frob-check and gob-check findings audience-aware and stamp nature"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T14:12:38Z"
updated = "2026-10-30T14:12:38Z"
scope = ["crates/frob-check/**, crates/gob-check/**"]

[[acceptance]]
text = "frob-check verb.rs and gob-check sibling.rs use FindingRecord::from_finding_for with the detected audience; the engine stamps Finding.nature and note from RuleDef.nature"
bound = false
+++

found while working 01M63B7F02SKSJCQG7TMXQ4HW5: only gob-cli success rendering is audience-aware; the check engines still call from_finding and never set Finding.nature from RuleDef.
