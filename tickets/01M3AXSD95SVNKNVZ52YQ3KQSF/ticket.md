+++
id = "01M3AXSD95SVNKNVZ52YQ3KQSF"
title = "SYSDESIGN105: internet-facing listener with no managed WAF ruleset bound"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8RPMPFSYCWPM0XQY5G"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6437"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/sysdesign/_waf.py (new)", "tests/fixtures/sysdesign/sysdesign105/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8HXYDTWRT25J4YX5HQ"
+++

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
