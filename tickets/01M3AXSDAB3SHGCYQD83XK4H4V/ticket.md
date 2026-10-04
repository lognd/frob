+++
id = "01M3AXSDAB3SHGCYQD83XK4H4V"
title = "SYSDESIGN302: outbound retry logic with a per-call max-attempts but no aggregate process-wide retry budget"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSDASH31CMNHAQ9JXR1YQ"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6475"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/strata/_retry_budget.py (new)", "tests/fixtures/sysdesign/sysdesign302/**"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN302: outbound retry logic with a per-call max-attempts but no aggregate,
       process-wide retry budget
kind: feature
tier: leaf
parent: T-SYS-SE
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_retry_budget.py (new), docs/modules/gates.md (SYSDESIGN302 row),
       tests/fixtures/sysdesign/sysdesign302/**
blocked_by: []
tag: Static: code

Research rows 2.7/5.10: Google SRE Book, "Addressing Cascading Failures", https://sre.google/
sre-book/addressing-cascading-failures/ -- "Consider having a server-wide retry budget. For
example, only allow 60 retries per minute in a process, and if the retry budget is exceeded,
don't retry; just fail the request. This strategy can contain the retry effect and be the
difference between a capacity planning failure that leads to some dropped queries and a global
cascading failure." Lint condition: "Outbound client retry logic with a per-call max-attempts
but no aggregate/process-wide retry budget flags."

Distinct from REL220 (per-flow `backoff_jitter` attr, existing): REL220 governs one flow's
retry shape (does it back off with jitter); this rule governs the process-wide AGGREGATE budget
across all retrying flows, which REL220/221 does not model at all.

Acceptance criteria: flags a process/service (per bound-code scan, same discipline as REL222's
"real backoff-shaped token" check) with 2+ REL220-marked retrying flows and no shared/aggregate
retry-budget primitive (percentage-based or fixed-rate cap) referenced across them. Positive-
control fixture: tests/fixtures/sysdesign/sysdesign302/per-flow-retry-no-budget/**.
