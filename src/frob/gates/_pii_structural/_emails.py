"""PII011: email-shaped string-literal value scan (T-0349 family 4) --
T-1076 split of `frob.gates._pii_structural`."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_pii_structural/_emails.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- carried from the \
# pre-T-1076-split monolith's identical file-level waiver"

from __future__ import annotations

import ast
import re
from email.utils import parseaddr

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

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
    EMAIL_SUFFIX`) -- such an address can never resolve to a real person,
    so PII011 must not fire on it no matter where it appears."""
    domain = value.rpartition("@")[2].lower()
    if domain in _RFC2606_RESERVED_EMAIL_DOMAINS:
        return True
    return domain.endswith(_RFC2606_RESERVED_EMAIL_SUFFIX)


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


def _line_marks_fake_email(lines: list[str], lineno: int) -> bool:
    """True if the 1-indexed `lineno` line or the line directly above it
    carries a REASON-bearing `_EMAIL_FAKE_MARKER` (T-0968: mirrors
    `_secrets.py::_fake_marker_reason`'s same-line-or-line-above convention
    and its `reason="..."` requirement -- a bare marker with no reason no
    longer discharges PII011, same as it no longer discharges SEC001)."""
    index = lineno - 1
    if index < 0 or index >= len(lines):
        return False
    if _EMAIL_FAKE_MARKER_REASON_RE.search(lines[index]) is not None:
        return True
    if index > 0 and _EMAIL_FAKE_MARKER_REASON_RE.search(lines[index - 1]) is not None:
        return True
    return False


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


def _pii011_violation(rel_path: str, lineno: int, value: str) -> Violation:
    """The PII011 `Violation` for one email-shaped string literal (T-0349)."""
    _log.warning("PII011: %s:%d email-shaped literal %r", rel_path, lineno, value)
    return Violation(
        rule="PII011",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
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
    tree: ast.Module, rel_path: str, text: str
) -> tuple[Violation, ...]:
    """PII011 over every email-shaped string-literal `ast.Constant` in
    `tree` (T-0349 family 4), skipping any literal marked fake via
    `_EMAIL_FAKE_MARKER` on its own line or the line directly above."""
    lines = text.splitlines()
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if not _is_email_shaped(node.value):
            continue
        if _is_reserved_test_domain_email(node.value):
            continue
        if _line_marks_fake_email(lines, node.lineno):
            continue
        violations.append(_pii011_violation(rel_path, node.lineno, node.value))
    return tuple(violations)
