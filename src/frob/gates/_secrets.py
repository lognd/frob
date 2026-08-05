"""SEC001/SEC002/SEC003/SEC004: real-looking API tokens and credentials in
tracked files (docs/modules/gates.md#rule-catalog).

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
unregistered marker -- the literal substring `frob:secret-fake reason="..."`
-- scanned directly out of tracked-file text, never routed through
`frob.graph.dsl`'s `_VERB_TABLE` and never turned into a graph edge. It
keeps the "secret" vocabulary (same family, same intent: mark a
secret-shaped site) without colliding with the pre-existing directive's
semantics.

T-0968 (gates-quality audit finding 3): the marker now REQUIRES
`reason="..."` to discharge anything, mirroring `frob:waive`'s WAIVE001
contract (a bare marker gets its own SEC004 violation instead of silently
discharging for free -- see `_bare_fake_marker_violations`). It still is
NOT a graph `WAIVE` edge (the T-0157 decision above stands -- `secret-fake`
stays a reserved, DSL-invisible marker verb, `frob.graph.dsl.
_RESERVED_MARKER_VERBS`), so it is not watched by the graph-edge `WAIVE004`
zero-findings staleness gate (`frob.gates._waive004_violations` iterates
real `frob:waive` edges only); it is auditable the same WAY `frob:waive` is
(a mandatory, logged, per-site reason), not literally the same mechanism.

T-0978: zero-findings staleness for this marker family IS now wired in --
at the GATE level, not the graph-edge level, per T-0157's constraint above
(promoting `secret-fake` into a real graph edge stays out of scope; this
module remains the sole owner of its detection logic).
`fake_marker_staleness_gate` re-scans every tracked file's REAL
(non-prose, non-bare) `frob:secret-fake reason="..."` marker sites and
emits a `WAIVE004`-rule `Violation` for any whose site trips zero real
secret-pattern hits this run (`_stale_fake_marker_violations`,
`_would_trip_without_marker`) -- the same "zero live findings behind a
still-standing suppression" shape `frob.gates._waive004_violations` checks
for `frob:waive` edges, computed independently since there is no edge to
iterate. `frob.gates.__init__` folds this gate's output into the same
`all_violations` set the graph-edge WAIVE004 detector feeds, so both
sources present as one `WAIVE004` rule to a caller.

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
# frob:ticket T-1318
from __future__ import annotations

import bisect
import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _shared_tracked_files
from frob.logging import get_logger
from frob.security._redact import (
    _FAKE_MARKER_REASON_RE,
    _PATTERNS,
    _redact,
    _scan_line,
    _SecretPattern,
)

_log = get_logger(__name__)

#: The unregistered, graph-invisible fake-marker (T-0157 decision above).
#: Recognized on the matched line itself OR the line immediately before it,
#: so a `# frob:secret-fake` comment above a fixture line still discharges it.

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

# T-1211 (perf report candidate #6): find which line indices in a file's
# text could possibly contain a hit (`_candidate_line_indices`) with 33
# whole-FILE `finditer` calls (one per `_PATTERNS` entry) instead of 33
# compiled patterns x `finditer` per PHYSICAL LINE (544k lines measured x 33
# patterns = ~18M `finditer` calls, ~94% of the gate's wall time -- the cost
# is Python-level per-call/regex-engine-setup overhead multiplied 544k-fold,
# not the character-scanning itself).
#
# A single COMBINED alternation regex (`(?P<p0>...)|(?P<p1>...)|...`) was
# tried first and measured SLOWER end-to-end (~19s vs. ~4.4s baseline on this
# repo's own tree) -- confirmed empirically, not assumed. Python's `re`
# engine has no shared-prefix/Aho-Corasick optimization across alternation
# branches; a single compiled pattern's literal-prefix fast path (the actual
# source of `finditer`'s per-pattern speed) is defeated the moment 33
# unrelated literal prefixes are OR'd into one pattern, so scanning the whole
# file with one combined regex tries all 33 branches at every character
# position instead of skipping ahead via one literal's own prefix scan.
# Keeping `_PATTERNS` as 33 SEPARATE compiled regexes, each run once over the
# whole file text (33 calls total, not 33 x line-count), preserves each
# pattern's own prefix optimization while still cutting `finditer` call
# count by ~5 orders of magnitude versus the per-line loop.
#
# None of `_PATTERNS` uses MULTILINE/DOTALL, and every char class that could
# otherwise cross a line (`.`, `\s`) is either bounded by `.`'s default
# no-newline-match semantics or is a NEGATED class excluding `\s` (hence
# `\n`) -- so a match's span can never straddle two physical lines, and
# mapping a match start offset to its containing line via `_line_offsets`/
# `bisect` is exact, not an approximation. The actual per-line claim/
# precedence/fake-marker logic is UNCHANGED and still runs, verbatim, via
# `_scan_line` -- only for the (rare) candidate lines this pre-pass
# identifies, never for a line with zero possible hits. This keeps findings
# byte-identical to the pre-T-1211 per-line-per-pattern loop while skipping
# the ~94% of lines that can never produce a violation.


# frob:ticket T-1211
def _line_offsets(text: str) -> list[int]:
    """Cumulative character offset (0-based) of the START of each physical
    line in `text`, `splitlines(keepends=True)`-derived so it agrees exactly
    with `text.splitlines()`'s own line boundaries (T-1211)."""
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


# frob:ticket T-1211
def _candidate_line_indices(text: str) -> list[int]:
    """0-based indices, ascending, of every physical line in `text` that at
    least one `_PATTERNS` entry matches (T-1211) -- the set of lines worth
    handing to `_scan_line`'s real per-pattern logic. A line absent from this
    list is provably a zero-hit line under every pattern in `_PATTERNS`, so
    skipping it changes nothing about the findings, only how much per-line
    work runs to reach them. Runs each of the 33 `_PATTERNS` regexes ONCE
    over the whole file text (33 `finditer` calls total) rather than once per
    physical line -- see the module-level comment above this function for
    why a single combined-alternation regex was tried and measured slower."""
    if not text:
        return []
    offsets = _line_offsets(text)
    indices: set[int] = set()
    for pattern in _PATTERNS:
        for match in pattern.regex.finditer(text):
            indices.add(bisect.bisect_right(offsets, match.start()) - 1)
    return sorted(indices)


# frob:doc docs/modules/gates.md#public-api
# frob:waive COV007 reason="docs/modules/gates.md's Public API section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
# frob:tests tests/test_secrets_gate.py::TestRedact.test_never_returns_the_token
# frob:invariant INV-039
# invariant spec: [INV-039](invariants/INV-039.md)
#: low.




def _sec004_violation(rel_path: str, lineno: int) -> Violation:
    """SEC004 (T-0968): a `frob:secret-fake` marker with no `reason="..."`
    attribute -- mirrors WAIVE001's malformed-`frob:waive` contract so a
    fake-marked fixture is auditable (who vouched for it, and why) the same
    way a `frob:waive` suppression already is."""
    _log.warning("SEC004: %s:%d frob:secret-fake missing reason=", rel_path, lineno)
    return Violation(
        rule="SEC004",
        severity=Severity.ERROR,
        file=rel_path,
        line=lineno,
        message=(
            f'SEC004: {rel_path}:{lineno} frob:secret-fake missing reason="..."; '
            f'add a reason attribute (e.g. `frob:secret-fake reason="fabricated '
            f'test fixture value\\"`) or remove the marker -- a bare '
            f"`frob:secret-fake` no longer discharges any secrets finding"
        ),
    )


#: An ACTUAL `frob:secret-fake` directive usage (a real comment marker),
#: never a backtick-quoted prose MENTION of the marker's name (this module's
#: own docstrings and this file's tests reference the literal marker text
#: constantly, e.g. "a `# frob:secret-fake` comment above ..."). The negative
#: lookbehind on the comment leader excludes exactly that backtick-adjacent
#: case: a real directive's `#`/`//` is never itself preceded by a backtick,
#: only a prose reference to it inside Markdown-style inline code is.
_BARE_FAKE_DIRECTIVE_RE = re.compile(r"(?<!`)(?:#|//)\s*frob:secret-fake\b")


def _bare_fake_marker_violations(rel_path: str, text: str) -> list[Violation]:
    """SEC004 for every REAL `frob:secret-fake` marker in `text` missing its
    `reason="..."` attribute -- surfaced independently of whether the marker
    is currently sitting next to a real secrets-pattern hit (T-0968: mirrors
    `_waive001_violations`, which flags a malformed `frob:waive` the same
    way regardless of whether it would have matched anything). Uses
    `_BARE_FAKE_DIRECTIVE_RE`, not a bare substring test, so a docstring/
    comment merely NAMING the marker (this module's own docstrings do this
    constantly) is never mistaken for an actual malformed directive."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for index, line in enumerate(lines):
        if _BARE_FAKE_DIRECTIVE_RE.search(line) is None:
            continue
        if _FAKE_MARKER_REASON_RE.search(line) is not None:
            continue
        violations.append(_sec004_violation(rel_path, index + 1))
    return violations


#: A REAL, reason-bearing `frob:secret-fake` marker (as opposed to a prose
#: MENTION of the marker inside this module's own docstrings/messages, which
#: use the identical `frob:secret-fake reason="..."` substring constantly --
#: see `_BARE_FAKE_DIRECTIVE_RE`'s comment for the same hazard on the bare
#: form). T-0978: this is the enumeration regex for the staleness check
#: only (`_stale_fake_marker_violations`); the loose, comment-leader-free
#: `_FAKE_MARKER_REASON_RE` above stays exactly as-is for the actual
#: discharge decision inside `_scan_line`/`_fake_marker_reason` -- changing
#: that regex's matching behavior is outside this ticket's scope.
#:
#: T-0978 second false-positive class (found while writing this ticket's
#: own tests, not theoretical): a *test* file that constructs a fixture's
#: marker text as a Python string literal argument -- e.g. this module's own
#: test suite writes `'# frob:secret-fake reason="..."\n'` as one argument
#: to `write_text` -- contains that exact substring in ITS OWN tracked
#: source, with a real `#`/`//` immediately before it, so the backtick-only
#: exclusion above is not enough; the whole line IS that string literal, so
#: there is no unrelated real secret token nearby in that SOURCE line for
#: `_would_trip_without_marker` to find, and every such literal would
#: misread as a stale marker. The additional `['"]`-preceded exclusion below
#: closes this: a `#`/`//` immediately preceded by a quote character is
#: inside a string literal being constructed, not a real standalone/inline
#: comment directive, and is excluded the same way the backtick case is.
_REAL_FAKE_MARKER_REASON_RE = re.compile(
    '(?<![\'"`])(?:#|//)\\s*frob:secret-fake\\s+reason="([^"]*)"'
)


#: T-0968's own docstring notes this marker family is SHARED between
#: `secrets_gate` (SEC00x) and `frob.gates._pii_structural`'s PII011
#: (email-shaped literal) detector -- confirmed empirically while building
#: this staleness check: every real, single-physical-line
#: `frob:secret-fake reason="..."` marker actually present in this repo's
#: own tracked test suite today (a dozen-plus sites) protects a fabricated
#: git identity EMAIL, not a SEC00x-shaped token, so checking SEC00x
#: patterns alone (`_would_trip_without_marker`) misreads every one of
#: them as stale. Replicating PII011's real AST-based `_is_email_shaped`
#: check here would require importing `frob.gates._pii_structural`
#: internals, outside this ticket's declared scope
#: (src/frob/graph/dsl.py, src/frob/gates/__init__.py,
#: src/frob/gates/_secrets.py, tests/**) -- a plain email-shape substring
#: heuristic is used instead, deliberately erring toward "plausibly still
#: needed" (never flagging staleness) on any uncertain match, the same
#: safe-direction posture `_looks_low_entropy` documents for the opposite
#: (never-suppress) case. A real PII011-aware staleness check is a natural
#: follow-up once frob.gates._pii_structural exposes a public seam for it.
_PLAUSIBLE_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _would_trip_without_marker(lines: list[str], index: int) -> bool:
    """True if `lines[index]` still contains at least one real-looking
    (non-placeholder) secret token, disregarding any `frob:secret-fake`
    marker that would otherwise discharge it (T-0978: the staleness
    predicate -- "does this site still need the marker it carries").
    Delegates to `_scan_line(..., ignore_marker=True)` rather than
    re-implementing the pattern-matching loop."""
    return bool(_scan_line(lines, index, ignore_marker=True))


def _plausibly_still_needed(lines: list[str], index: int) -> bool:
    """True if `lines[index]` either still trips a real SEC00x pattern
    (`_would_trip_without_marker`) or looks email-shaped
    (`_PLAUSIBLE_EMAIL_RE`, a conservative stand-in for PII011's real
    structural check -- see that constant's comment for why). Either one
    means the marker's site is not stale."""
    return (
        _would_trip_without_marker(lines, index)
        or _PLAUSIBLE_EMAIL_RE.search(lines[index]) is not None
    )


#: T-0978: files where a `frob:secret-fake reason="..."` marker sighting is
#: source-level test DATA -- built as a Python string-literal fragment that
#: itself, in this file's OWN tracked source, spans multiple physical
#: lines (concatenated/`+`-joined or embedded inside one multi-line `src =
#: (...)` literal) -- rather than a real, single-physical-line directive
#: comment sitting next to the content it discharges. This staleness check
#: is inherently physical-line-based (mirrors `_fake_marker_reason`'s own
#: same-line-or-line-below convention, which the real, non-staleness
#: discharge path also uses), so it cannot tell "this IS the real marker
#: line for a real fixture" from "this is one fragment of test-authored
#: string data that merely CONTAINS marker-shaped text, whose actual
#: 'content' fragment lives on a different physical source line entirely".
#: Confirmed empirically (not theoretical) while building this feature:
#: every site below produced a false "stale" WAIVE004 finding against a
#: perfectly live, intentional test fixture. Excluded by file, the same
#: precedent `TestGateIsGreenOnItself._LEDGER_NARRATIVE_FILES` and
#: `frob.gates._pii_structural._SELF_EXCLUDED_FILES` already set for this
#: exact class of scanner/test-fixture self-collision.
_STALENESS_MULTILINE_LITERAL_EXCLUDED_FILES = frozenset(
    {
        "tests/test_secrets_gate.py",
        "tests/test_pii_structural_gate.py",
        "tests/unit/graph/test_dsl.py",
    }
)


def _stale_fake_marker_violations(rel_path: str, text: str) -> list[Violation]:
    """WAIVE004 (T-0978): a REAL, reason-bearing `frob:secret-fake` marker
    whose discharged site(s) -- the marker's own line, and/or the line
    directly below it (mirrors `_fake_marker_reason`'s same-line-or-line-
    below discharge convention, read from the marker's own position rather
    than the content line's) -- trip ZERO real secret-pattern hits (SEC00x)
    or plausible PII011-shaped content (`_plausibly_still_needed`) this run.

    This is `frob.gates._waive004_violations`'s zero-findings staleness
    check, reimplemented for this marker family specifically because
    `frob:secret-fake` is a reserved, graph-invisible verb
    (`frob.graph.dsl._RESERVED_MARKER_VERBS`, T-0157) that never becomes a
    real `frob:waive` `Edge` -- so the graph-edge detector
    (`frob.gates._waive004_violations`) cannot see it at all. Emits the same
    `WAIVE004` rule id/severity so both staleness sources read as one gate
    to a caller, per this ticket's "wire into WAIVE004" mandate; the
    finding text names the marker family so it is not mistaken for a real
    `frob:waive` edge when read.

    Skips `_STALENESS_MULTILINE_LITERAL_EXCLUDED_FILES` -- see that
    constant's comment."""
    if rel_path in _STALENESS_MULTILINE_LITERAL_EXCLUDED_FILES:
        return []
    lines = text.splitlines()
    violations: list[Violation] = []
    for index, line in enumerate(lines):
        match = _REAL_FAKE_MARKER_REASON_RE.search(line)
        if match is None:
            continue
        reason = match.group(1)
        targets = [index]
        if index + 1 < len(lines):
            targets.append(index + 1)
        # frob:waive PERF008 reason="_plausibly_still_needed only reads lines[index] \
        # (an in-memory list already held by this call) and runs a regex match; it \
        # performs no I/O of any kind. PERF008's resolver claims a transitive \
        # walk_pruned/fs-walk effect here by name-only coincidence through an \
        # unrelated call elsewhere in the repo -- a resolver ambiguity, not a real \
        # fs-walk. Tracked as a resolver precision follow-up \
        # (T-1041's Done report)"  # noqa: E501
        if any(_plausibly_still_needed(lines, target) for target in targets):
            continue
        lineno = index + 1
        _log.warning(
            "WAIVE004: %s:%d frob:secret-fake reason=%r matches 0 findings this run",
            rel_path,
            lineno,
            reason,
        )
        violations.append(
            Violation(
                rule="WAIVE004",
                severity=Severity.WARN,
                file=rel_path,
                line=lineno,
                message=(
                    f"WAIVE004: {rel_path}:{lineno} frob:secret-fake "
                    f"reason={reason!r} matches 0 secret findings in this "
                    f"run -- the marker may be pre-forgiving a future "
                    f"regression with no live secret-shaped token behind "
                    f"it; confirm the site still needs it, or remove the "
                    f"marker (known-flaky for a scoped/`--only`-excluded "
                    f"run; trust this only from a full, unscoped `secrets` "
                    f"gate run)"
                ),
            )
        )
    return violations


# frob:doc docs/modules/gates.md#public-api
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling so one bad file cannot abort the whole staleness pass; the documented WAIVE004 behavior is unchanged, so docs/modules/gates.md#public-api needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def fake_marker_staleness_gate(root: Path) -> tuple[Violation, ...]:
    """WAIVE004 (T-0978): every git-tracked file's `frob:secret-fake
    reason="..."` marker sites that currently discharge zero real secret
    findings -- the gate-level staleness check for this marker family (see
    `_stale_fake_marker_violations` for the "why gate-level, not graph-edge"
    rationale). Mirrors `secrets_gate`'s own tracked-file/read-text posture
    exactly (git-tracked files only, unreadable/binary files skipped)."""
    root = Path(root)
    violations: list[Violation] = []
    for rel_path in _shared_tracked_files(root, caller="secrets_gate"):
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            _log.debug("secrets_gate: skipping unreadable/binary %s", rel_path)
            continue
        try:
            violations.extend(_stale_fake_marker_violations(rel_path, text))
        except Exception:
            # One file's marker text being surprising must not abort the
            # WAIVE004 staleness pass over every OTHER tracked file
            # (EXHAUST001/EXHAUST002, T-1371).
            _log.debug("fake_marker_staleness_gate: skipping unparseable %s", rel_path)
    return tuple(violations)




# frob:enforces CWE-798
# T-0684: weaknesses.yaml's CWE-798 (Use of Hard-coded Credentials) is
# handled_by:SEC001 -- this is the emitting site.
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
        severity=Severity(pattern.severity),
        file=rel_path,
        line=index + 1,
        message=(
            f"{pattern.rule}: {pattern.provider} ({pattern.label}) "
            f"real-looking credential at {rel_path}:{index + 1} -- "
            f"{redacted}; if this "
            f"is a deliberate test fixture, mark it fake (placeholder "
            f"XXXX/**** tail, the word changeme/placeholder in the token, "
            f'or a `frob:secret-fake reason="..."` comment on this line '
            f"or the line above), otherwise rotate and remove it"
        ),
    )


# frob:ticket T-1211
def _scan_text(rel_path: str, text: str) -> list[Violation]:
    """SEC001/SEC004 violations for every real-looking token found in `text`
    (SEC004: T-0968, a `frob:secret-fake` marker missing `reason="..."`).

    T-1211: only lines `_candidate_line_indices` flags as possibly matching
    `_PATTERNS` (via one combined-alternation pass over the whole file text)
    are handed to `_scan_line`'s real per-pattern/fake-marker logic -- a line
    with zero possible hits is skipped entirely rather than re-scanned by all
    33 patterns individually. Findings are unchanged; see `_COMBINED_PATTERN`
    for why this cannot silently drop or reorder a real hit."""
    lines = text.splitlines()
    violations: list[Violation] = list(_bare_fake_marker_violations(rel_path, text))
    for index in _candidate_line_indices(text):
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
# frob:enforces CHK-GATE-SEC004
# frob:enforces CHK-SUBSYS-GATES-QUALITY
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling so one bad file cannot abort the whole scan; the documented SEC001-003 behavior is unchanged, so docs/modules/gates.md#public-api needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
def secrets_gate(root: Path) -> tuple[Violation, ...]:
    """SEC001/SEC002/SEC003 (docs/modules/gates.md#rule-catalog): every
    git-tracked file scanned for real-looking provider credentials, plus a
    standalone check for a tracked `.env`. Never touches untracked files
    (git ls-files only) and never echoes a matched token -- see `_redact`."""
    root = Path(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _shared_tracked_files(root, caller="secrets_gate"):
        if _is_env_file(rel_path):
            violations.append(_env002_violation(rel_path))
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            _log.debug("secrets_gate: skipping unreadable/binary %s", rel_path)
            continue
        scanned += 1
        try:
            violations.extend(_scan_text(rel_path, text))
        except Exception:
            # One file's text being surprising to the secret-pattern
            # scanner must not abort the whole SEC001-003 pass over every
            # OTHER tracked file (EXHAUST001/EXHAUST002, T-1371).
            _log.debug("secrets_gate: skipping unscannable %s", rel_path)

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
    "fake_marker_staleness_gate",
    "secrets_gate",
]
