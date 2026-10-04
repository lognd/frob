+++
id = "01M3AXSDB73R2KVGH468Z79R41"
title = "Envoy/NGINX/Caddy structured config ingestion"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSD8TNZP3PQVKB7EKCR7M"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:26Z"
aliases = ["T-6503"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/lang/_config_proxy.py (new)", "tests/fixtures/sysdesign/config-proxy/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD7WN9GJ27A1ZEMT1JYG"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: Envoy/NGINX/Caddy structured config ingestion
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 5
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_proxy.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-proxy/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

SYSDESIGN-INVENTORY.md sec 2: nginx.conf and Caddyfile are "LINE-REGEX SCANNED (not parsed)"
for one narrow WEBSEC purpose (`add_header`, `autoindex on;`); "envoy yaml: NOT FOUND. Zero
hits for 'envoy' anywhere in src/." This leaf gives Story C's LB/mesh rules (active/passive
health checks, outlier detection, circuit breaking, mTLS) a structural read instead of a
regex scan, without duplicating or replacing the existing WEBSEC header-line scan (NO
DUPLICATION -- WEBSEC's scan stays as-is; this is a separate, structural reader for a different
rule family's needs).

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: `frob.lang._config_proxy.parse(path) -> list[ConfigDoc]` covers Envoy
YAML (`clusters[].health_checks`, `outlier_detection`, `circuit_breakers`, `transport_socket`
for mTLS), nginx.conf directives (`client_max_body_size`, `limit_conn_zone`,
`keepalive_timeout`, timeouts), and Caddyfile equivalents, as a structural extractor (block/
directive-aware, not a byte-regex) for the specific directive names Story C's rules need.
Positive-control fixture: tests/fixtures/sysdesign/config-proxy/envoy-no-outlier-detection/**.
