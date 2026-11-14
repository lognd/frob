+++
id = "01M7CMHQGHM5X32TWG3D5WB4PT"
title = "gob-symbols field-write graph for UNITY004 and Serializable nested-class public fields"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-14T08:59:53Z"
updated = "2026-11-14T09:51:36Z"
labels = ['["no-story"]']
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**"]
+++

Follow-up of ~47WNTP3: UNITY004 uses the lexical name-based never_written_fields scan. Build a real field-write graph in gob-symbols and handle public fields of [Serializable] nested classes.
