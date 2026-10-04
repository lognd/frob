+++
id = "01M3AXSD8W3FK6RAWZ8QA6KJA1"
title = "dropped: single `WITH RECURSIVE` / graph-traversal-by-CTE call with runtime-unbounded depth parameter"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
parent = "01M3AXSD9Z2T54HFHNCZ91W3YV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:02Z"
aliases = ["T-6428"]
labels = ["milestone:0.538.0"]
+++

Research file, Relational anti-pattern #7 / Graph anti-pattern #5.
Static tier: "dynamic-only (need to see it's called in a loop / with
unbounded depth param)" -- a SINGLE call site with a depth parameter
whose bound is a runtime value cannot be distinguished from a safely
bounded call without knowing what value flows into that parameter at
runtime. Distinct from STORE121 (the CALL-IN-A-LOOP shape, which IS
static and IS filed) -- this dropped ticket is specifically the
single-call, data-dependent-depth case.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule
