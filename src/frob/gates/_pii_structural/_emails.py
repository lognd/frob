"""PII011: email-shaped string-literal value scan (T-0349 family 4) --
T-1076 split of `frob.gates._pii_structural`."""

from __future__ import annotations

import ast
import re
from email.utils import parseaddr

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

from ._node_index import _build_node_index, _NodeIndex, enclosing_qualname

_log = get_logger(__name__)

# RFC 2606 reserves `example.com`/`example.net`/`example.org` (plus the
# `.example` TLD) for documentation and testing use -- no real person can
# ever be registered there, so an email literal at one of these domains is
# STRUCTURALLY guaranteed non-personal regardless of what file it appears
# in (T-0539: 57 of this gate's 66 PII011 findings were exactly this
# shape, `test@example.com`/`legal@example.com`/`t@example.com`, spread
# across dozens of ordinary test files with no `frob:secret-fake` marker).
# This is a VALUE-shape fact like `_is_email_shaped` itself, not a file
# exclusion -- reused wherever the literal appears, not gated on path.
_RFC2606_RESERVED_EMAIL_DOMAINS = frozenset(
    {"example.com", "example.net", "example.org"}
)
_RFC2606_RESERVED_EMAIL_SUFFIX = ".example"


def _is_reserved_test_domain_email(value: str) -> bool:
    """True if `value`'s domain part is an RFC 2606 reserved documentation/
    testing domain (`_RFC2606_RESERVED_EMAIL_DOMAINS`/`_RFC2606_RESERVED_
    EMAIL_SUFFIX`), OR its TLD label is a single character (T-2712: no
    real DNS TLD is one character -- ICANN's root zone has never
    delegated one, every ccTLD is exactly 2 characters and every gTLD is
    3+ -- so an address like `a@b.c`/`t@t.t` cannot resolve to any real
    mailbox no matter what appears to its left; this is the same
    structural, path-independent guarantee `_RFC2606_RESERVED_EMAIL_
    DOMAINS` already rests on, just a second unregistrable shape rather
    than a second reserved name. Confirmed live: `git config user.email`
    test-fixture literals across this repo's own test suite use exactly
    this shape) -- such an address can never resolve to a real person, so
    PII011 must not fire on it no matter where it appears."""
    domain = value.rpartition("@")[2].lower()
    if domain in _RFC2606_RESERVED_EMAIL_DOMAINS:
        return True
    if domain.endswith(_RFC2606_RESERVED_EMAIL_SUFFIX):
        return True
    tld = domain.rpartition(".")[2]
    return len(tld) == 1


#: T-0349 (family 4) shared fake-marker convention: the SAME literal
#: substring `frob.gates._secrets._FAKE_MARKER` uses (T-0157) -- not
#: imported directly (that module's fake-detection is line/entropy-aware
#: and secret-specific; PII011's escape hatch only needs the bare marker
#: string), but kept textually identical so one comment discharges both
#: gates' fixture literals at once.
_EMAIL_FAKE_MARKER = "frob:secret-fake"

#: T-0968: mirrors `_secrets.py::_FAKE_MARKER_REASON_RE` -- a bare
#: `_EMAIL_FAKE_MARKER` no longer discharges PII011 either; both gates share
#: the one literal marker string, so they now share the one reason-requiring
#: contract too. `_secrets.py`'s own `_bare_fake_marker_violations` (SEC004)
#: already flags a bare marker anywhere in a tracked file, PII011's included
#: -- no second SEC004-equivalent scan needed here.
_EMAIL_FAKE_MARKER_REASON_RE = re.compile(r'frob:secret-fake\s+reason="([^"]*)"')


def _joined_comment_continuation(
    lines: list[str], index: int, max_lookback: int = 8
) -> str | None:
    """T-2712: reconstruct the logical text of a `#`-comment BLOCK ending
    at 0-indexed `index`, by walking upward while each earlier physical
    line is itself a `#`-comment ending in a trailing `\\` (this repo's
    own multi-line directive-comment convention -- see
    `docs/guides/agent-playbook.md` sec 1d and every `frob:waive
    reason="...\\` / `# ...more text"` pair in this codebase). Returns
    `None` when `lines[index]` is not a comment at all, or when it has no
    continuation predecessor (single physical-line comment -- the caller
    already checks that line directly, so re-joining a lone line would
    just duplicate the same search). `max_lookback` bounds the walk so a
    pathological file cannot make this scan the whole comment history."""
    if not lines[index].lstrip().startswith("#"):
        return None
    chain = [lines[index]]
    i = index
    steps = 0
    while i > 0 and steps < max_lookback:
        prev = lines[i - 1]
        if not prev.lstrip().startswith("#") or not prev.rstrip().endswith("\\"):
            break
        chain.insert(0, prev)
        i -= 1
        steps += 1
    if len(chain) == 1:
        return None
    return " ".join(chain)


def _line_or_block_marks_fake_email(lines: list[str], index: int) -> bool:
    """True if the 0-indexed `index` line, ALONE or joined with the
    multi-line comment continuation chain it is the tail of (T-2712's
    `_joined_comment_continuation`), carries a REASON-bearing
    `_EMAIL_FAKE_MARKER`. A single-physical-line marker matches directly;
    a marker whose `reason="..."` text was wrapped across several `#`-
    prefixed lines (this repo's own convention for a long reason) only
    matches once those lines are rejoined -- the raw per-line regex
    search a naive caller would do can see the marker keyword on one
    physical line and the reason's closing quote on another, and match
    neither alone."""
    if _EMAIL_FAKE_MARKER_REASON_RE.search(lines[index]) is not None:
        return True
    joined = _joined_comment_continuation(lines, index)
    if joined is None:
        return False
    return _EMAIL_FAKE_MARKER_REASON_RE.search(joined) is not None


def _line_marks_fake_email(lines: list[str], lineno: int) -> bool:
    """True if the 1-indexed `lineno` line or the line directly above it
    carries a REASON-bearing `_EMAIL_FAKE_MARKER` (T-0968: mirrors
    `_secrets.py::_fake_marker_reason`'s same-line-or-line-above convention
    and its `reason="..."` requirement -- a bare marker with no reason no
    longer discharges PII011, same as it no longer discharges SEC001).

    T-2712: both the direct line and the line above are now checked via
    `_line_or_block_marks_fake_email`, which also reconstructs a wrapped
    multi-line marker comment before searching it -- a marker whose
    `reason="..."` spans 2+ physical `#`-lines used to never match either
    line alone (T-2438's own symref-precision fix made this class of gap
    visible repo-wide; this is its PII011-marker-side counterpart)."""
    index = lineno - 1
    if index < 0 or index >= len(lines):
        return False
    if _line_or_block_marks_fake_email(lines, index):
        return True
    return index > 0 and _line_or_block_marks_fake_email(lines, index - 1)


#: Structural (non-regex) local-part/domain-label character allowances for
#: `_is_email_shaped` -- RFC 5322 dot-atom-text's common subset, kept as a
#: plain character set (`str.isalnum()` plus these) rather than a pattern.
_EMAIL_LOCAL_EXTRA_CHARS = frozenset("._%+-")
_EMAIL_LABEL_EXTRA_CHARS = frozenset("-")


def _is_email_shaped(value: str) -> bool:
    """T-0349 (family 4): whether `value` is structurally an email address,
    via `email.utils.parseaddr` (an RFC 822 header parser, NOT a regex --
    the ticket body's explicit "regex is bad for email matching" mandate)
    plus a plain character-set validation of the parsed local/domain parts.
    Whitespace anywhere rules a literal out outright (an email address
    never contains a space); `parseaddr` returning a DIFFERENT address than
    `value` itself means `value` was some other RFC 822 header shape
    (`"Name <addr>"`, a bare display name, ...), not a bare email literal."""
    if not value or any(ch.isspace() for ch in value):
        return False
    _, addr = parseaddr(value)
    if addr != value:
        return False
    local, sep, domain = addr.partition("@")
    if not sep or not local or not domain or "@" in domain:
        return False
    labels = domain.split(".")
    if len(labels) < 2 or any(not label for label in labels):
        return False
    if not all(ch.isalnum() or ch in _EMAIL_LOCAL_EXTRA_CHARS for ch in local):
        return False
    for label in labels:
        if label.startswith("-") or label.endswith("-"):
            return False
        if not all(ch.isalnum() or ch in _EMAIL_LABEL_EXTRA_CHARS for ch in label):
            return False
    return True


def _pii011_violation(
    rel_path: str, lineno: int, value: str, *, symref: str | None = None
) -> Violation:
    """The PII011 `Violation` for one email-shaped string literal (T-0349).

    T-2696: `symref` (the enclosing class/function's dotted qualname, from
    `_node_index.enclosing_qualname`) lets `_match_waiver` require an exact
    `path::qualname` match instead of the file-wide fallback every PII011
    finding used before this ticket -- `None` for a module-level literal
    (no enclosing symbol), matching `Violation.symref`'s own documented
    contract.

    T-2712: `enclosing_qualname` returns a bare dotted qualname with no
    file prefix, but `Violation.symref`'s documented contract (and every
    waiver comment's DSL-bound `waiver.src`) is `path::qualname` -- an
    un-prefixed symref can never `_canonical_symref`-match a real waiver,
    so this prefixes `rel_path` here, at the one place both values are
    already in scope, rather than at each of this rule's call sites."""
    _log.warning("PII011: %s:%d email-shaped literal %r", rel_path, lineno, value)
    qualified_symref = f"{rel_path}::{symref}" if symref is not None else None
    return Violation(
        rule="PII011",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        symref=qualified_symref,
        message=(
            f"PII011: {rel_path}:{lineno} string literal {value!r} is "
            f"email-shaped (structural parseaddr match) with no PII "
            f"declaration or waiver -- declare it via a std.pii `carries` "
            f"tag on the owning strata node, mark it a fixture with a "
            f'`{_EMAIL_FAKE_MARKER} reason="..."` comment on this line or '
            f'the line above, or `frob:waive PII011 reason="..."` if this '
            f"is not actually personal data"
        ),
    )


# frob:tests tests/test_pii_structural_gate.py::TestEmailShapeValues.test_email_literal_fires  # noqa: E501
def _scan_python_email_values(
    tree: ast.Module, rel_path: str, text: str, *, _index: _NodeIndex | None = None
) -> tuple[Violation, ...]:
    """PII011 over every email-shaped string-literal `ast.Constant` in
    `tree` (T-0349 family 4), skipping any literal marked fake via
    `_EMAIL_FAKE_MARKER` on its own line or the line directly above.
    `_index` (T-1209 perf): see `_scan_python_fields`'s docstring --
    computed locally when omitted."""
    index = _index if _index is not None else _build_node_index(tree)
    lines = text.splitlines()
    violations: list[Violation] = []
    for node in index.str_constants:
        value = node.value
        if not isinstance(value, str):
            # Unreachable at runtime -- see `_scan_ddl_strings`'s identical
            # guard (`_python_fields.py`) for why this re-check exists.
            continue
        if not _is_email_shaped(value):
            continue
        if _is_reserved_test_domain_email(value):
            continue
        if _line_marks_fake_email(lines, node.lineno):
            continue
        violations.append(
            _pii011_violation(
                rel_path,
                node.lineno,
                value,
                symref=enclosing_qualname(index, node.lineno),
            )
        )
    return tuple(violations)
