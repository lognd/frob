+++
id = "01M3AXSD8MNYVG0SPHPBAJ16FR"
title = "SYSDESIGN104: LB deregistration_delay unset while workload terminationGracePeriodSeconds is shorter"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6420"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_lb.py", "tests/fixtures/sysdesign/sysdesign104/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"

[[links]]
kind = "blocked-by"
target = "01M3AXSD8HXYDTWRT25J4YX5HQ"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN104: LB deregistration_delay unset while workload terminationGracePeriodSeconds
       is shorter, a request-drop race
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_lb.py, docs/modules/gates.md (SYSDESIGN104 row),
       tests/fixtures/sysdesign/sysdesign104/**
blocked_by: [T-SYS-B-K8S, T-SYS-B-TERRAFORM]
tag: Static: config

Research row 2.5 (citation partial -- AWS pillar fetched at intro level only, sub-page 404'd):
evidence artifact "ALB/NLB target-group `deregistration_delay.timeout_seconds`, or k8s
`terminationGracePeriodSeconds` combined with readiness-gate removal." Lint condition: "Target
group / Service with `deregistration_delay` unset (defaulting) while
`terminationGracePeriodSeconds` on the workload is shorter than the LB drain window flags a
request-drop race."

Acceptance criteria: cross-references T-SYS-B-TERRAFORM's `aws_lb_target_group.
deregistration_delay` against T-SYS-B-K8S's matching Deployment's
`spec.template.spec.terminationGracePeriodSeconds`; flags when the grace period is shorter than
the drain window (or the drain window is unset/defaulting). Positive-control fixture:
tests/fixtures/sysdesign/sysdesign104/short-grace-period/**.
