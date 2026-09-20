---
id: T-draft-809836e5
title: 'WEBSEC authorization, business logic and LLM surface: admin routes without
  auth, front-end-only guards, IDOR/BOLA, mass assignment, RLS off, webhook signature
  and replay, payment idempotency, TOCTOU, resource limits, OWASP LLM Top 10 2025
  (ASVS V4 V8, API Top 10, LLM Top 10)'
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
threat: elevation-of-privilege
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
33 entries, 23 static, 9 config. Static rules: route handlers under /admin or with admin in name lacking the auth decorator/middleware the framework uses; permission checks only in client code (React route guards with no server counterpart for the same path); ORM lookups by id from request with no owner filter; request.json/params passed whole to create/update; Supabase tables without RLS policy in migrations, anon key used with service scope; webhook handlers without signature verification and timestamp tolerance (Stripe, GitHub, Twilio, Slack); payment calls without idempotency key; read-modify-write on balance/coupon without SELECT FOR UPDATE or atomic update; list endpoints without pagination; no per-user rate limit on auth and expensive endpoints. LLM rules: model output flowing to exec/SQL/HTML/shell sinks; tool definitions with write or spend capability and no confirmation gate; system prompt literals containing secrets or PII; no max_tokens or budget on completion calls; retrieval sources without access filtering. Cites in corpus.