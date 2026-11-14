+++
id = "01M7CMHQGHM5X32TWG3D5WB4PT"
title = "gob-symbols field-write graph for UNITY004 and Serializable nested-class public fields"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-14T08:59:53Z"
updated = "2026-11-14T11:12:44Z"
labels = ['["no-story"]']
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**", "docs/reference/rules/UNITY004.md"]

[[acceptance]]
text = "Public fields of a [Serializable] class nested in an engine type are not reported by UNITY004, and writes are kept in a gob-symbols FieldWrites graph"
bound = true
+++

Follow-up of ~47WNTP3: UNITY004 uses the lexical name-based never_written_fields scan. Build a real field-write graph in gob-symbols and handle public fields of [Serializable] nested classes. no-story: internal rule-engine refinement with no user-visible story.
