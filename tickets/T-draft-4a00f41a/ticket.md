---
id: T-draft-4a00f41a
title: Terraform/HCL ingestion (security groups, LB, WAF, DNS records)
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-1f5f5b2d
parent: T-draft-579d39b7
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/lang/_config_terraform.py (new)
- tests/fixtures/sysdesign/config-terraform/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 1829
  new_length: 1918
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
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
