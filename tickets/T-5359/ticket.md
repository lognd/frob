---
id: T-5359
title: 'WEBSEC408-419: Supabase RLS, webhooks, payments, LLM surface (OWASP LLM Top
  10)'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5144
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_authz_integrations.py
- src/frob/webapp/_websec_llm.py
- tests/fixtures/webapp/websec4xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Config checks: Supabase migration SQL scan for tables missing ENABLE ROW LEVEL SECURITY/policy, anon key used with service scope, webhook signature verification absent (Stripe/GitHub/Twilio/Slack SDK call), webhook timestamp-tolerance absent, payment call missing idempotency_key, read-modify-write on balance/coupon without SELECT-FOR-UPDATE/atomic update (best-effort same-file heuristic), TOCTOU. LLM surface (new detection area, no existing frob substrate): model output flowing to exec/SQL/HTML/shell sinks (reuses 5141-1's taint substrate), tool/function definitions with write/spend capability and no confirmation gate, system-prompt literals containing secrets/PII (reuses SEC001-003 patterns), missing max_tokens/budget on completion calls, retrieval sources without access filtering. Start with OpenAI + Anthropic SDK shapes; LangChain/LlamaIndex as a follow-up ticket if scope grows past this leaf's budget. Fixture per rule id.