+++
id = "01M3AXSD7PNT7RJ8TTNEZC1FTE"
title = "SYSDESIGN202: autoscaled service with no local admission-control/load-shedding check"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSDAZX9B4327J18H8GE7S"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6390"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_admission.py (new)", "tests/fixtures/sysdesign/sysdesign202/**"]
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN202: autoscaled service with no local admission-control/load-shedding check
kind: feature
tier: leaf
parent: T-SYS-SD
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_admission.py (new), docs/modules/gates.md (SYSDESIGN202 row),
       tests/fixtures/sysdesign/sysdesign202/**
blocked_by: []
tag: Static: code

Research row 6.10: Google SRE Book, "Handling Overload", https://sre.google/sre-book/
handling-overload/ -- "As utilization approaches configured thresholds, we start rejecting
requests based on their criticality (higher thresholds for higher criticalities)." Lint
condition: "A service with autoscaling but no local admission-control/load-shedding check
(accepts every request regardless of local utilization) flags."

Cross-reference row 9.3 (observability pairing, filed here as the same rule's second
requirement, not a separate id, per NO DUPLICATION): "A service with load-shedding logic (6.10)
whose utilization signal is not exported as a metric flags (the control exists but is
unobservable)."

Acceptance criteria: code-level detection of a utilization-based admission check (CPU/queue-
depth threshold consulted before accepting work) on a service declared `capacity replicas
2..N` (autoscaling-shaped); flags its absence, and separately flags presence-with-no-exported-
metric (the 9.3 pairing) as a second finding in the same module. Positive-control fixture:
tests/fixtures/sysdesign/sysdesign202/autoscaled-no-admission-check/**.
