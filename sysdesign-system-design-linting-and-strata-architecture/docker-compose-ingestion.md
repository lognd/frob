+++
id = "01M3AXSD86HDFQN74EXZ45GAQ9"
title = "docker-compose ingestion"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-6406"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/lang/_config_compose.py (new)", "tests/fixtures/sysdesign/config-compose/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: docker-compose ingestion
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_compose.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-compose/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

SYSDESIGN-INVENTORY.md sec 2: "docker-compose: NOT FOUND. Zero hits for 'docker-compose'/
'compose.yaml' in src/." Genuine zero-coverage gap.

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: `frob.lang._config_compose.parse(path) -> list[ConfigDoc]` reads
`services.<name>.{image, ports, environment, depends_on, deploy.resources, restart}` from
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->compose.yaml/docker-compose.yml. Positive-control fixture: tests/fixtures/sysdesign/
config-compose/env-baked-secret-in-service/**.
