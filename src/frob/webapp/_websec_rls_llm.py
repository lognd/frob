"""WEBSEC408-419: Supabase RLS, webhooks, payments, and LLM surface
(docs/modules/webapp-websec-rls-llm.md, T-5359, the T-5140 web-app
epic's RLS/webhook/payment/LLM leaf, OWASP LLM Top 10-shaped for the
LLM half).

Same posture as every WEBSEC family in this epic: framework-gated
(short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
reports no web framework, T-5302's own contract), and folded into
`frob.gates._taint_gate.taint_gate` via the `websec_findings(root,
frameworks)` pkgutil-discovery hook (T-5308) rather than a second gate
registration. All twelve rules are TEXT-REGEX/text-window scans -- the
same disclosed-gap "textual proxy, not resolved data-flow" posture
every text-regex WEBSEC family in this epic carries.

TWELVE RULE IDS (T-5301's reserved `WEBSEC408`-`WEBSEC419` block), six
"data/integration" rules and six "LLM surface" rules (the LLM half is a
NEW detection area -- no prior frob substrate -- OWASP LLM Top 10
shaped, starting with OpenAI + Anthropic SDK call shapes only;
LangChain/LlamaIndex are a follow-up ticket if scope grows past this
leaf's own budget, per the ticket body):

Data/integration:

- WEBSEC408: a Supabase migration `CREATE TABLE` with no `ENABLE ROW
  LEVEL SECURITY` anywhere in the same `.sql` file.
- WEBSEC409: an anon-scoped Supabase key identifier used within the
  same text window as a `service_role` reference -- anon key granted
  service scope.
- WEBSEC410: a webhook-shaped route handler (Stripe/GitHub/Twilio/Slack
  SDK call or a route/function name containing "webhook") with no
  signature-verification call anywhere in the file.
- WEBSEC411: a webhook handler WITH signature verification present but
  no "tolerance"/timestamp-window keyword anywhere in the file --
  replay-window not bounded.
- WEBSEC412: a payment-provider `.create(`-shaped call (Stripe
  `PaymentIntent`/`charges`) with no `idempotency_key` keyword in the
  same call window -- duplicate-charge risk on retry.
- WEBSEC413: a `balance`/`coupon`-referencing `UPDATE`/ORM `.update(`
  statement with no `FOR UPDATE`/`select_for_update`/atomic-update
  keyword in the same text window -- read-modify-write race
  (TOCTOU-shaped), best-effort same-file heuristic.

LLM surface (OWASP LLM Top 10):

- WEBSEC415: an LLM response accessor (`.choices[0].message.content`/
  `.content` off an Anthropic response) flowing directly into an
  exec/SQL/HTML/shell sink within the same text window (reuses
  T-5307's taint-substrate sink vocabulary rather than reimplementing
  it) -- LLM01 (prompt injection -> unsafe output handling).
- WEBSEC416: a tool/function definition whose name suggests a
  write/spend capability (`transfer`/`charge`/`delete`/`purchase`/
  `refund`) with no "confirm"/"approval" keyword nearby -- LLM06
  (excessive agency).
- WEBSEC417: a system-prompt string literal containing a secret/PII-
  shaped literal (reuses SEC001-003's own secret-literal detection
  vocabulary) -- LLM07 (system prompt leakage).
- WEBSEC418: an OpenAI/Anthropic completion call with no `max_tokens`
  keyword in the same call window -- LLM10 (unbounded consumption).
- WEBSEC419: a vector-store/retriever query call with no
  filter/namespace/user-scoping keyword in the same call window --
  LLM08 (vector/embedding weaknesses, cross-tenant retrieval leakage).

WEBSEC414 (TOCTOU) is the generic check-then-act sibling of WEBSEC413's
balance/coupon-specific heuristic: a stock/quantity availability check
followed by a decrement/update call in the same window with no locking
keyword in between.

Each is WARN-tier at first turn-on, the T-0688/T-0973 promotion posture
every WEBSEC family in this epic follows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.findings import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.webapp._detect import FrameworkKind, detect_frameworks

_log = get_logger(__name__)

__all__ = [
    "WebsecRlsLlmFinding",
    "websec_findings",
    "websec_rls_llm_findings",
]


# frob:doc docs/modules/webapp-websec-rls-llm.md#public-api
@dataclass(frozen=True)
class WebsecRlsLlmFinding:
    """One WEBSEC408-419 finding: a Supabase-RLS/webhook/payment/LLM-
    surface hardening gap.

    frob:ticket T-5359
    """

    rule: str
    file: str
    line: int
    message: str


_WINDOW_CHARS = 400

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\S+)", re.IGNORECASE
)
_ENABLE_RLS_RE = re.compile(r"ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE)

_ANON_KEY_RE = re.compile(r"\bANON_KEY\b|\banon_key\b|\bSUPABASE_ANON_KEY\b")
_SERVICE_ROLE_RE = re.compile(r"service_role|SERVICE_ROLE", re.IGNORECASE)

_WEBHOOK_HANDLER_RE = re.compile(
    r"stripe\.Webhook\.construct_event|def\s+\w*webhook\w*\s*\(|"
    r"function\s+\w*webhook\w*\s*\(|app\.(?:post|route)\(\s*[\"'][^\"']*webhook",
    re.IGNORECASE,
)
_WEBHOOK_VERIFY_RE = re.compile(
    r"construct_event\(|verify_signature\(|verifySignature\(|createHmac\(",
    re.IGNORECASE,
)
_WEBHOOK_TOLERANCE_RE = re.compile(r"tolerance", re.IGNORECASE)

_PAYMENT_CREATE_RE = re.compile(
    r"(?:PaymentIntent|charges)\.create\(([^)]*(?:\)[^)]*)?)\)", re.IGNORECASE
)
_IDEMPOTENCY_KEY_RE = re.compile(r"idempotency_key", re.IGNORECASE)

_BALANCE_UPDATE_RE = re.compile(
    r"UPDATE\s+\w*(?:balance|coupon)\w*\s+SET|\.update\([^)]*(?:balance|coupon)",
    re.IGNORECASE,
)
_ATOMIC_UPDATE_RE = re.compile(r"FOR\s+UPDATE|select_for_update|atomic", re.IGNORECASE)

_STOCK_CHECK_RE = re.compile(
    r"if\s+[\w.]*(?:stock|quantity|inventory)[\w.]*\s*[><=]", re.IGNORECASE
)
_STOCK_MUTATE_RE = re.compile(
    r"\.(?:save|update|decrement|decrease)\(|UPDATE\s+\w*(?:stock|quantity|inventory)",
    re.IGNORECASE,
)

_LLM_OUTPUT_RE = re.compile(
    r"\.choices\[0\]\.message\.content|response\.content\b", re.IGNORECASE
)
_UNSAFE_SINK_RE = re.compile(
    r"\bexec\(|\beval\(|os\.system\(|subprocess\.\w+\(|\.execute\(|innerHTML\s*=|dangerouslySetInnerHTML",
    re.IGNORECASE,
)

_TOOL_WRITE_CAPABILITY_RE = re.compile(
    r"""def\s+(\w*(?:transfer|charge|delete|purchase|refund)\w*)\s*\(""", re.IGNORECASE
)
_CONFIRMATION_RE = re.compile(r"confirm|approval", re.IGNORECASE)

_SYSTEM_PROMPT_RE = re.compile(
    r"""role["']?\s*[:=]\s*["']system["'][^\n]*content["']?\s*[:=]\s*["']([^"']*)["']|"""
    r"""SystemMessage\(\s*content\s*=\s*["']([^"']*)["']""",
    re.IGNORECASE,
)
_SECRET_LITERAL_RE = re.compile(
    r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{12,}|password\s*[:=]|\bssn\b", re.IGNORECASE
)

_COMPLETION_CALL_RE = re.compile(
    r"(?:ChatCompletion\.create|chat\.completions\.create|"
    r"Messages\.create|messages\.create)\(([^)]*(?:\)[^)]*)?)\)",
    re.IGNORECASE,
)
_MAX_TOKENS_RE = re.compile(r"max_tokens", re.IGNORECASE)

_RETRIEVAL_QUERY_RE = re.compile(
    r"\.similarity_search\(([^)]*)\)|\.query\(([^)]*)\)|index\.query\(([^)]*)\)",
    re.IGNORECASE,
)
_ACCESS_SCOPE_RE = re.compile(r"filter\s*=|namespace\s*=|user_id", re.IGNORECASE)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors `_websec_headers_log.
    _tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5359
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_rls_llm: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_rls_llm: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5359
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5359
    """
    return text.count("\n", 0, offset) + 1


def _rls_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC408: a `CREATE TABLE` with no RLS enabled anywhere in the
    same migration file.

    frob:ticket T-5359
    """
    if _ENABLE_RLS_RE.search(text):
        return []
    findings: list[WebsecRlsLlmFinding] = []
    for match in _CREATE_TABLE_RE.finditer(text):
        table = match.group(1)
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC408",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC408: {rel_path}:{line} table {table!r} has "
                    f"no ENABLE ROW LEVEL SECURITY anywhere in this "
                    f"migration -- unrestricted table access via the "
                    f"Supabase API. Enable RLS and a policy, or "
                    f'`frob:waive WEBSEC408 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _anon_service_scope_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC409: an anon-scoped key identifier used within the same
    window as a `service_role` reference.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _ANON_KEY_RE.finditer(text):
        window = text[match.end() : match.end() + _WINDOW_CHARS]
        if not _SERVICE_ROLE_RE.search(window):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC409",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC409: {rel_path}:{line} an anon-scoped "
                    f"Supabase key is used alongside a service_role "
                    f"reference -- anon key granted service scope, "
                    f"RLS bypass. Keep the anon key client-scoped and "
                    f"the service-role key server-only, or "
                    f'`frob:waive WEBSEC409 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _webhook_verification_findings(
    text: str, rel_path: str
) -> list[WebsecRlsLlmFinding]:
    """WEBSEC410: a webhook handler with no signature verification.
    WEBSEC411: verification present but no tolerance/timestamp-window
    keyword.

    frob:ticket T-5359
    """
    handler_match = _WEBHOOK_HANDLER_RE.search(text)
    if handler_match is None:
        return []
    line = _line_of(text, handler_match.start())
    if not _WEBHOOK_VERIFY_RE.search(text):
        return [
            WebsecRlsLlmFinding(
                rule="WEBSEC410",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC410: {rel_path}:{line} a webhook handler "
                    f"exists but this file has no signature-"
                    f"verification call anywhere -- forgeable webhook "
                    f"delivery. Verify the provider's signature, or "
                    f'`frob:waive WEBSEC410 reason="..."` with a real '
                    f"justification"
                ),
            )
        ]
    if _WEBHOOK_TOLERANCE_RE.search(text):
        return []
    return [
        WebsecRlsLlmFinding(
            rule="WEBSEC411",
            file=rel_path,
            line=line,
            message=(
                f"WEBSEC411: {rel_path}:{line} a webhook handler "
                f"verifies signatures but this file has no tolerance/"
                f"timestamp-window keyword anywhere -- replay window "
                f"unbounded. Pass an explicit tolerance, or "
                f'`frob:waive WEBSEC411 reason="..."` with a real '
                f"justification"
            ),
        )
    ]


def _payment_idempotency_findings(
    text: str, rel_path: str
) -> list[WebsecRlsLlmFinding]:
    """WEBSEC412: a payment-provider create call with no
    `idempotency_key` in the same call window.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _PAYMENT_CREATE_RE.finditer(text):
        args = match.group(1) or ""
        if _IDEMPOTENCY_KEY_RE.search(args):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC412",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC412: {rel_path}:{line} a payment create "
                    f"call has no idempotency_key -- a client retry can "
                    f"double-charge. Pass an idempotency_key, or "
                    f'`frob:waive WEBSEC412 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _balance_race_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC413: a balance/coupon update with no locking keyword in the
    same window.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _BALANCE_UPDATE_RE.finditer(text):
        window = text[max(0, match.start() - _WINDOW_CHARS) : match.end()]
        if _ATOMIC_UPDATE_RE.search(window):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC413",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC413: {rel_path}:{line} a balance/coupon "
                    f"update has no SELECT-FOR-UPDATE/atomic-update "
                    f"keyword nearby -- read-modify-write race "
                    f"(best-effort same-file heuristic). Use "
                    f"SELECT ... FOR UPDATE or an atomic update, or "
                    f'`frob:waive WEBSEC413 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _toctou_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC414: a stock/quantity check followed by a decrement/update
    call in the same window with no locking keyword in between.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _STOCK_CHECK_RE.finditer(text):
        window = text[match.end() : match.end() + _WINDOW_CHARS]
        mutate_match = _STOCK_MUTATE_RE.search(window)
        if mutate_match is None:
            continue
        between = window[: mutate_match.start()]
        if _ATOMIC_UPDATE_RE.search(between):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC414",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC414: {rel_path}:{line} a stock/quantity "
                    f"check is followed by a decrement/update with no "
                    f"locking keyword in between -- TOCTOU race. Lock "
                    f"the row or use an atomic decrement, or "
                    f'`frob:waive WEBSEC414 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _llm_output_sink_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC415: an LLM response accessor flowing into an unsafe sink
    within the same window.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _LLM_OUTPUT_RE.finditer(text):
        window = text[match.end() : match.end() + _WINDOW_CHARS]
        sink_match = _UNSAFE_SINK_RE.search(window)
        if sink_match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC415",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC415: {rel_path}:{line} an LLM response "
                    f"flows into an unsafe sink ({sink_match.group(0)!r}) "
                    f"-- unsanitized model output can execute/inject "
                    f"(OWASP LLM01/LLM02). Sanitize/validate the "
                    f"output before the sink, or `frob:waive WEBSEC415 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _tool_confirmation_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC416: a write/spend-shaped tool definition with no
    confirmation keyword nearby.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _TOOL_WRITE_CAPABILITY_RE.finditer(text):
        name = match.group(1)
        window = text[match.end() : match.end() + _WINDOW_CHARS]
        if _CONFIRMATION_RE.search(window):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC416",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC416: {rel_path}:{line} tool/function "
                    f"{name!r} has a write/spend-shaped name but no "
                    f"confirmation/approval keyword nearby -- excessive "
                    f"agency (OWASP LLM06), the model can invoke it "
                    f"unchecked. Add a confirmation gate, or "
                    f'`frob:waive WEBSEC416 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _system_prompt_secret_findings(
    text: str, rel_path: str
) -> list[WebsecRlsLlmFinding]:
    """WEBSEC417: a system-prompt string literal containing a
    secret/PII-shaped literal.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _SYSTEM_PROMPT_RE.finditer(text):
        content = match.group(1) or match.group(2) or ""
        if not _SECRET_LITERAL_RE.search(content):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC417",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC417: {rel_path}:{line} a system-prompt "
                    f"literal appears to contain a secret/PII-shaped "
                    f"value -- system prompt leakage (OWASP LLM07). "
                    f"Move the secret out of the prompt, or "
                    f'`frob:waive WEBSEC417 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _completion_budget_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC418: a completion call with no `max_tokens` in the same call
    window.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _COMPLETION_CALL_RE.finditer(text):
        args = match.group(1) or ""
        if _MAX_TOKENS_RE.search(args):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC418",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC418: {rel_path}:{line} a completion call "
                    f"has no max_tokens -- unbounded consumption "
                    f"(OWASP LLM10). Pass an explicit max_tokens/budget, "
                    f'or `frob:waive WEBSEC418 reason="..."` with a '
                    f"real justification"
                ),
            )
        )
    return findings


def _retrieval_access_findings(text: str, rel_path: str) -> list[WebsecRlsLlmFinding]:
    """WEBSEC419: a retrieval query call with no filter/namespace/
    user-scoping keyword in the same call window.

    frob:ticket T-5359
    """
    findings: list[WebsecRlsLlmFinding] = []
    for match in _RETRIEVAL_QUERY_RE.finditer(text):
        args = match.group(1) or match.group(2) or match.group(3) or ""
        if _ACCESS_SCOPE_RE.search(args):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecRlsLlmFinding(
                rule="WEBSEC419",
                file=rel_path,
                line=line,
                message=(
                    f"WEBSEC419: {rel_path}:{line} a retrieval query "
                    f"has no filter/namespace/user-scoping keyword -- "
                    f"cross-tenant retrieval leakage (OWASP LLM08). "
                    f"Scope the query to the requesting user/tenant, or "
                    f'`frob:waive WEBSEC419 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _file_findings(path: Path, root: Path) -> list[WebsecRlsLlmFinding]:
    """Every WEBSEC408-419 finding in one tracked file.

    frob:ticket T-5359
    """
    rel_path = path.relative_to(root).as_posix()
    text = _read_text(path)
    if not text:
        return []
    findings: list[WebsecRlsLlmFinding] = []
    if rel_path.endswith(".sql"):
        findings.extend(_rls_findings(text, rel_path))
    findings.extend(_anon_service_scope_findings(text, rel_path))
    findings.extend(_webhook_verification_findings(text, rel_path))
    findings.extend(_payment_idempotency_findings(text, rel_path))
    findings.extend(_balance_race_findings(text, rel_path))
    findings.extend(_toctou_findings(text, rel_path))
    findings.extend(_llm_output_sink_findings(text, rel_path))
    findings.extend(_tool_confirmation_findings(text, rel_path))
    findings.extend(_system_prompt_secret_findings(text, rel_path))
    findings.extend(_completion_budget_findings(text, rel_path))
    findings.extend(_retrieval_access_findings(text, rel_path))
    return findings


# frob:doc docs/modules/webapp-websec-rls-llm.md#public-api
# frob:ticket T-5359
def websec_rls_llm_findings(root: Path) -> tuple[WebsecRlsLlmFinding, ...]:
    """WEBSEC408-419: every Supabase-RLS/webhook/payment/LLM-surface
    finding under `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all (T-5302's own contract, the same
    posture every WEBSEC family in this epic follows).

    frob:ticket T-5359
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_rls_llm: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecRlsLlmFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx", ".sql"):
        findings.extend(_file_findings(root / rel, root))

    _log.info("websec_rls_llm: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-rls-llm.md#public-api
# frob:ticket T-5359
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """T-5308's `taint_gate` module-discovery hook: every
    `frob.webapp._websec_*` module exposing a module-level
    `websec_findings(root, frameworks) -> tuple[Violation, ...]` is
    auto-discovered and folded into `taint_gate`'s scan, so this new
    WEBSEC family never needs its own `gates/__init__.py`/`_taint_gate.py`
    edit. `frameworks` is the caller's own already-computed
    `detect_frameworks(root)` result (avoids a second detect call per
    discovered module) -- an empty set short-circuits to `()` exactly
    like `websec_rls_llm_findings`'s own direct-call contract.

    frob:ticket T-5359
    """
    if not frameworks:
        _log.debug(
            "websec_rls_llm: no framework detected at %s, skipping scan (hook)", root
        )
        return ()
    return tuple(
        Violation(
            rule=finding.rule,
            severity=Severity.WARN,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )
        for finding in websec_rls_llm_findings(root)
    )
