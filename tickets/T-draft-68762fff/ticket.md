---
id: T-draft-68762fff
title: 'SYSDESIGN105: internet-facing listener with no managed WAF ruleset bound'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-4a00f41a
parent: T-draft-56ac0a37
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
- src/frob/sysdesign/_waf.py (new)
- tests/fixtures/sysdesign/sysdesign105/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN105: internet-facing listener with no managed WAF ruleset bound
kind: feature
tier: leaf
parent: T-SYS-SC
milestone: 0.539.0
sprint: sysdesign
points: 2
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_waf.py (new), docs/modules/gates.md (SYSDESIGN105 row),
       tests/fixtures/sysdesign/sysdesign105/**
blocked_by: [T-SYS-B-TERRAFORM]
tag: Static: config

Research row 3.1: Cloudflare WAF managed rules docs, https://developers.cloudflare.com/waf/
managed-rules/ -- "Cloudflare provides pre-configured managed rulesets that protect against web
application exploits such as the following: Zero-day vulnerabilities... Cloudflare OWASP Core
Ruleset: Cloudflare's implementation of the Open Web Application Security Project (OWASP)
ModSecurity Core Rule Set." Lint condition: "Internet-facing listener/app with no managed WAF
ruleset bound flags."

Acceptance criteria: flags a T-SYS-B-TERRAFORM internet-facing listener (`aws_lb_listener` on a
public-subnet ALB, or `cloudflare_ruleset` absent for a proxied zone) with no
`ManagedRuleGroupStatement`/`cloudflare_ruleset`/Azure WAF policy binding. Positive-control
fixture: tests/fixtures/sysdesign/sysdesign105/public-alb-no-waf/**.
