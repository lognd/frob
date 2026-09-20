---
id: T-5144
title: 'WEBSEC authorization, business logic and LLM surface: admin routes without
  auth, front-end-only guards, IDOR/BOLA, mass assignment, RLS off, webhook signature
  and replay, payment idempotency, TOCTOU, resource limits, OWASP LLM Top 10 2025
  (ASVS V4 V8, API Top 10, LLM Top 10)'
state: queued
kind: security
origin: human
created: '2026-09-20'
priority: critical
parent: T-5140
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
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 1054
  new_length: 21915
designated_repro_test: null
threat: elevation-of-privilege
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
33 entries, 23 static, 9 config. Static rules: route handlers under /admin or with admin in name lacking the auth decorator/middleware the framework uses; permission checks only in client code (React route guards with no server counterpart for the same path); ORM lookups by id from request with no owner filter; request.json/params passed whole to create/update; Supabase tables without RLS policy in migrations, anon key used with service scope; webhook handlers without signature verification and timestamp tolerance (Stripe, GitHub, Twilio, Slack); payment calls without idempotency key; read-modify-write on balance/coupon without SELECT FOR UPDATE or atomic update; list endpoints without pagination; no per-user rate limit on auth and expensive endpoints. LLM rules: model output flowing to exec/SQL/HTML/shell sinks; tool definitions with write or spend capability and no confirmation gate; system prompt literals containing secrets or PII; no max_tokens or budget on completion calls; retrieval sources without access filtering. Cites in corpus.

# Authorization, business logic, API, and LLM lint authorities (ASVS V4, V8 + OWASP API Top 10 2023 + OWASP LLM Top 10 2025)

Authority base: OWASP ASVS 5.0.0 flat requirements JSON (same source as the
other appsec files); OWASP API Security Top 10 2023, fetched at
https://owasp.org/API-Security/editions/2023/en/0x11-t10/; OWASP Top 10 for
LLM Applications 2025, fetched at https://genai.owasp.org/llm-top-10/.

## Part A -- function-level auth, IDOR/BOLA, business logic (ASVS V4/V8 + API Top 10 2023)

### 1. Function-level auth on admin routes
Authority: ASVS 5.0 V8.2.1; API Top 10 2023, API5:2023 Broken Function Level Authorization
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: ASVS V8.2.1: "Verify that the application ensures that function-level access is restricted to consumers with explicit permissions." Page confirms category "API5:2023 - Broken Function Level Authorization."
Lint condition: route-table lint for an `/admin/*` (or role-gated) route registered with no role/permission-check decorator or middleware in the handler chain.
Static: yes

### 2. Front-end-only permission guards
Authority: ASVS 5.0 V8.3.1
URL: https://github.com/OWASP/ASVS (chapter V8, Authorization)
Quote: "Verify that the application enforces authorization rules at a trusted service layer and doesn't rely on controls that an untrusted consumer could manipulate, such as client-side JavaScript."
Lint condition: code lint for a UI component conditionally rendering an admin/privileged action (`if (user.role === 'admin') <Button/>`) with no matching server-side authorization check found for the API route that action calls.
Static: yes

### 3. IDOR / BOLA
Authority: ASVS 5.0 V8.2.2 (from prior pass); API Top 10 2023, API1:2023 Broken Object Level Authorization
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: ASVS V8.2.2: "Verify that the application ensures that data-specific access is restricted to consumers with explicit permissions to specific data items to mitigate insecure direct object reference (IDOR) and broken object level authorization (BOLA)." Page confirms "API1:2023 - Broken Object Level Authorization" as the top-ranked API risk.
Lint condition: handler lint for `GET/PUT/DELETE /resource/:id` with no `WHERE owner_id = current_user` (or RLS-equivalent) clause before returning/mutating the row.
Static: yes

### 4. BOPLA (broken object property level authorization)
Authority: ASVS 5.0 V8.2.3, V15.3.1 (from prior pass); API Top 10 2023, API3:2023 Broken Object Property Level Authorization
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: ASVS V8.2.3: "Verify that the application ensures that field-level access is restricted to consumers with explicit permissions to specific fields to mitigate broken object property level authorization (BOPLA)." Page confirms "API3:2023 - Broken Object Property Level Authorization" (merges the prior 2019 "Excessive Data Exposure" and "Mass Assignment" categories).
Lint condition: serializer lint for a response schema exposing internal-only fields (`is_admin`, `internal_notes`, `cost_basis`) with no per-role field allowlist.
Static: yes

### 5. Mass assignment
Authority: ASVS 5.0 V15.3.3 (from prior pass); API Top 10 2023, API3:2023 (mass assignment folded into BOPLA)
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: ASVS V15.3.3: "Verify that the application has countermeasures to protect against mass assignment attacks by limiting allowed fields per controller and action."
Lint condition: ORM lint for `Model.create(**request.json)`/`Model(**form.data)` whole-body assignment with no explicit DTO/allowlist.
Static: yes

### 6. Predictable/sequential IDs exposed
Authority: ASVS 5.0 V6.5.3, V11.2.2 (CSPRNG-generation requirement generalized to public-facing resource identifiers); CWE-330 (Use of Insufficiently Random Values)
URL: https://github.com/OWASP/ASVS
Quote: same CSPRNG-generation text cited in the session/auth file's item 27, applied here to primary-key/resource-ID generation instead of tokens.
Lint condition: schema lint for a publicly-referenced resource ID (invoice number, order ID, share link) backed by an auto-incrementing integer primary key rather than a UUID/ULID, on any endpoint lacking an independent ownership check.
Static: yes

### 7. RLS off / default DB grants
Authority: ASVS 5.0 V8.2.2 (data-specific access restriction, generalized to the database layer); Supabase RLS docs (cross-referenced from lint-authorities.md item E35)
URL: https://github.com/OWASP/ASVS ; https://supabase.com/docs/guides/database/postgres/row-level-security
Quote: same ASVS V8.2.2 text as item 3, applied at the database-policy layer instead of the application-handler layer.
Lint condition: migration lint for `CREATE TABLE` with no matching `ENABLE ROW LEVEL SECURITY`, and for a `GRANT` statement giving the `anon`/public role `SELECT`/`INSERT`/`UPDATE`/`DELETE` on a table with no accompanying RLS policy.
Static: yes

### 8. Multi-tenant cross-tenant isolation
Authority: ASVS 5.0 V8.4.1
URL: https://github.com/OWASP/ASVS (chapter V8)
Quote: "Verify that multi-tenant applications use cross-tenant controls to ensure consumer operations will never affect tenants with which they do not have permissions to interact."
Lint condition: query-builder lint for a multi-tenant schema (shared tables with a `tenant_id` column) where a query/handler omits the `tenant_id` filter, relying only on the row's own `id`.
Static: yes

### 9. Administrative interface hardening
Authority: ASVS 5.0 V8.4.2
URL: https://github.com/OWASP/ASVS (chapter V8)
Quote: "Verify that access to administrative interfaces incorporates multiple layers of security, including continuous consumer identity verification, device security posture assessment, and contextual risk analysis, ensuring that network..."
Lint condition: infra config lint for an admin panel/dashboard route reachable from the public internet with no additional network control (IP allowlist, VPN-only, separate auth realm) layered on top of standard app auth.
Static: config

### 10. Webhook signature verification
Authority: cross-reference lint-authorities.md item A22 (Stripe webhook signature docs); ASVS 5.0 V6.8.3 (replay-prevention framing, generalized from SAML assertions to any signed webhook payload)
URL: https://docs.stripe.com/webhooks ; https://github.com/OWASP/ASVS
Quote: Stripe: "You perform the verification by providing the event payload, the Stripe-Signature header, and the endpoint's secret." ASVS V6.8.3 (SAML-specific text): "Verify that SAML assertions are uniquely processed and used only once within the validity period to prevent replay attacks" -- the same replay-window principle applies to any webhook.
Lint condition: webhook-handler lint for a route parsing the body before signature verification, or never calling the verification function at all.
Static: yes

### 11. Webhook replay window
Authority: same ASVS V6.8.3/V10.3.5 replay-prevention class cited in lint-authorities.md item E36's cross-reference
URL: https://github.com/OWASP/ASVS
Quote: V10.3.5: "Verify that the resource server prevents the use of stolen access tokens or replay of access tokens (from unauthorized parties) by requiring..." sender-constraint or timestamp-bound validation -- the same replay-window principle Stripe documents as checking the `Stripe-Signature` timestamp tolerance.
Lint condition: webhook-handler lint for signature verification performed with no timestamp-tolerance check (accepting a signed payload regardless of age), enabling replay of a captured request.
Static: yes

### 12. Payment idempotency keys
Authority: no dedicated ASVS 5.0 requirement id found this pass with the phrase "idempotency" (searched and got zero hits); cross-reference V2.3.3's transactional-integrity framing and Stripe's own idempotency-key documentation (not independently re-fetched this pass beyond the webhooks page already pulled).
URL: https://github.com/OWASP/ASVS (V2.3.3, adjacent) ; https://docs.stripe.com/webhooks
Quote: ASVS V2.3.3: "Verify that transactions are being used at the business logic level such that either a business logic operation succeeds in its entirety or it is rolled back to the previous correct state." (Idempotency-key support is the standard mechanism payment processors document for making retried requests safe under this same principle.)
Lint condition: payment-handler lint for a charge-creation call with no `Idempotency-Key` header/parameter passed, risking duplicate charges on client retry.
Static: yes

### 13. Coupon/balance TOCTOU
Authority: ASVS 5.0 V2.3.4, V15.4.1, V15.4.2 (from prior pass, business-logic locking + race-condition chapters)
URL: https://github.com/OWASP/ASVS
Quote: V2.3.4: "Verify that business logic level locking mechanisms are used to ensure that limited quantity resources (such as theater seats or delivery slots) cannot be double-booked by manipulating the application[']s timing."
Lint condition: code lint for a read-check-then-write pattern on a coupon-redemption or balance-deduction column with no DB-level lock/transaction/unique constraint enforcing atomicity.
Static: yes

### 14. Unrestricted resource consumption -- no pagination
Authority: ASVS 5.0 V15.2.2 (from prior pass); API Top 10 2023, API4:2023 Unrestricted Resource Consumption
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: page confirms "API4:2023 - Unrestricted Resource Consumption" as a top-10 API risk; ASVS V15.2.2 requires "defenses against loss of availability due to functionality which is time-consuming or resource-demanding."
Lint condition: list/collection-endpoint lint for a handler returning `SELECT *`/all rows with no `LIMIT`/page-size cap and no `?page=`/cursor parameter.
Static: yes

### 15. Rate limiting per-user and per-IP
Authority: ASVS 5.0 V6.1.1, V2.4.1 (from prior pass); API Top 10 2023, API4:2023
URL: https://github.com/OWASP/ASVS ; https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: V2.4.1: "Verify that anti-automation controls are in place to protect against excessive calls to application functions that could lead to data exfiltration, garbage-data creation, quota exhaustion, rate-limit breaches, denial-of-[service]."
Lint condition: route config lint for a public/authenticated endpoint with no rate-limit middleware keyed on both IP and account/API-key identity.
Static: config

### 16. API inventory / undocumented and legacy versions
Authority: API Top 10 2023, API9:2023 Improper Inventory Management
URL: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: page confirms "API9:2023 - Improper Inventory Management" as a top-10 API risk (covers undocumented/shadow/deprecated API versions still reachable).
Lint condition: route-table diff lint comparing the deployed router's registered paths against the published API spec (OpenAPI/GraphQL schema), flagging any live route absent from the spec, and flagging any `/v1/` route still mounted after a documented `/v2/` migration with no deprecation/sunset header.
Static: config

### 17. Unsafe consumption of third-party APIs
Authority: API Top 10 2023, API10:2023 Unsafe Consumption of APIs (not independently re-quoted this pass -- confirmed only via the numbered-list grep, which returned "API6:2023 - Unrestricted..." truncated before this session's grep window; flagging API10 specifically as needing a direct re-fetch)
URL: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: BLOCKED for a verbatim API10:2023 quote this pass -- the category's presence in the 2023 list is well-documented (added new in 2023, covering blind trust in data/redirects/responses returned by integrated third-party APIs) but not re-extracted from the raw page text in this pass.
Lint condition: code lint for a server-side call to a third-party API whose response is deserialized and used (URL redirect, file path, SQL parameter, HTML render) with no validation/schema-check on the response body, treating it as trusted input.
Static: yes

### 18. Server-Side Request Forgery via API integrations (cross-ref)
Authority: API Top 10 2023, API7:2023 Server Side Request Forgery; cross-reference lint-authorities.md item E8 / ASVS V1.3.6
URL: https://owasp.org/API-Security/editions/2023/en/0x11-t10/ ; https://github.com/OWASP/ASVS
Quote: page confirms "API7:2023 - Server Side Request Forgery" as a top-10 API risk.
Lint condition: same as lint-authorities.md item E8 -- server-side HTTP-fetch calls with a URL argument from unvalidated request input and no allowlist.
Static: yes

### 19. Security misconfiguration at the API-gateway layer
Authority: API Top 10 2023, API8:2023 Security Misconfiguration
URL: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: page confirms "API8:2023 - Security Misconfiguration" as a top-10 API risk.
Lint condition: API-gateway config lint for missing TLS enforcement, permissive CORS, verbose error responses, or unpatched default configuration at the gateway/ingress layer, distinct from application-level misconfiguration already covered in lint-appsec-config-headers-infra.md.
Static: config

### 20. Broken authentication at the API layer
Authority: API Top 10 2023, API2:2023 Broken Authentication
URL: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
Quote: page confirms "API2:2023 - Broken Authentication" as a top-10 API risk.
Lint condition: cross-reference lint-appsec-session-auth-crypto.md items 1-34, applied specifically to machine-to-machine/API-key auth paths (API-key-only auth with no rotation/expiry, static bearer tokens with no scope restriction).
Static: yes

### 21. Content-Type mismatch / MIME confusion
Authority: ASVS 5.0 V4.1.1 (chapter V4, API and Web Service)
URL: https://github.com/OWASP/ASVS
Quote: "Verify that every HTTP response with a message body contains a Content-Type header field that matches the actual content of the response, including the charset parameter to specify safe character encoding (e.g., UTF-8, ISO-8859-1)."
Lint condition: response-serializer lint for a JSON API endpoint that fails to set `Content-Type: application/json; charset=utf-8` explicitly, or that returns HTML-capable content with a `text/plain` content-type (encouraging browser sniffing).
Static: yes

### 22. Trusted-intermediary headers overridable by end user
Authority: ASVS 5.0 V4.1.3
URL: https://github.com/OWASP/ASVS
Quote: "Verify that any HTTP header field used by the application and set by an intermediary layer, such as a load balancer, a web proxy, or a backend-for-frontend service, cannot be overridden by the end-user. Example headers might inclu[de X-Forwarded-For, X-Real-IP]."
Lint condition: app-code lint for logic trusting `X-Forwarded-For`/`X-Real-IP`/`X-Forwarded-Host` request headers for security decisions (IP allowlisting, auth) without the edge/proxy layer stripping client-supplied copies of the same header first.
Static: config

### 23. HTTP request smuggling via message-boundary ambiguity
Authority: ASVS 5.0 V4.2.1
URL: https://github.com/OWASP/ASVS (chapter V4)
Quote: "Verify that all application components (including load balancers, firewalls, and application servers) determine boundaries of incoming HTTP messages using the appropriate mechanism for the HTTP version to prevent HTTP request smug[gling]."
Lint condition: infra config lint for a reverse-proxy/app-server pair with mismatched `Content-Length`/`Transfer-Encoding` handling, or an outdated server version with known smuggling CVEs in front of a load balancer.
Static: config

## Part B -- OWASP Top 10 for LLM Applications 2025 (genai.owasp.org/llm-top-10)

### 24. LLM01:2025 Prompt Injection
Authority: OWASP Top 10 for LLM Applications 2025, LLM01
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed via page extraction as "LLM01:2025 Prompt Injection."
Lint condition: code lint for an LLM prompt template that concatenates untrusted user/document/tool-output content directly into the system or developer prompt with no delimiter/sanitization strategy, and no output-side check before the model's response is used to take an action.
Static: yes

### 25. LLM02:2025 Sensitive Information Disclosure
Authority: OWASP Top 10 for LLM Applications 2025, LLM02
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM02:2025 Sensitive Information Disclosure."
Lint condition: code lint for a system prompt or few-shot example embedding API keys, internal URLs, or customer PII, and for a retrieval-augmented-generation (RAG) pipeline with no per-document access-control filter before the fetched context is placed into the prompt.
Static: yes

### 26. LLM03:2025 Supply Chain
Authority: OWASP Top 10 for LLM Applications 2025, LLM03
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM03:2025 Supply Chain."
Lint condition: manifest lint for a model/adapter/embedding-model reference pulled from an unpinned Hugging Face revision (`main` branch rather than a commit hash) or an unverified third-party fine-tune, same supply-chain-pinning pattern as item 26 (lint-appsec-config-headers-infra.md item 26).
Static: yes

### 27. LLM04:2025 Data and Model Poisoning
Authority: OWASP Top 10 for LLM Applications 2025, LLM04
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM04:2025 Data and Model Poisoning."
Lint condition: pipeline config lint for a fine-tuning/RAG-ingestion job that consumes user-submitted content (support tickets, reviews, uploaded documents) directly into the training/embedding corpus with no content-validation or provenance-tracking step.
Static: config

### 28. LLM05:2025 Improper Output Handling
Authority: OWASP Top 10 for LLM Applications 2025, LLM05
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM05:2025 Improper Output Handling."
Lint condition: code lint for LLM-generated text passed directly into `eval()`/`exec()`, a shell command, a SQL query string, or rendered as raw HTML (same sinks as lint-appsec-injection-output.md items 2-10) with no output-side validation/sanitization between the model call and the sink.
Static: yes

### 29. LLM06:2025 Excessive Agency
Authority: OWASP Top 10 for LLM Applications 2025, LLM06
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM06:2025 Excessive Agency."
Lint condition: agent/tool-definition lint for a tool with write/delete/send-money/send-email capability registered for autonomous agent use with no human-confirmation gate or scope restriction (e.g., a "send_email" or "execute_sql" tool with no allowlist of permitted actions/targets).
Static: yes

### 30. LLM07:2025 System Prompt Leakage
Authority: OWASP Top 10 for LLM Applications 2025, LLM07
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM07:2025 System Prompt" (Leakage).
Lint condition: same as item 25's first check -- system prompt containing secrets, internal business logic, or credentials that would be damaging if disclosed via a prompt-extraction attack; treat any secret-shaped string in a system-prompt template as a finding.
Static: yes

### 31. LLM08:2025 Vector and Embedding Weaknesses
Authority: OWASP Top 10 for LLM Applications 2025, LLM08
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM08:2025 Vector and Embedding Weaknesses."
Lint condition: vector-store config lint for a shared embedding index/collection with no tenant/namespace isolation (same class as item 8's multi-tenant check) allowing cross-tenant retrieval leakage in a RAG pipeline.
Static: config

### 32. LLM09:2025 Misinformation
Authority: OWASP Top 10 for LLM Applications 2025, LLM09
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM09:2025 Misinformation."
Lint condition: not statically lintable in general (a factual-accuracy problem, not a code defect); the only static proxy is checking that a user-facing AI-generated-content surface carries the disclosure/watermark required under lint-authorities.md item G10 (EU AI Act Art. 50) and provides no unmediated "trust this answer" UI pattern for high-stakes domains (medical/legal/financial) without a human-review gate.
Static: dynamic-only

### 33. LLM10:2025 Unbounded Consumption
Authority: OWASP Top 10 for LLM Applications 2025, LLM10
URL: https://genai.owasp.org/llm-top-10/
Quote: category confirmed as "LLM10:2025 Unbounded Consumption."
Lint condition: API config lint for an LLM-proxying endpoint with no per-user token-budget/rate-limit, no `max_tokens` cap on generation requests, and no cap on the number of chained/recursive tool-calls an agent loop can make per user turn.
Static: config
