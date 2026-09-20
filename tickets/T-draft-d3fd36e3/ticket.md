---
id: T-draft-d3fd36e3
title: 'WEBSEC configuration, headers and supply chain: CSP/HSTS/COOP/CORP set, CORS,
  debug flags, source maps, stack traces, public buckets, secrets in bundles and CI,
  Actions SHA pinning, Dockerfile root, timeouts and body limits, audit logging (ASVS
  V3 V13 V14 V16)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
parent: T-draft-09897a86
tier: story
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
- path: T-draft-d3fd36e3/attachments/01-untitled.md
  caption: ''
  sha256: 4877bdd1f05f0675b70cb0e544d8afc03645379e3c2faa9dd40b133b1a0b544e
threat: info-disclosure
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
39 entries in the attached corpus, 26 static, 13 config. Config rules read next.config, vite.config, nginx/caddy, helmet or secure-headers usage, Django SECURE_* and DEBUG, Flask debug, NODE_ENV, tsconfig/webpack sourcemap in prod build, .github/workflows uses: pinned by tag, pull_request_target with checkout of PR head, Dockerfile USER and :latest, storage bucket policies (S3 public-read, Supabase storage policies), CORS * with credentials or reflected origin, Cache-Control on authenticated responses, outbound HTTP calls without timeout, upload and body size limits absent, auth events not logged, PII in log format strings. Every rule cites the ASVS id from the corpus; header values cite the OWASP Secure Headers Project. Extends SEC001-003 (secrets) with front-end bundle and CI-log scanning.