# frob.webapp._websec_rls_llm -- WEBSEC408-419 Supabase RLS, webhooks, payments, LLM surface

One sentence: `frob.webapp._websec_rls_llm.websec_rls_llm_findings`
extends `frob.gates._taint_gate.taint_gate`'s WEBSEC scan with a rule
family covering Supabase row-level-security, webhook/payment
integration hardening, and an LLM-surface family shaped after the OWASP
LLM Top 10, folded into `taint_gate`'s own scan via T-5308's
pkgutil-discovery hook rather than a second gate registration -- the
same reasoning T-5307's `docs/modules/webapp-websec-injection.md`
already documents for WEBSEC101-106.

This is a downstream leaf of the T-5140 web-app epic's seven-sibling
substrate wave (`docs/modules/webapp.md`'s own scope: framework
detection only, not any individual rule family).

## Framework gating

`websec_rls_llm_findings(root)` calls
`frob.webapp._detect.detect_frameworks` first and returns `()`
immediately for a repo with no detected web framework -- the same
short-circuit every WEBSEC/COMPLY/A11Y/SEO/WEBPERF family uses (T-5302).
This module never re-implements framework sniffing.

## Rule catalog

All twelve rules are TEXT-REGEX/text-window scans, the same
disclosed-gap "textual proxy, not resolved data-flow" posture every
text-regex WEBSEC family in this epic carries.

### Data/integration

| rule | shape | detection |
| --- | --- | --- |
| WEBSEC408 | a `CREATE TABLE` with no `ENABLE ROW LEVEL SECURITY` anywhere in the same `.sql` migration file | tracked-`.sql`-file text scan |
| WEBSEC409 | an anon-scoped Supabase key identifier used within the same text window as a `service_role` reference | text-window scan |
| WEBSEC410 | a webhook-shaped route handler with no signature-verification call anywhere in the file | text scan |
| WEBSEC411 | a webhook handler WITH signature verification present but no tolerance/timestamp-window keyword anywhere in the file | text scan |
| WEBSEC412 | a payment-provider `.create(`-shaped call with no `idempotency_key` keyword in the same call window | text-window scan |
| WEBSEC413 | a `balance`/`coupon`-referencing update with no `FOR UPDATE`/`select_for_update`/atomic-update keyword in the same text window | text-window scan |

### LLM surface (OWASP LLM Top 10)

Starts with OpenAI + Anthropic SDK call shapes only; LangChain/LlamaIndex
support is a follow-up ticket if scope grows past this leaf's own
budget, per the ticket body.

| rule | shape | detection | OWASP LLM Top 10 |
| --- | --- | --- | --- |
| WEBSEC414 | a stock/quantity availability check followed by a decrement/update call in the same window with no locking keyword in between | text-window scan | (TOCTOU, generic sibling of WEBSEC413) |
| WEBSEC415 | an LLM response accessor flowing directly into an exec/SQL/HTML/shell sink within the same text window | text-window scan | LLM01/LLM02 |
| WEBSEC416 | a tool/function definition whose name suggests a write/spend capability with no confirmation/approval keyword nearby | text-window scan | LLM06 |
| WEBSEC417 | a system-prompt string literal containing a secret/PII-shaped literal | text scan (reuses SEC001-003's secret-literal vocabulary) | LLM07 |
| WEBSEC418 | a completion call with no `max_tokens` keyword in the same call window | text-window scan | LLM10 |
| WEBSEC419 | a retrieval query call with no filter/namespace/user-scoping keyword in the same call window | text-window scan | LLM08 |

WEBSEC414 sits in the LLM-surface half of the rule id block numerically
(`WEBSEC408`-`WEBSEC413` data/integration, `WEBSEC414`-`WEBSEC419` here)
but is conceptually a data/integration rule -- the generic check-then-act
(TOCTOU) sibling of WEBSEC413's balance/coupon-specific heuristic,
grouped with the LLM half only by id-range position, not by topic.

## Severity

WARN-tier at first turn-on -- the same T-0688/T-0973 promotion posture
`taint_gate`/every other WEBSEC family in this epic already follows for
a brand-new structural rule.

## Public API

- `WebsecRlsLlmFinding` (`src/frob/webapp/_websec_rls_llm.py`) -- one
  finding: `rule`, `file`, `line`, `message`.
- `websec_rls_llm_findings(root: Path) -> tuple[WebsecRlsLlmFinding, ...]`
  -- every WEBSEC408-419 finding under `root`.
- `websec_findings(root: Path, frameworks: frozenset[FrameworkKind]) ->
  tuple[frob.findings.Violation, ...]` -- the `taint_gate` module-
  discovery hook (T-5308): `frob.gates._taint_gate.taint_gate`
  auto-discovers every `frob.webapp._websec_*` module exposing a
  module-level `websec_findings(root, frameworks)` callable and folds
  its returned `Violation`s into the same tuple it returns, so this
  leaf never needs its own hand-edit to `_taint_gate.py`/
  `gates/__init__.py`. `frameworks` is the caller's own
  already-computed `detect_frameworks(root)` result (this hook never
  re-detects); an empty set short-circuits to `()`, same contract as
  `websec_rls_llm_findings` itself.

## Tests and fixtures

`tests/unit/test_websec_rls_llm.py` -- one positive-control and one
negative-control fixture per rule under
`tests/fixtures/webapp/websec4xx/rls_llm/webesc4{08..19}_{positive,negative}/`,
each carrying a minimal Flask (`requirements.txt` with `flask`)
framework marker so `detect_frameworks` fires, plus exactly the
SQL/config/handler shape under test. Also includes an end-to-end
positive control (`test_taint_gate_discovers_websec_rls_llm_hook`)
proving `frob.gates._taint_gate.taint_gate` discovers and calls this
module's hook with no `_taint_gate.py` edit.

frob:ticket T-5359
