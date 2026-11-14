+++
id = "01M5FRZGDQ88QYMF8R547WNTP3"
title = "never-written field rule consuming frob_obligations::never_written_fields"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M44YQS4CNZM54P067GJVPDC0"
reporter = "lognd"
created = "2026-10-21T17:43:39Z"
updated = "2026-11-14T08:37:25Z"
labels = ["no-story"]
scope = ["crates/frob-obligations/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a C# field no code assigns and the unity pack enabled, when frob check runs, then UNITY004 reports it; an assigned field is clean"
bound = false
+++

found while working ~9QK3N9A: no rule reports never-assigned fields and the C# symbol graph has no field-write edges. never_written_fields is a lexical, name-based list with no consumer; add a rule (id, doc) and a real field-write graph, and consider [Serializable] nested-class public fields.

no-story: internal engineering task in frob-obligations; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
