"""SEC001/SEC002/SEC003: real-looking API tokens and credentials in tracked
files (docs/modules/gates.md#rule-catalog).

Scope decision on `frob:secret` (T-0157, investigated before writing this
module): `frob.graph.dsl`'s `frob:secret <construct-id>` verb already has an
established, different meaning -- it binds a code site to a strata design's
Secret-clearance `Node` id (`frob.strata._design_load`), consumed by
`SYS001`/`SYS002` to prove every design secret has a code attestation.
Reusing that SAME directive for "this literal string is a fake credential"
would (a) mint a bogus `EdgeKind.SECRET` edge whose target ("fake") is never
a real design construct id, which SYS001 would then flag as a dangling
reference in any repo with a `design/` directory (this repo has one), and
(b) conflate two unrelated concerns (design attestation vs. fixture
fake-marking) under one verb. Instead this module recognizes a sibling,
unregistered marker -- the literal substring `frob:secret-fake` -- scanned
directly out of tracked-file text, never routed through `frob.graph.dsl`'s
`_VERB_TABLE` and never turned into a graph edge. It keeps the "secret"
vocabulary (same family, same intent: mark a secret-shaped site) without
colliding with the pre-existing directive's semantics.

Redaction discipline: `_redact` NEVER returns the matched token itself, only
`<provider> <fixed-prefix>... (<N> chars)`. Every violation message and log
line MUST go through it -- this is the whole point of the gate; a leaked
scanner is worse than no scanner.

Providers deliberately covered by a real, testable pattern (T-0157's
per-provider mandate; extended toward provider-format parity by T-0427):
Anthropic, OpenAI, Stripe (live+test, secret+restricted+publishable+
webhook), AWS access key ids, AWS Bedrock long-lived API keys, GitHub,
GitLab, Slack, Google, Twilio, SendGrid, Square, Braintree/PayPal (via
Braintree's fixed `access_token$production$` shape -- see `_PATTERNS`
comment for why bare PayPal secrets are NOT patterned), npm, PyPI,
HuggingFace, Discord bot tokens, MongoDB Atlas connection URIs, HashiCorp
Vault service/batch tokens, generic basic-auth-in-URL credentials, Plaid
(context-gated, see comment), PEM private-key headers, and a JWT header
heuristic.

Deliberately OMITTED: a generic Shannon-entropy fallback. This repo alone
carries content-hash digests, git shas, UUIDs, and base64 test fixtures
throughout `.frob/` and `tests/fixtures/**`; an entropy trigger tuned loose
enough to catch real secrets is also loose enough to fire on all of those,
which is the exact "dishonest gate" T-0151 documents -- so it is left out
rather than half-built. A future ticket could revisit this with a properly
tuned, context-aware entropy pass; until then the pattern table is the
whole detector. Same reasoning excludes several more `docs/design/
secrets-pii-corpus.md` A.4 rows even after T-0427's parity pass: AWS
secret access keys (40-char no-prefix base64), Azure Storage Account keys
(88-char no-prefix base64) and Azure AD/Entra client secrets (opaque,
context-only), and the generic keyword+entropy "API key" rule -- all
tagged "entropy-heuristic + contextual" in that corpus, none has a fixed,
matchable prefix, and generic-shaped `_scan_line` matching would be the
same false-positive class this module already declines. GCP service-
account JSON keys are NOT separately patterned either: the structural
signal that actually distinguishes the JSON blob (its embedded PEM
`private_key` field) already fires the existing `private-key-pem` pattern
line-by-line, so a dedicated whole-document JSON pattern would be a
redundant detector for the same underlying leak. (`_looks_low_entropy`,
added T-0219, is NOT that fallback:
it never fires a violation, only narrows an existing phrase-based
SUPPRESSION so it can't be bypassed -- a different, much lower-stakes use
of entropy than a detection trigger would be.)

Also honest about: this scanner is line-oriented (each tracked line is
matched independently), so a token that has been line-wrapped -- split
across two physical lines by an editor, formatter, or manual line break --
will not match any pattern and will silently pass. Documented gap, not a
silent omission.
"""

# frob:ticket T-0157
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

#: The unregistered, graph-invisible fake-marker (T-0157 decision above).
#: Recognized on the matched line itself OR the line immediately before it,
#: so a `# frob:secret-fake` comment above a fixture line still discharges it.
_FAKE_MARKER = "frob:secret-fake"

#: Placeholder shapes inside a token that make it obviously non-real
#: regardless of provider (T-0157: "so docs and tests stay writable").
#: Checked case-insensitively against the matched token text only, never
#: the whole line (a real key sitting next to the word "example" in prose
#: must still fire).
_PLACEHOLDER_WORDS = ("fake", "changeme", "example", "placeholder")
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
# frob:waive COV007 reason="docs/guides/extending/secrets-scan-providers.md \
# is a whole guide dedicated to this private dataclass, frob:describes-\
# anchored at its own top heading (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
class _SecretPattern:
    """One provider's detection rule: what to match, how bad it is, and how
    much of the match is safe to print back in a violation message."""

    provider: str
    rule: str
    severity: Severity
    label: str  # "critical" / "high" / "medium" / "low" -- printed in the message
    regex: re.Pattern[str]
    display_prefix: str  # the fixed literal shown in redacted output


def _pat(
    provider: str,
    rule: str,
    severity: Severity,
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
        Severity.ERROR,
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
        Severity.ERROR,
        "critical",
        r"sk_live_[A-Za-z0-9]{16,}",
        "sk_live_",
    ),
    _pat(
        "stripe-restricted-live",
        "SEC001",
        Severity.ERROR,
        "critical",
        r"rk_live_[A-Za-z0-9]{16,}",
        "rk_live_",
    ),
    _pat(
        "stripe-webhook",
        "SEC001",
        Severity.ERROR,
        "critical",
        r"whsec_[A-Za-z0-9]{16,}",
        "whsec_",
    ),
    _pat(
        "stripe-publishable-live",
        "SEC001",
        Severity.ERROR,
        "high",
        r"pk_live_[A-Za-z0-9]{16,}",
        "pk_live_",
    ),
    # Stripe test-mode keys: real-looking (T-0157 explicit call-out) but
    # inert against the live API, so a lower "low" label / WARN severity.
    _pat(
        "stripe-secret-test",
        "SEC001",
        Severity.WARN,
        "low",
        r"sk_test_[A-Za-z0-9]{16,}",
        "sk_test_",
    ),
    _pat(
        "stripe-publishable-test",
        "SEC001",
        Severity.WARN,
        "low",
        r"pk_test_[A-Za-z0-9]{16,}",
        "pk_test_",
    ),
    _pat(
        "openai-project",
        "SEC001",
        Severity.ERROR,
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
        Severity.ERROR,
        "critical",
        r"sk-live-[A-Za-z0-9-]{16,}",
        "sk-live-",
    ),
    _pat(
        "openai-legacy",
        "SEC001",
        Severity.ERROR,
        "critical",
        r"sk-[A-Za-z0-9]{20,}",
        "sk-",
    ),
    _pat(
        "aws-access-key-id",
        "SEC001",
        Severity.ERROR,
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
        Severity.ERROR,
        "critical",
        r"ABSK[A-Za-z0-9+/]{109,}=*",
        "ABSK",
    ),
    _pat(
        "github",
        "SEC001",
        Severity.ERROR,
        "critical",
        r"gh[pousr]_[A-Za-z0-9]{36}",
        "ghp_/gho_/ghu_/ghs_",
    ),
    _pat(
        "github-fine-grained",
        "SEC001",
        Severity.ERROR,
        "critical",
        r"github_pat_[A-Za-z0-9_]{22,}",
        "github_pat_",
    ),
    _pat(
        "gitlab",
        "SEC001",
        Severity.ERROR,
        "high",
        r"glpat-[A-Za-z0-9_-]{20,}",
        "glpat-",
    ),
    _pat(
        "slack",
        "SEC001",
        Severity.ERROR,
        "high",
        r"xox[baprs]-[A-Za-z0-9-]{10,}",
        "xoxb-/xoxp-/xoxa-/xoxs-",
    ),
    _pat(
        "google",
        "SEC001",
        Severity.ERROR,
        "high",
        r"AIza[0-9A-Za-z_-]{35}",
        "AIza",
    ),
    _pat(
        "twilio-api-key",
        "SEC001",
        Severity.ERROR,
        "medium",
        r"SK[a-f0-9]{32}",
        "SK",
    ),
    _pat(
        "twilio-account-sid",
        "SEC001",
        Severity.WARN,
        "low",
        r"AC[a-f0-9]{32}",
        "AC",
    ),
    _pat(
        "sendgrid",
        "SEC001",
        Severity.ERROR,
        "high",
        r"SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
        "SG.",
    ),
    _pat(
        "square",
        "SEC001",
        Severity.ERROR,
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
        Severity.ERROR,
        "high",
        r"access_token\$production\$[a-z0-9]{16}\$[a-f0-9]{32}",
        "access_token$production$",
    ),
    _pat(
        "npm",
        "SEC001",
        Severity.ERROR,
        "high",
        r"npm_[A-Za-z0-9]{36}",
        "npm_",
    ),
    _pat(
        "pypi",
        "SEC001",
        Severity.ERROR,
        "high",
        r"pypi-[A-Za-z0-9_-]{50,}",
        "pypi-",
    ),
    _pat(
        "huggingface",
        "SEC001",
        Severity.ERROR,
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
        Severity.ERROR,
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
        Severity.ERROR,
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
        Severity.ERROR,
        "high",
        r"hvs\.[A-Za-z0-9_-]{20,}",
        "hvs.",
    ),
    _pat(
        "hashicorp-vault-batch",
        "SEC001",
        Severity.ERROR,
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
        Severity.WARN,
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
        Severity.ERROR,
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
        Severity.WARN,
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
        Severity.WARN,
        "low",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "eyJ",
    ),
)

# frob:doc docs/modules/gates.md#public-api
#: Every provider name flagged "critical"; informational only (the actual
#: unwaivable-or-not decision is per-rule-id, `SEC003` vs `SEC001` above,
#: not derived from this set -- see the `stripe-secret-live`/
#: `private-key-pem` pattern comments and `frob.gates._UNWAIVABLE_RULES`).
CRITICAL_PROVIDERS = frozenset(p.provider for p in _PATTERNS if p.label == "critical")

# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_secrets_gate.py::TestDriftLock.test_every_provider_has_a_fixture
#: Drift-lock source of truth: every provider name that MUST have a
#: corresponding test fixture (T-0157's drift-lock requirement).
ALL_PROVIDERS: frozenset[str] = frozenset(p.provider for p in _PATTERNS)


# frob:doc docs/modules/gates.md#public-api
# frob:waive COV007 reason="docs/modules/gates.md's Public API section \
# individually frob:describes this private helper by name (T-0529) -- a \
# deliberate architecture doc, not accidental drift onto a private helper"
# frob:tests tests/test_secrets_gate.py::TestRedact.test_never_returns_the_token
# frob:invariant INV-039
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
#: low.
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


def _line_marks_fake(lines: list[str], index: int) -> bool:
    """True if `lines[index]` or `lines[index - 1]` carries the
    `frob:secret-fake` marker (T-0157: annotate a fixture on its own line
    or the comment line directly above it)."""
    if _FAKE_MARKER in lines[index]:
        return True
    if index > 0 and _FAKE_MARKER in lines[index - 1]:
        return True
    return False


def _scan_line(lines: list[str], index: int) -> list[tuple[_SecretPattern, str]]:
    """Every `(pattern, token)` hit on `lines[index]` not already claimed by
    an earlier (more specific) pattern's span, and not fake-marked."""
    line = lines[index]
    claimed: list[tuple[int, int]] = []
    hits: list[tuple[_SecretPattern, str]] = []
    for pattern in _PATTERNS:
        for match in pattern.regex.finditer(line):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in claimed):
                continue
            token = match.group(0)
            if _looks_fake(token) or _line_marks_fake(lines, index):
                _log.debug(
                    "secrets: %s match at line %d fake-marked/placeholder, skipping",
                    pattern.provider,
                    index + 1,
                )
                continue
            claimed.append(span)
            hits.append((pattern, token))
    return hits


def _secret_violation(
    pattern: _SecretPattern, token: str, rel_path: str, index: int
) -> Violation:
    """The SEC001 `Violation` for one real-looking-token hit at 1-based `index + 1`."""
    redacted = _redact(token, pattern.display_prefix)
    _log.warning(
        "%s: %s (%s) real-looking token at %s:%d",
        pattern.rule,
        pattern.provider,
        pattern.label,
        rel_path,
        index + 1,
    )
    return Violation(
        rule=pattern.rule,
        severity=pattern.severity,
        file=rel_path,
        line=index + 1,
        message=(
            f"{pattern.rule}: {pattern.provider} ({pattern.label}) "
            f"real-looking credential at {rel_path}:{index + 1} -- "
            f"{redacted}; if this "
            f"is a deliberate test fixture, mark it fake (placeholder "
            f"XXXX/**** tail, the word fake/changeme/example/placeholder "
            f"in the token, or a `frob:secret-fake` comment on this line "
            f"or the line above), otherwise rotate and remove it"
        ),
    )


def _scan_text(rel_path: str, text: str) -> list[Violation]:
    """SEC001 violations for every real-looking token found in `text`."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for index in range(len(lines)):
        for pattern, token in _scan_line(lines, index):
            violations.append(_secret_violation(pattern, token, rel_path, index))
    return violations


def _env002_violation(rel_path: str) -> Violation:
    """SEC002: a tracked `.env` file -- a critical finding by itself (T-0157:
    "a TRACKED .env file is itself a critical finding"), independent of
    whether any of its contents also match SEC001."""
    _log.warning("SEC002: tracked .env file at %s", rel_path)
    return Violation(
        rule="SEC002",
        severity=Severity.ERROR,
        file=rel_path,
        line=0,
        message=(
            f"SEC002: {rel_path} is a git-tracked .env file; .env files are "
            f"write-once local secrets and must never be committed -- "
            f"git rm --cached {rel_path} and add it to .gitignore"
        ),
    )


def _is_env_file(rel_path: str) -> bool:
    """True for `.env` and `.env.*` (`.env.local`, `.env.production`, ...),
    matching the common dotenv naming family; `.env.example`/`.env.sample`
    are conventional placeholder templates and are excluded."""
    name = rel_path.rsplit("/", 1)[-1]
    if name in (".env.example", ".env.sample", ".env.template"):
        return False
    return name == ".env" or name.startswith(".env.")


def _tracked_files(root: Path) -> tuple[str, ...]:
    """`git ls-files` under `root`, root-relative POSIX paths, `()` on any
    git failure (no repo, git missing) -- mirrors `frob.gitio`'s
    degrade-don't-crash posture for git subprocess calls (same `run_argv`
    seam `frob.gates` already uses elsewhere, e.g. `_changelog_mentions`)."""
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.error("secrets_gate: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.error("secrets_gate: git ls-files exited %d", result.returncode)
        return ()
    files = tuple(line for line in result.stdout.splitlines() if line.strip())
    _log.debug("secrets_gate: %d tracked file(s)", len(files))
    return files


# frob:doc docs/modules/gates.md#public-api
# frob:tests tests/test_secrets_gate.py::TestFindsTokens.test_stripe_live_key_sec003
# frob:tests tests/test_secrets_gate.py::TestFakeMarking.test_fake_marker_same_line
# frob:tests tests/test_secrets_gate.py::TestTrackedEnvFile.test_env_file_sec002
# frob:tests tests/test_secrets_gate.py::TestGateIsGreenOnItself.test_repo_is_clean
# frob:enforces SEC-SECRETS-SECRETS-DETECT_SECRETS_PLUGINS
# frob:enforces SEC-SECRETS-SECRETS-PROVIDER_TOKEN_FORMATS
# frob:enforces CHK-GATE-SEC001
# frob:enforces CHK-GATE-SEC002
# frob:enforces CHK-GATE-SEC003
def secrets_gate(root: Path) -> tuple[Violation, ...]:
    """SEC001/SEC002/SEC003 (docs/modules/gates.md#rule-catalog): every
    git-tracked file scanned for real-looking provider credentials, plus a
    standalone check for a tracked `.env`. Never touches untracked files
    (git ls-files only) and never echoes a matched token -- see `_redact`."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _tracked_files(root):
        if _is_env_file(rel_path):
            violations.append(_env002_violation(rel_path))
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            _log.debug("secrets_gate: skipping unreadable/binary %s", rel_path)
            continue
        scanned += 1
        violations.extend(_scan_text(rel_path, text))

    _log.info(
        "secrets_gate: scanned %d tracked file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = [
    "ALL_PROVIDERS",
    "CRITICAL_PROVIDERS",
    "_redact",
    "secrets_gate",
]
