---
id: T-draft-09897a86
title: 'Web application lint families: appsec, compliance, accessibility, SEO and
  web performance, SQL -- every rule cites its external authority'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: epic
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
attachments:
- path: T-draft-09897a86/attachments/01-untitled.md
  caption: ''
  sha256: b8903ddcde3588694a71cf36ea223f032b3dbda0e25689e36b775be1086dda8c
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-20: frob MUST lint the owner's web-launch list exhaustively, and every rule with an external authority (statute, regulation, Google spam policy, WCAG, OWASP ASVS, vendor docs) cites the operative section in its reason text. Research corpus attached to the child stories: nine files, 283 entries, 109 distinct ASVS 5.0 requirement ids, 42 WCAG 2.2 criteria, each entry tagged Static: yes | config | dynamic-only. Dynamic-only entries become test obligations (frob:tests) not static rules. Convention-only items (team photo, case studies, FAQ count, thank-you page, sticky mobile CTA, response-time promise, analytics) ship as an advisory LAUNCH checklist family, never as errors. Rule families to add: WEBSEC (appsec, four stories), COMPLY (compliance pages and config), A11Y, SEO, WEBPERF, SQL, LAUNCH. Each family: policy entries in frob.toml where the DSL suffices, tree-sitter queries for HTML/JSX/TSX/Vue/Jinja/Django template sinks, a positive-control fixture per rule that plants the finding, a docs/modules/gates.md row generated from the registry, and the tool-registry entry when an adapter is needed (sqlfluff, squawk, lighthouse, axe-core, pa11y). All families respect T-draft-94870246: a missing relevant adapter is UNMEASURED and loud. Framework detection (Next, Vite, Django, Flask, FastAPI, Rails, Laravel, SvelteKit, Astro) decides which rules are relevant so a Python CLI repo sees none of them.