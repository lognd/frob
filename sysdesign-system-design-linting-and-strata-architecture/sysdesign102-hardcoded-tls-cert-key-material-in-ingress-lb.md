+++
id = "01M3AXSDA1Q0TWAH25E9FRPGDP"
title = "SYSDESIGN102: hardcoded TLS cert/key material in ingress/LB config, no cert-manager/ACM annotation"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6465"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/sysdesign/_edge.py", "tests/fixtures/sysdesign/sysdesign102/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7TTVWH9XEP3NH163QX"

[[links]]
kind = "blocked-by"
target = "01M3AXSD8HXYDTWRT25J4YX5HQ"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN102: hardcoded TLS cert/key material in ingress/LB config, no cert-manager/
       ACM annotation
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_edge.py, docs/modules/gates.md (SYSDESIGN102 row),
       tests/fixtures/sysdesign/sysdesign102/**
blocked_by: [T-SYS-B-K8S, T-SYS-B-TERRAFORM]
tag: Static: config

Research row 1.2: "AWS Well-Architected Security Pillar, https://docs.aws.amazon.com/
wellarchitected/latest/security-pillar/welcome.html (fetched, intro-level page; pillar affirms
'protecting data in transit' as a security best-practice area)." Lint condition: "Hardcoded
certificate/key material in an ingress or load-balancer config (no cert-manager/ACM/managed
annotation) fails."

Note cross-reference (row 10.3 in the research): this row is distinct from TLS-in-transit
generally, which strata's `tls_terminates_at_provider` (cdn declassification, per
STRATA-EXPRESSIVENESS.md section D) already models for CDN edges -- this rule is the
config-layer check (ingress/LB YAML/HCL), not a strata design-model check, so it does not
duplicate that surface.

Acceptance criteria: flags a T-SYS-B-K8S Ingress or T-SYS-B-TERRAFORM `aws_lb_listener`/
`cloudflare_*` resource whose TLS block contains inline PEM-shaped certificate/key material
instead of a `cert-manager.io/cluster-issuer` annotation or ACM ARN reference. Positive-control
fixture: tests/fixtures/sysdesign/sysdesign102/ingress-inline-pem/**.
