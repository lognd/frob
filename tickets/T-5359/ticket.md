---
id: T-5359
title: 'WEBSEC408-419: Supabase RLS, webhooks, payments, LLM surface (OWASP LLM Top
  10)'
state: done
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5144
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5359
branch: t-5359
scope:
- tests/fixtures/webapp/websec4xx/rls_llm/**
- src/frob/webapp/_websec_rls_llm.py
- tests/unit/test_websec_rls_llm.py
- docs/modules/webapp-websec-rls-llm.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec4xx/**
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/webapp/_websec_authz_integrations.py
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/webapp/_websec_llm.py
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/websec4xx/rls_llm/**
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/webapp/_websec_rls_llm.py
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_websec_rls_llm.py
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-websec-rls-llm.md
  reason: per-ticket fixture subdir to avoid T-5357 lease collision; consolidated
    to one module _websec_rls_llm.py per coordinator naming; scope test file + doc
    per playbook convention
  actor: logan
  at: '2026-09-24'
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
- field: points
  old_value: '5'
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_websec_rls_llm.py::test_taint_gate_discovers_websec_rls_llm_hook
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc408_positive-WEBSEC408-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc408_negative-WEBSEC408-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc409_positive-WEBSEC409-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc409_negative-WEBSEC409-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc410_positive-WEBSEC410-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc410_negative-WEBSEC410-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc411_positive-WEBSEC411-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc411_negative-WEBSEC411-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc412_positive-WEBSEC412-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc412_negative-WEBSEC412-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc413_positive-WEBSEC413-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc413_negative-WEBSEC413-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc414_positive-WEBSEC414-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc414_negative-WEBSEC414-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc415_positive-WEBSEC415-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc415_negative-WEBSEC415-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc416_positive-WEBSEC416-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc416_negative-WEBSEC416-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc417_positive-WEBSEC417-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc417_negative-WEBSEC417-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc418_positive-WEBSEC418-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc418_negative-WEBSEC418-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc419_positive-WEBSEC419-True]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc419_negative-WEBSEC419-False]
- tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_no_framework_short_circuits
- tests/unit/test_websec_rls_llm.py::test_websec_findings_discovery_hook_emits_violation
- tests/unit/test_websec_rls_llm.py::test_websec_findings_discovery_hook_empty_frameworks_short_circuits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Config checks: Supabase migration SQL scan for tables missing ENABLE ROW LEVEL SECURITY/policy, anon key used with service scope, webhook signature verification absent (Stripe/GitHub/Twilio/Slack SDK call), webhook timestamp-tolerance absent, payment call missing idempotency_key, read-modify-write on balance/coupon without SELECT-FOR-UPDATE/atomic update (best-effort same-file heuristic), TOCTOU. LLM surface (new detection area, no existing frob substrate): model output flowing to exec/SQL/HTML/shell sinks (reuses 5141-1's taint substrate), tool/function definitions with write/spend capability and no confirmation gate, system-prompt literals containing secrets/PII (reuses SEC001-003 patterns), missing max_tokens/budget on completion calls, retrieval sources without access filtering. Start with OpenAI + Anthropic SDK shapes; LangChain/LlamaIndex as a follow-up ticket if scope grows past this leaf's budget. Fixture per rule id.