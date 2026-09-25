---
id: T-draft-1e1d6060
title: Helm values ingestion
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
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
- src/frob/lang/_config_helm.py (new)
- tests/fixtures/sysdesign/config-helm/**
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
title: Helm values ingestion
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_helm.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-helm/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

SYSDESIGN-INVENTORY.md sec 2: "Helm: NOT PARSED. The 'helm' git-grep hits (22 files) are false
positives -- every one traced back is either the English word 'help'-derived or... the JS
`helmet()` middleware call-site scan for WEBSEC-family security-header checks, unrelated to
Helm charts." Genuine zero-coverage gap.

Acceptance criteria: `frob.lang._config_helm.parse(chart_dir) -> list[ConfigDoc]` reads
`values.yaml` plus any `values-<env>.yaml` overlays, resolving the merge order Helm itself uses
(base values overridden by environment-specific files, last-wins) so downstream rules see the
same effective config Helm would render. Positive-control fixture: tests/fixtures/sysdesign/
config-helm/base-plus-override/** proving override-merge order.
