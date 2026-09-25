---
id: T-draft-ebcfc698
title: Envoy/NGINX/Caddy structured config ingestion
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
- src/frob/lang/_config_proxy.py (new)
- tests/fixtures/sysdesign/config-proxy/**
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

Acceptance criteria: `frob.lang._config_proxy.parse(path) -> list[ConfigDoc]` covers Envoy
YAML (`clusters[].health_checks`, `outlier_detection`, `circuit_breakers`, `transport_socket`
for mTLS), nginx.conf directives (`client_max_body_size`, `limit_conn_zone`,
`keepalive_timeout`, timeouts), and Caddyfile equivalents, as a structural extractor (block/
directive-aware, not a byte-regex) for the specific directive names Story C's rules need.
Positive-control fixture: tests/fixtures/sysdesign/config-proxy/envoy-no-outlier-detection/**.
