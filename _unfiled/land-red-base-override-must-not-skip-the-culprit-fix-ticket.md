+++
id = "01M7AV6DA56YMV88HFEMM9Z56N"
title = "land: red-base override must not skip the culprit fix-ticket filing"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-13T16:17:34Z"
updated = "2026-11-13T21:20:37Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "An overridden land still files the culprit ticket; test proves it."
bound = true
+++

H1: --override-base-ci used 685 times and also disables the auto-filed fix ticket. Source: frob-audit-meta.md (Opus audit).
