+++
id = "01M3AXSDAES8ZSK907ZEN6Q5YS"
title = "SYSDESIGN101: declared tier-1 availability with no health-checked/multi-provider DNS failover"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6478"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_edge.py (new)", "tests/fixtures/sysdesign/sysdesign101/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8HXYDTWRT25J4YX5HQ"

[[links]]
kind = "blocked-by"
target = "01M3AXSDAJ8YB45QEY8G9Z8DWV"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN101: declared tier-1 availability with no health-checked/multi-provider
       DNS failover
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_edge.py (new), docs/modules/gates.md (SYSDESIGN101 row),
       tests/fixtures/sysdesign/sysdesign101/**
blocked_by: [T-SYS-B-TERRAFORM, T-SYS-H-RESEARCH-GAPS]
tag: Static: design

Research row 1.1 (citation flagged weak in-row): "Cloudflare DDoS Protection,
https://developers.cloudflare.com/ddos-protection/ (fetched; general DDoS mitigation posture
doc, no single-line quote on DNS failover found in this pass -- see 1.1 note)." The research
file's own note: "DNS multi-provider failover... [was] not found with a directly quotable
primary-source line in this pass... The lint conditions above are still filed but their
authority citation is weaker than the others in this section -- flagged, not invented." Filed
blocked_by T-SYS-H-RESEARCH-GAPS so the rule does not ship until this citation is strengthened
or the owner explicitly accepts it as-is.

Lint condition (row 1.1): "If a service is declared 'tier-1 availability' in the design model
but DNS has a single A/AAAA record with no health check and no secondary provider, flag."

Acceptance criteria: reads a design-model `attr availability=tier-1` (or equivalent, cf.
node-level `owner`/attr conventions) node cross-referenced against T-SYS-B-TERRAFORM's parsed
`aws_route53_record`/`cloudflare_record` set for the same hostname; flags when no health-check
reference and no secondary/failover record exists. Positive-control fixture: tests/fixtures/
sysdesign/sysdesign101/tier1-single-a-record/**.
