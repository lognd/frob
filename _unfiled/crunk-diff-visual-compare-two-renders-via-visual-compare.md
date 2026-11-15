+++
id = "01M7EXRE771TGW9DC4HHP35SPH"
title = "crunk diff --visual: compare two renders via visual::compare"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK794J40RVB9YAWNQ6NF3"
reporter = "lognd"
created = "2026-11-15T06:19:19Z"
updated = "2026-11-15T06:19:20Z"
idempotency_key = "crunkplan-b20f8b772261"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXRDAGY3M6ZGQQWR8M2ET6"

[[acceptance]]
text = "crunk diff --visual A B prints a pixel-difference verdict and exits non-zero above threshold"
bound = false

[[acceptance]]
text = "missing input image yields a typed error, not a panic"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H1.
Evidence: visual::compare exists with no verb exposing it
Remedy: add crunk diff --visual A B over visual::compare; overlaps ~CFF3C0J (VIS001 wiring), coordinate scope
Crates/files: crates/crunk/src, crates/crunk-check visual module
Verify against HEAD first; the audit ran on a stale binary.
