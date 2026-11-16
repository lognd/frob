+++
id = "01M66JFKH9C5P32RFS1WPV35JV"
title = "Make frob-check and gob-check findings audience-aware and stamp nature"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T14:12:38Z"
updated = "2026-11-16T10:45:25Z"
labels = ["no-story", "good-first"]
scope = ["crates/frob-check/**, crates/gob-check/**"]

[[acceptance]]
text = "Given a check run with a detected audience, when frob-check verb.rs and gob-check sibling.rs build records, then they use FindingRecord::from_finding_for and the engine stamps Finding.nature and note from RuleDef.nature"
bound = false
+++

found while working 01M63B7F02SKSJCQG7TMXQ4HW5: only gob-cli success rendering is audience-aware; the check engines still call from_finding and never set Finding.nature from RuleDef.

## Start here
Read crates/frob-check/src/verb.rs and crates/gob-check/src/sibling.rs where from_finding is called; switch to FindingRecord::from_finding_for.
no-story: internal engineering task in frob-check and gob-check; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
