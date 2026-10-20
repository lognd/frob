+++
id = "01M3AXSD7NVG8KPGNRJ3SPHA5N"
title = "dropped: MongoDB schema-less drift (inconsistent field types/names across documents)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6389"]
labels = ["milestone:0.538.0"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Document anti-pattern #6. Static tier: "dynamic-only
(requires cross-file type-consistency inference across all writers of a
collection)" -- proving drift requires knowing every writer's actual
field types/names across the whole codebase and reconciling them
against real document shapes, which is a data-shape inference problem,
not a call-shape or repo-fact one.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
