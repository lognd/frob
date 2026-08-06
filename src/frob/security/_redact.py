"""Lightweight secret-token detection primitives (T-1318): the exact
regex/entropy/redaction engine `frob.gates._secrets` uses to detect and
redact a real-looking provider secret token, extracted OUT of the
`frob.gates` package tree so importing it never pays that package's
`__init__.py` eager stage-roster import cost (~257ms measured, T-1318's
own incident: `frob.app.telemetry.redact_command`'s `finally`-block call
on EVERY CLI invocation, regardless of subcommand, was dragging in the
whole `frob.gates` aggregator -- pii/arch/dup/vet._capability/testing/...
-- just to reach two private functions).

`frob.gates._secrets` now imports `_PATTERNS`/`_SecretPattern`/`_redact`/
`_scan_line`/the fake-marker constants FROM this module (the dependency
direction T-1318's ticket names: "a lightweight module ... that BOTH
frob.gates._secrets and frob.app.telemetry import") rather than defining
them itself -- this module is the single source of truth for the pattern
table and detection logic; `frob.gates._secrets` adds only the
GATE-specific layer on top (`Violation` construction, `Severity`
classification, file/text-scanning orchestration, the `frob:secret-fake`
staleness/bare-marker gates) that `frob.app.telemetry.redact_command`
never needed and this module deliberately has no dependency on.

`_SecretPattern.severity` is a plain `str` ("error"/"warn"), not
`frob.gates._models.Severity` -- `frob.gates._models` lives inside the
`frob.gates` package this module exists specifically to avoid importing;
`frob.gates._secrets` converts via `Severity(pattern.severity)` (a
`StrEnum` accepts its own value string) at its own `Violation`-construction
call site, the one place that actually needs the enum type.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "_FAKE_MARKER",
    "_FAKE_MARKER_REASON_RE",
    "_PATTERNS",
    "_SecretPattern",
    "_fake_marker_reason",
    "_looks_fake",
    "_redact",
    "_scan_line",
]


_FAKE_MARKER = "frob:secret-fake"

#: T-0968 (gates-quality audit finding 3): a bare `frob:secret-fake` used to
#: discharge SEC001/SEC003 with NO reason string, NO ticket, NO waiver-ledger
#: record at all -- unlike `frob:waive`, which is WAIVE001-enforced to always
#: carry `reason="..."`. This mirrors that exact contract: only a marker
#: matching `frob:secret-fake reason="..."` (this line or the line above)
#: discharges a hit; a marker present but missing `reason=` now gets its own
#: SEC004 violation (mirroring WAIVE001) instead of silently discharging for
#: free -- see `_fake_marker_reason`/`_bare_fake_marker`/`_sec004_violation`.
_FAKE_MARKER_REASON_RE = re.compile(r'frob:secret-fake\s+reason="([^"]*)"')

#: Placeholder shapes inside a token that make it obviously non-real
#: regardless of provider (T-0157: "so docs and tests stay writable").
#: Checked case-insensitively against the matched token text only, never
#: the whole line (a real key sitting next to the word "example" in prose
#: must still fire).
#:
#: T-0968: the bare words `example`/`fake` are DROPPED from this tuple
#: (gates-quality audit finding 3's second complaint -- `_looks_fake` used
#: to suppress any token merely CONTAINING one of these substrings,
#: unanchored, so a real-shaped key sitting next to "EXAMPLE" discharged
#: for free with no marker at all -- AWS's own canonical placeholder access
#: key id (`AKIA` + `IOSFODNN7EXAMPLE`, split here so this comment does not
#: itself trip this repo's own tightened gate/GH013-push-protection checks)
#: used to slip past this way). `changeme`/`placeholder` are kept: both are
#: template-only words no
#: real provider token format ever legitimately contains, so they carry
#: none of `example`/`fake`'s false-negative risk. The anchored
#: template-shape (`_KNOWN_TEMPLATE_SHAPE_RE`) and low-entropy-phrase
#: (`_looks_low_entropy` + `_PLACEHOLDER_PHRASE_RE`) checks below are the
#: only path left for an `example`/`fake`-flavored fixture token; an honest
#: fixture should carry `frob:secret-fake reason="..."` instead.
_PLACEHOLDER_WORDS = ("changeme", "placeholder")
_PLACEHOLDER_RUN_RE = re.compile(r"(x{4,}|\*{4,})", re.IGNORECASE)
#: Placeholder PHRASES (as opposed to single words above) -- T-0219: a
#: fixture like `xoxb-your-...-here` reads as an obvious template
#: to a human but contains none of `_PLACEHOLDER_WORDS`. Matched
#: case-insensitively against the token text, same as `_PLACEHOLDER_WORDS`.
#:
#: BYPASS FIX (T-0219 review round 2): this regex alone is a `.search()`
#: substring test -- a real, high-entropy token that merely CONTAINS
#: `your-`/`insert-`/`-here` anywhere (e.g. a live key naming a tenant
#: "your-company") used to suppress SEC001 unconditionally. It is now only
#: ever consulted through `_looks_fake`, gated by EITHER
#: `_KNOWN_TEMPLATE_SHAPE_RE` (a whole-token structural anchor) OR
#: `_looks_low_entropy` (the phrase must be sitting inside human-written
#: template text, not real secret noise). Never call `.search()` on this
#: pattern directly to decide fakeness again -- go through `_looks_fake`.
_PLACEHOLDER_PHRASE_RE = re.compile(r"(-here\b|\byour-|\binsert-)", re.IGNORECASE)
#: Whole-token ANCHOR (T-0219 bypass fix): a known template *shape* --
#: short provider-ish prefix, then `your-`/`insert-`, then more words,
#: ending in `-here` -- matched with `fullmatch` against the ENTIRE token,
#: never a substring. Catches `xoxb-your-...-here`,
#: `sk-insert-api-key-here`, etc. without needing every placeholder word
#: enumerated, and without ever matching a token that has anything else
#: (digits, unrelated suffix) tacked on after the template.
_KNOWN_TEMPLATE_SHAPE_RE = re.compile(
    r"^[a-z0-9]{2,10}-(your|insert)-[a-z-]+-here$", re.IGNORECASE
)


@dataclass(frozen=True)
# frob:doc docs/guides/extending/secrets-scan-providers.md#secrets-scan-providers
# frob:waive COV007 reason="docs/guides/extending/secrets-scan-providers.md is a whole \
# guide dedicated to this private dataclass, frob:describes-anchored at its own top \
# heading (T-0529) -- a deliberate architecture doc, not accidental drift onto a \
# private helper"
class _SecretPattern:
    """One provider's detection rule: what to match, how bad it is, and how
    much of the match is safe to print back in a violation message."""

    provider: str
    rule: str
    severity: str  # "error"/"warn" -- Severity(pattern.severity) at the
    # frob.gates._secrets call site
    label: str  # "critical" / "high" / "medium" / "low" -- printed in the message
    regex: re.Pattern[str]
    display_prefix: str  # the fixed literal shown in redacted output


def _pat(
    provider: str,
    rule: str,
    severity: str,
    label: str,
    pattern: str,
    display_prefix: str,
) -> _SecretPattern:
    """Build one `_SecretPattern`, compiling `pattern` once at import time."""
    return _SecretPattern(
        provider=provider,
        rule=rule,
        severity=severity,
        label=label,
        regex=re.compile(pattern),
        display_prefix=display_prefix,
    )


# Ordered most-specific-prefix first so overlapping charsets (e.g. Stripe's
# "sk_" family vs. a hypothetical generic "sk" scan) never double-report the
# same span under two providers -- `_scan_line` keeps only the first pattern
# that claims a given span. Each regex carries a length/charset floor to cut
# false positives on short, coincidental substrings.


_PATTERNS: tuple[_SecretPattern, ...] = (
    _pat(
        "anthropic",
        "SEC001",
        "error",
        "critical",
        r"sk-ant-[A-Za-z0-9_-]{20,}",
        "sk-ant-",
    ),
    # T-0157 explicit decision: a live Stripe SECRET key is one of the two
    # patterns the ticket asks us to weigh for `_UNWAIVABLE_RULES` -- it is
    # a direct, unattenuated production-account takeover primitive with no
    # legitimate reason to ever be tracked, fake-shaped or not (a real
    # `sk_live_` value cannot be "intentionally" committed). Given its own
    # rule id `SEC003` (added to `frob.gates._UNWAIVABLE_RULES`) rather than
    # sharing `SEC001`, because `SEC001` also carries genuinely waivable,
    # lower-confidence findings (JWTs, Plaid's context-gated heuristic,
    # Stripe TEST keys) that a blanket unwaivable rule id would wrongly
    # block from ever being dismissed with a written reason.
    _pat(
        "stripe-secret-live",
        "SEC003",
        "error",
        "critical",
        r"sk_live_[A-Za-z0-9]{16,}",
        "sk_live_",
    ),
    _pat(
        "stripe-restricted-live",
        "SEC001",
        "error",
        "critical",
        r"rk_live_[A-Za-z0-9]{16,}",
        "rk_live_",
    ),
    _pat(
        "stripe-webhook",
        "SEC001",
        "error",
        "critical",
        r"whsec_[A-Za-z0-9]{16,}",
        "whsec_",
    ),
    _pat(
        "stripe-publishable-live",
        "SEC001",
        "error",
        "high",
        r"pk_live_[A-Za-z0-9]{16,}",
        "pk_live_",
    ),
    # Stripe test-mode keys: real-looking (T-0157 explicit call-out) but
    # inert against the live API, so a lower "low" label / WARN severity.
    _pat(
        "stripe-secret-test",
        "SEC001",
        "warn",
        "low",
        r"sk_test_[A-Za-z0-9]{16,}",
        "sk_test_",
    ),
    _pat(
        "stripe-publishable-test",
        "SEC001",
        "warn",
        "low",
        r"pk_test_[A-Za-z0-9]{16,}",
        "pk_test_",
    ),
    _pat(
        "openai-project",
        "SEC001",
        "error",
        "critical",
        r"sk-proj-[A-Za-z0-9_-]{20,}",
        "sk-proj-",
    ),
    # T-0219: a hyphenated `sk-live-...` shape (distinct from Stripe's
    # underscore `sk_live_` above) was silently missed -- the old
    # `openai-legacy` entry below requires 20+ alnum-ONLY chars right after
    # `sk-`, and `live-` breaks that run at its first hyphen, so a real
    # `sk-live-<hex>` token never matched ANY pattern in the table. Ordered
    # before `openai-legacy` (longer, more specific prefix) per this table's
    # most-specific-first discipline.
    _pat(
        "generic-live-key",
        "SEC001",
        "error",
        "critical",
        r"sk-live-[A-Za-z0-9-]{16,}",
        "sk-live-",
    ),
    _pat(
        "openai-legacy",
        "SEC001",
        "error",
        "critical",
        r"sk-[A-Za-z0-9]{20,}",
        "sk-",
    ),
    _pat(
        "aws-access-key-id",
        "SEC001",
        "error",
        "high",
        r"A(?:KIA|SIA)[0-9A-Z]{16}",
        "AKIA/ASIA",
    ),
    # T-0427 provider-format parity pass (docs/design/secrets-pii-corpus.md
    # A.4 row "AWS Bedrock long-lived API key"): fixed `ABSK` prefix, unlike
    # the entropy/contextual-only AWS secret access key (deliberately NOT
    # added -- see the "Deliberately OMITTED" section of this module's
    # docstring; a 40-char no-prefix base64 string is exactly the dishonest
    # entropy-fallback class this module declines to ship).
    _pat(
        "aws-bedrock-api-key",
        "SEC001",
        "error",
        "critical",
        r"ABSK[A-Za-z0-9+/]{109,}=*",
        "ABSK",
    ),
    _pat(
        "github",
        "SEC001",
        "error",
        "critical",
        r"gh[pousr]_[A-Za-z0-9]{36}",
        "ghp_/gho_/ghu_/ghs_",
    ),
    _pat(
        "github-fine-grained",
        "SEC001",
        "error",
        "critical",
        r"github_pat_[A-Za-z0-9_]{22,}",
        "github_pat_",
    ),
    _pat(
        "gitlab",
        "SEC001",
        "error",
        "high",
        r"glpat-[A-Za-z0-9_-]{20,}",
        "glpat-",
    ),
    _pat(
        "slack",
        "SEC001",
        "error",
        "high",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
        "xoxb-/xoxp-/xoxa-/xoxs-",
    ),
    _pat(
        "google",
        "SEC001",
        "error",
        "high",
        r"AIza[0-9A-Za-z_-]{35}",
        "AIza",
    ),
    _pat(
        "twilio-api-key",
        "SEC001",
        "error",
        "medium",
        r"SK[a-f0-9]{32}",
        "SK",
    ),
    _pat(
        "twilio-account-sid",
        "SEC001",
        "warn",
        "low",
        r"AC[a-f0-9]{32}",
        "AC",
    ),
    _pat(
        "sendgrid",
        "SEC001",
        "error",
        "high",
        r"SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
        "SG.",
    ),
    _pat(
        "square",
        "SEC001",
        "error",
        "high",
        r"sq0[a-z]{3}-[A-Za-z0-9_-]{22,43}",
        "sq0atp-/sq0csp-",
    ),
    # Braintree's production access token is the one PayPal-family shape
    # with a fixed, matchable literal (`access_token$production$...`); bare
    # PayPal REST client secrets have no recognizable format at all (no
    # fixed prefix, no fixed length) -- patterning them would mean matching
    # "any 32+ char opaque string", which is indistinguishable from a
    # session id, a database key, or a test fixture and would be exactly
    # the dishonest-entropy-fallback class this module's docstring already
    # declines to ship. Documented gap, not a silent omission.
    _pat(
        "braintree",
        "SEC001",
        "error",
        "high",
        r"access_token\$production\$[a-z0-9]{16}\$[a-f0-9]{32}",
        "access_token$production$",
    ),
    _pat(
        "npm",
        "SEC001",
        "error",
        "high",
        r"npm_[A-Za-z0-9]{36}",
        "npm_",
    ),
    _pat(
        "pypi",
        "SEC001",
        "error",
        "high",
        r"pypi-[A-Za-z0-9_-]{50,}",
        "pypi-",
    ),
    _pat(
        "huggingface",
        "SEC001",
        "error",
        "high",
        r"hf_[A-Za-z0-9]{34}",
        "hf_",
    ),
    # T-0427 (docs/design/secrets-pii-corpus.md A.4 "Discord bot token"):
    # the historical three-segment shape gitleaks/detect-secrets/GitHub all
    # name -- `[MN]` lead byte, base-ID segment, fixed 6-char timestamp
    # segment, 27+ char HMAC segment.
    _pat(
        "discord-bot-token",
        "SEC001",
        "error",
        "critical",
        r"[MN][A-Za-z0-9]{23,25}\.[\w-]{6}\.[\w-]{27,}",
        "<discord-bot-token>",
    ),
    # T-0427 (A.4 "MongoDB Atlas connection URI w/ credentials"): structural
    # match on the URI shape itself -- the password segment is opaque (any
    # charset), so this is "exact-pattern-matchable (structural)" per the
    # corpus tag, not an entropy check on the credential.
    _pat(
        "mongodb-atlas-uri",
        "SEC001",
        "error",
        "high",
        r"mongodb(?:\+srv)?://[^\s:/@]+:[^\s@/]+@[^\s/]+",
        "mongodb(+srv)://...:...@",
    ),
    # T-0427 (A.4 "HashiCorp Vault token"): current-generation service and
    # batch token prefixes. The legacy `s.` prefix is deliberately NOT
    # patterned here -- two literal characters is indistinguishable from
    # ordinary prose/code (`s.` appears constantly as a coincidental
    # substring) and would be exactly the false-positive-heavy class this
    # module avoids; documented gap, not a silent omission.
    _pat(
        "hashicorp-vault-service",
        "SEC001",
        "error",
        "high",
        r"hvs\.[A-Za-z0-9_-]{20,}",
        "hvs.",
    ),
    _pat(
        "hashicorp-vault-batch",
        "SEC001",
        "error",
        "high",
        r"hvb\.[A-Za-z0-9_-]{20,}",
        "hvb.",
    ),
    # Plaid has no fixed prefix either (secrets are bare 30-char hex); gated
    # on the line also mentioning "plaid" (case-insensitive) to keep the
    # false-positive class to "a hex-ish string near the word plaid" rather
    # than "any 30-char hex string anywhere" (T-0151-style honesty: the
    # context requirement IS the documented limitation, not a fix for it --
    # a plaid secret with no nearby mention of "plaid" is a false negative
    # by construction).
    _pat(
        "plaid",
        "SEC001",
        "warn",
        "medium",
        r"(?i:plaid).{0,40}\b[a-f0-9]{30}\b",
        "<context-gated>",
    ),
    # Second T-0157 `_UNWAIVABLE_RULES` candidate: a private-key PEM header
    # in a tracked file means the key material itself is very likely
    # tracked too (the header is not something anyone writes as a lone
    # comment). Same `SEC003` treatment and same reasoning as the Stripe
    # live-secret entry above.
    _pat(
        "private-key-pem",
        "SEC003",
        "error",
        "critical",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----",
        "-----BEGIN ... PRIVATE KEY-----",
    ),
    # T-0427 (A.4 "Basic-auth in URL"): generic scheme, colon-slash-slash,
    # user, colon, password, at-sign, host credential-in-URL shape (detect-
    # secrets `BasicAuthDetector`). (Written out in prose above, not as one
    # contiguous example string, so this comment does not self-trip the
    # very pattern it describes -- see `TestGateIsGreenOnItself` below.)
    # Deliberately LAST among the URL-shaped patterns (ordering discipline
    # at top of this table) -- `mongodb-atlas-uri` above is a strict subset
    # of this shape and must claim its span first, or every Mongo URI would
    # double-report under both providers.
    #
    # Host segment requires an embedded dot (`[^\s/@]+\.[^\s/@]+`) rather
    # than a bare `[^\s/]+` -- T-0427 discovery: the un-anchored version
    # matched `docs/design/secrets-pii-corpus.md`'s own prose row
    # documenting this exact provider format (a placeholder literal
    # ending in the single word "host", no dot), a real false positive on
    # an existing tracked file rather than a fixture. Requiring a dotted
    # hostname keeps the pattern honest for real URLs (which always have
    # one) while no longer tripping on bare descriptive placeholder words.
    _pat(
        "basic-auth-url",
        "SEC001",
        "warn",
        "medium",
        r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/@]+:[^\s@/]+@[^\s/@]+\.[^\s/@]+",
        "<scheme>://...:...@",
    ),
    # JWTs are frequently non-secret (public ID tokens, doc examples, test
    # fixtures embedding a third-party sample) -- "low" label / WARN, a
    # heads-up rather than a hard fail, documented false-positive class.
    _pat(
        "jwt",
        "SEC001",
        "warn",
        "low",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "eyJ",
    ),
)


# frob:doc docs/modules/gates.md#public-api
# frob:waive COV007 reason="docs/modules/gates.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:tests tests/test_secrets_gate.py::TestRedact.test_never_returns_the_token
# frob:invariant INV-039
# invariant spec: [INV-039](invariants/INV-039.md)
def _redact(token: str, display_prefix: str) -> str:
    """`<prefix>... (<N> chars)` -- the ONLY representation of a matched
    token this module (or any caller) may print, log, or persist."""
    return f"{display_prefix}... ({len(token)} chars)"


#: Shannon-entropy floor (bits/char over alnum chars) below which a
#: digit-free, single-case token is judged "human template prose" rather
#: than a real secret's random tail (T-0219 round 3 bypass fix). Calibrated
#: against the repo's own fixtures: `xoxb-insert-...-token` (an
#: existing, intentionally-suppressed legit placeholder) sits at ~3.64
#: bits/char; the reviewer's adversarial digit-free "real" tokens -- an
#: `sk-live-insert-` prefix glued to a near-unique-letter run (~4.32
#: bits/char) -- and any mixed-case token sit well above 3.7. The gap
#: between "repeats a handful of English words" and "near-unique alphabet
#: run" is wide enough that 3.7 is a conservative cut: it never needs to
#: be exact, only to never let a genuinely random-looking token read as


_LOW_ENTROPY_BITS_PER_CHAR = 3.7


def _looks_low_entropy(token: str) -> bool:
    """True if `token` reads as human-written template prose rather than a
    machine-generated secret (T-0219 round 3: replaces the round-2 binary
    "has no digits" check, which let a digit-free but high-entropy
    real-shaped token -- an `sk-live-your-` prefix glued to a mixed-case
    random tail -- still slip past).

    Three independent, conservative gates, ALL of which must hold before a
    token is ever called low-entropy -- failing any one means "not low",
    i.e. the security-safe direction (never suppress on uncertainty):

    1. No digit anywhere. A digit is decisive evidence of real secret-shaped
       content regardless of what else is true.
    2. Single case (all-lowercase or all-uppercase letters, no mixing). A
       real generated token frequently mixes case; hand-typed template
       phrases like `your-slack-token-here` never do.
    3. Real Shannon entropy over the token's alnum characters, in bits per
       character, below `_LOW_ENTROPY_BITS_PER_CHAR`. English template
       phrases repeat a small set of common letters (low entropy); a
       machine-generated token -- even a digit-free, single-case one built
       from a wide alphabet run -- has a much flatter, higher-entropy
       character distribution.

    Only reached by `_looks_fake` when `_PLACEHOLDER_PHRASE_RE` already
    matched a phrase fragment (`your-`/`insert-`/`-here`) in the token, so
    this never runs against arbitrary unrelated secrets."""
    if any(char.isdigit() for char in token):
        return False
    has_upper = any(char.isupper() for char in token)
    has_lower = any(char.islower() for char in token)
    if has_upper and has_lower:
        return False
    alnum = [char for char in token if char.isalnum()]
    if not alnum:
        return False
    counts = Counter(alnum)
    total = len(alnum)
    entropy = -sum(
        (count / total) * math.log2(count / total) for count in counts.values()
    )
    return entropy < _LOW_ENTROPY_BITS_PER_CHAR


def _looks_fake(token: str) -> bool:
    """True if `token` itself is an obvious placeholder shape (T-0157:
    XXXX/**** runs or the literal words fake/changeme/example/placeholder).

    T-0219 round 1 added obvious placeholder PHRASING (`-here` tail, or a
    `your-`/`insert-` fragment) but matched it as a bare substring against
    the whole token -- round 2 (this version) closes the resulting bypass:
    a phrase match now only counts as fake when the token is EITHER a
    known whole-token template shape (`_KNOWN_TEMPLATE_SHAPE_RE`, fullmatch)
    OR low-entropy human text containing the phrase (`_looks_low_entropy`).
    A high-entropy, real-shaped token (digits present, doesn't fullmatch
    the template shape) is NEVER suppressed by phrase content alone, no
    matter what substrings it happens to contain.

    Independent of any `frob:secret-fake` marker on the surrounding line."""
    if _PLACEHOLDER_RUN_RE.search(token):
        return True
    if _KNOWN_TEMPLATE_SHAPE_RE.fullmatch(token):
        return True
    if _looks_low_entropy(token) and _PLACEHOLDER_PHRASE_RE.search(token):
        return True
    lowered = token.lower()
    return any(word in lowered for word in _PLACEHOLDER_WORDS)


def _fake_marker_reason(lines: list[str], index: int) -> str | None:
    """The `reason="..."` text from a `frob:secret-fake reason="..."` marker
    on `lines[index]` or the line directly above it (T-0968: mirrors
    `frob:waive`'s WAIVE001 contract -- annotate a fixture on its own line or
    the comment line directly above it, same as the pre-T-0968 bare marker's
    same-line-or-line-above convention), or `None` if neither line carries a
    reason-bearing marker. A bare `frob:secret-fake` with no `reason=` no
    longer discharges anything -- see `_bare_fake_marker_violations`/SEC004."""
    match = _FAKE_MARKER_REASON_RE.search(lines[index])
    if match is not None:
        return match.group(1)
    if index > 0:
        match = _FAKE_MARKER_REASON_RE.search(lines[index - 1])
        if match is not None:
            return match.group(1)
    return None


# frob:waive DEAD001 reason="genuinely called directly from src/frob/gates/_secrets.py \
# and src/frob/app/telemetry.py, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _scan_line(
    lines: list[str], index: int, *, ignore_marker: bool = False
) -> list[tuple[_SecretPattern, str]]:
    """Every `(pattern, token)` hit on `lines[index]` not already claimed by
    an earlier (more specific) pattern's span, and not fake-marked.

    T-0968: a fake-marked line only discharges via a REASON-bearing
    `frob:secret-fake reason="..."` (`_fake_marker_reason`) -- a bare marker
    is surfaced separately as SEC004 (`_bare_fake_marker_violations`) and no
    longer suppresses anything here.

    T-0978: `ignore_marker=True` disregards any `frob:secret-fake` reason on
    this line entirely (as if the marker were absent) while still applying
    every other filter (`_looks_fake`, claimed-span dedup) -- used only by
    `_would_trip_without_marker` to test whether a marker's site would still
    produce a real hit, never to decide whether to emit a live finding."""
    line = lines[index]
    claimed: list[tuple[int, int]] = []
    hits: list[tuple[_SecretPattern, str]] = []
    reason = None if ignore_marker else _fake_marker_reason(lines, index)
    for pattern in _PATTERNS:
        for match in pattern.regex.finditer(line):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in claimed):
                continue
            token = match.group(0)
            if _looks_fake(token) or reason is not None:
                _log.debug(
                    "secrets: %s match at line %d fake-marked (reason=%r)/"
                    "placeholder, skipping",
                    pattern.provider,
                    index + 1,
                    reason,
                )
                continue
            claimed.append(span)
            hits.append((pattern, token))
    return hits
