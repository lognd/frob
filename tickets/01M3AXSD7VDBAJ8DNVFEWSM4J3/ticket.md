+++
id = "01M3AXSD7VDBAJ8DNVFEWSM4J3"
title = "Helm values ingestion"
type = "task"
category = "triage"
priority = "medium"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-09-25T00:00:00Z"
aliases = ["T-6395"]
labels = ["milestone:0.539.0", "v1-cluster:B1", "area:grimble"]
scope = ["src/frob/lang/_config_helm.py (new)", "tests/fixtures/sysdesign/config-helm/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
+++

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

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: `frob.lang._config_helm.parse(chart_dir) -> list[ConfigDoc]` reads
`values.yaml` plus any `values-<env>.yaml` overlays, resolving the merge order Helm itself uses
(base values overridden by environment-specific files, last-wins) so downstream rules see the
same effective config Helm would render. Positive-control fixture: tests/fixtures/sysdesign/
config-helm/base-plus-override/** proving override-merge order.
