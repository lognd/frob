+++
id = "01M35RZY7FY0WTR2G6J87W4WF4"
title = "WEBSEC408-419: Supabase RLS, webhooks, payments, LLM surface (OWASP LLM Top 10)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 8
parent = "01M2Y1SS0R72ZC7F5PSP0BC04T"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5359"]
labels = ["milestone:0.534.0"]
scope = ["tests/fixtures/webapp/websec4xx/rls_llm/**", "src/frob/webapp/_websec_rls_llm.py", "tests/unit/test_websec_rls_llm.py", "docs/modules/webapp-websec-rls-llm.md"]

[[links]]
kind = "blocked-by"
target = "01M336K75PBAVJE0SEABECQYQV"
+++

Config checks: Supabase migration SQL scan for tables missing ENABLE ROW LEVEL SECURITY/policy, anon key used with service scope, webhook signature verification absent (Stripe/GitHub/Twilio/Slack SDK call), webhook timestamp-tolerance absent, payment call missing idempotency_key, read-modify-write on balance/coupon without SELECT-FOR-UPDATE/atomic update (best-effort same-file heuristic), TOCTOU. LLM surface (new detection area, no existing frob substrate): model output flowing to exec/SQL/HTML/shell sinks (reuses 5141-1's taint substrate), tool/function definitions with write/spend capability and no confirmation gate, system-prompt literals containing secrets/PII (reuses SEC001-003 patterns), missing max_tokens/budget on completion calls, retrieval sources without access filtering. Start with OpenAI + Anthropic SDK shapes; LangChain/LlamaIndex as a follow-up ticket if scope grows past this leaf's budget. Fixture per rule id.
