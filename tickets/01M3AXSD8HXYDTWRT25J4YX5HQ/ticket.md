+++
id = "01M3AXSD8HXYDTWRT25J4YX5HQ"
title = "Terraform/HCL ingestion (security groups, LB, WAF, DNS records)"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6417"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/lang/_config_terraform.py (new)", "tests/fixtures/sysdesign/config-terraform/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: Terraform/HCL ingestion (security groups, LB, WAF, DNS records)
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 5
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_terraform.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-terraform/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

SYSDESIGN-INVENTORY.md sec 2: "Terraform/HCL: NOT PARSED as structured config. Only mention:
src/frob/webapp/_websec_debug_config.py:33 explicitly states its own scan is 'a regex scan, not
a full HCL/CFN parser' -- i.e. frob acknowledges it does NOT structurally parse HCL." This leaf
closes that gap for the resource kinds the edge/network rules in Story C need: security groups
(`aws_security_group`), load balancers (`aws_lb`/`aws_lb_target_group`), WAF (`aws_wafv2_*`,
`cloudflare_ruleset`), and DNS records (`aws_route53_record`/`cloudflare_record`).

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: `frob.lang._config_terraform.parse(path) -> list[ConfigDoc]` covers the
named resource kinds' block-level attributes (ingress/egress cidr_blocks, health_check blocks,
deregistration_delay, managed ruleset bindings, DNS record type/health-check reference). A
real HCL grammar is preferred; if budget does not allow a full parser in this leaf, the
implementer may ship a structural (not line-regex) block/attribute extractor scoped to exactly
these resource kinds and must document the narrowing in docs/modules/lang.md, matching the
honesty precedent set by _websec_debug_config.py's own self-admission. Positive-control
fixture: tests/fixtures/sysdesign/config-terraform/open-egress-sg/**.
