"""WEBSEC218-224: password policy and storage
(docs/modules/webapp-websec-password.md, T-5353), the T-5140 web-app
epic's password-policy/storage leaf: file-scope evidence of a missing
control (no breach-password check anywhere alongside a `set_password`
call, no `email_verified` check anywhere alongside a privileged-action
call) or a weak cryptographic primitive/config (MD5/SHA1 password
hashing, AES-ECB, a hardcoded IV, a default seed-data account, a
case-folded password comparison) -- single-file evidence scans, the
same posture T-5329's `_websec_debug_config` already uses for this
shape of check.

Same posture as the rest of the `_websec_*` family: TEXT-REGEX over
tracked source/config files (the ticket body's own "AST lint per sink"
is approximated as a call/literal-site regex here, the same idiom
`_websec_headers_log`/`_websec_debug_config`/`_websec_tokens` already
use for JS/TS evidence -- `frob.lang`'s identifier walker has no
javascript/typescript entry yet, T-3232), gated on
`frob.webapp._detect.detect_frameworks` reporting at least one web
framework (T-5302's contract), and discovered by
`frob.gates._taint_gate`'s pkgutil hook (T-5308) via this module's
`websec_findings(root, frameworks)` -- no `_taint_gate.py`/
`gates/__init__.py` edit needed.

SEVEN RULE IDS used of the reserved `WEBSEC218`-`WEBSEC225` eight-id
block (T-5301-shaped reservation); `WEBSEC225` is left unimplemented --
see the T-5353 Done report for the follow-up ticket id:

- WEBSEC218: a privileged-action call (`delete_account(`/
  `transfer_funds(`/`grant_admin(`/`change_password(`) in a file with
  no `email_verified`/`is_verified` check anywhere in that same file --
  a file-scope proxy for "this action path never gates on email
  verification" (a per-function/per-branch check would need real
  control-flow analysis this module does not attempt, the same
  disclosed granularity gap `_websec_headers_log`'s intra-line
  sanitizer check already carries for a different axis).
- WEBSEC219: a `set_password(`/`hash_password(` call in a file with no
  breach-password check anywhere in that same file (no `pwned`/
  `breach`/`hibp` reference) -- NIST 800-63B 5.1.1.2.
- WEBSEC220: `hashlib.md5(`/`hashlib.sha1(` called on a line that also
  mentions `password`/`pwd`/`passwd` -- a weak (non-bcrypt/argon2/
  scrypt) password-hashing algorithm.
- WEBSEC221: `MODE_ECB`/an `"aes-*-ecb"`-shaped cipher-mode string --
  ECB leaks block-level plaintext structure.
- WEBSEC222: an `iv`/`nonce`-named variable assigned a hardcoded
  hex/byte-string literal, instead of drawn from a CSPRNG
  (`os.urandom`/`crypto.randomBytes`) -- static IV/nonce reuse.
- WEBSEC223: a file under a `seed`/`migration`/`fixtures`-shaped path
  segment assigning a default-looking credential (`admin`/`password`/
  `changeme`/`123456`) to a `password`-named field.
- WEBSEC224: a password comparison/verification with `.lower()` (or
  `.upper()`) applied to either side -- silent case-folding weakens the
  effective password space; this module does not attempt to detect
  silent 72-byte bcrypt truncation, a config-level fact this text scan
  cannot see.

Default-credential findings outside seed/migration data are SEC001-003's
job, not duplicated here.

Each fires WARN-tier at first turn-on, the same T-0688/T-0973 promotion
posture every other brand-new WEBSEC family in this repo follows.
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
    "WebsecPasswordFinding",
    "websec_findings",
    "websec_password_findings",
]


# frob:doc docs/modules/webapp-websec-password.md#public-api
# frob:ticket T-5353
@dataclass(frozen=True)
class WebsecPasswordFinding:
    """One WEBSEC218-224 finding: a missing password-policy control, or
    a weak cryptographic primitive/config around password storage.

    frob:ticket T-5353
    """

    rule: str
    file: str
    line: int
    message: str


_PRIVILEGED_ACTION_RE = re.compile(
    r"\b(?:delete_account|transfer_funds|grant_admin|change_password)\s*\("
)
_EMAIL_VERIFIED_RE = re.compile(r"email_verified|is_verified", re.IGNORECASE)

_SET_PASSWORD_RE = re.compile(r"\b(?:set_password|hash_password)\s*\(")
_BREACH_CHECK_RE = re.compile(r"pwned|breach|hibp", re.IGNORECASE)

_WEAK_HASH_CALL_RE = re.compile(r"""hashlib\.(?:md5|sha1)\s*\(""", re.IGNORECASE)
_PASSWORD_WORD_RE = re.compile(r"""\b(?:password|pwd|passwd)\b""", re.IGNORECASE)

_ECB_MODE_RE = re.compile(r"""MODE_ECB|aes-\d{3}-ecb""", re.IGNORECASE)

_STATIC_IV_RE = re.compile(
    r"""\b(?:iv|nonce)\b\s*[:=]\s*b?["'][0-9a-fA-F]{16,}["']""", re.IGNORECASE
)

_SEED_PATH_RE = re.compile(r"(^|/)(seed|seeds|migrations?|fixtures)(/|$)")
_DEFAULT_CRED_RE = re.compile(
    r"""password["']?\s*[:=]\s*["'](admin|password|changeme|123456)["']""",
    re.IGNORECASE,
)

_CASE_FOLDED_COMPARE_RE = re.compile(
    r"""\bpassword\w*\.(?:lower|upper)\(\)""", re.IGNORECASE
)


def _tracked_files(root: Path, *suffixes: str) -> tuple[str, ...]:
    """`git ls-files` under `root`, filtered to `suffixes`, root-relative
    POSIX paths, `()` on any git failure -- mirrors
    `_websec_headers_log._tracked_files`'s own tracked-file-scan shape.

    frob:ticket T-5353
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files"))
    if spawned.is_err:
        _log.warning("websec_password: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("websec_password: git ls-files exited %d", result.returncode)
        return ()
    return tuple(
        line
        for line in result.stdout.splitlines()
        if line.strip() and line.endswith(suffixes)
    )


def _read_text(path: Path) -> str:
    """Read `path` as text, returning "" for anything unreadable.

    frob:ticket T-5353
    """
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line_of(text: str, offset: int) -> int:
    """1-based line number of char `offset` in `text`.

    frob:ticket T-5353
    """
    return text.count("\n", 0, offset) + 1


def _email_verification_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC218: a privileged-action call in a file with no
    email-verification check anywhere in that file.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _PRIVILEGED_ACTION_RE.search(text)
        if match is None or _EMAIL_VERIFIED_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC218",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC218: {rel}:{line} a privileged action is "
                    f"performed with no email_verified/is_verified check "
                    f"anywhere in this file. Gate the action on the "
                    f"user's verified-email status, or `frob:waive "
                    f'WEBSEC218 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _breach_password_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC219: a `set_password`/`hash_password` call in a file with
    no breach-password check anywhere in that file (NIST 800-63B
    5.1.1.2).

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _SET_PASSWORD_RE.search(text)
        if match is None or _BREACH_CHECK_RE.search(text):
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC219",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC219: {rel}:{line} a new password is set with "
                    f"no breach-password check anywhere in this file "
                    f"(NIST 800-63B 5.1.1.2) -- a known-compromised "
                    f"password is accepted. Check it against a breach "
                    f"corpus (e.g. HIBP k-anonymity) first, or `frob:waive "
                    f'WEBSEC219 reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _weak_hash_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC220: `hashlib.md5`/`hashlib.sha1` used to hash a password.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py"):
        text = _read_text(root / rel)
        for lineno, line_text in enumerate(text.splitlines(), start=1):
            if not _WEAK_HASH_CALL_RE.search(line_text):
                continue
            if not _PASSWORD_WORD_RE.search(line_text):
                continue
            findings.append(
                WebsecPasswordFinding(
                    rule="WEBSEC220",
                    file=rel,
                    line=lineno,
                    message=(
                        f"WEBSEC220: {rel}:{lineno} a password is hashed "
                        f"with MD5/SHA1 -- both are fast, "
                        f"unsalted-by-default digests unsuitable for "
                        f"password storage. Use bcrypt/argon2/scrypt "
                        f'instead, or `frob:waive WEBSEC220 reason="..."` '
                        f"with a real justification"
                    ),
                )
            )
    return findings


def _ecb_mode_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC221: an AES-ECB cipher mode.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _ECB_MODE_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC221",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC221: {rel}:{line} ECB cipher mode leaks "
                    f"block-level plaintext structure (identical "
                    f"plaintext blocks encrypt to identical ciphertext "
                    f"blocks). Use an authenticated mode (GCM) instead, "
                    f'or `frob:waive WEBSEC221 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


def _static_iv_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC222: an `iv`/`nonce` variable assigned a hardcoded literal.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _STATIC_IV_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC222",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC222: {rel}:{line} an iv/nonce is a hardcoded "
                    f"literal -- reusing the same IV/nonce across "
                    f"encryptions breaks the cipher mode's security "
                    f"guarantee. Draw it fresh from a CSPRNG per "
                    f'encryption, or `frob:waive WEBSEC222 reason="..."` '
                    f"with a real justification"
                ),
            )
        )
    return findings


def _default_account_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC223: a default-looking credential in seed/migration data.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx", ".json"):
        if _SEED_PATH_RE.search(rel) is None:
            continue
        text = _read_text(root / rel)
        match = _DEFAULT_CRED_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC223",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC223: {rel}:{line} seed/migration data creates "
                    f"an account with a default-looking password -- ships "
                    f"a guessable credential into every environment that "
                    f"runs this seed. Generate a random password per "
                    f"environment instead, or `frob:waive WEBSEC223 "
                    f'reason="..."` with a real justification'
                ),
            )
        )
    return findings


def _case_folded_compare_findings(root: Path) -> list[WebsecPasswordFinding]:
    """WEBSEC224: a password comparison with `.lower()`/`.upper()`
    applied.

    frob:ticket T-5353
    """
    findings: list[WebsecPasswordFinding] = []
    for rel in _tracked_files(root, ".py", ".js", ".jsx", ".ts", ".tsx"):
        text = _read_text(root / rel)
        match = _CASE_FOLDED_COMPARE_RE.search(text)
        if match is None:
            continue
        line = _line_of(text, match.start())
        findings.append(
            WebsecPasswordFinding(
                rule="WEBSEC224",
                file=rel,
                line=line,
                message=(
                    f"WEBSEC224: {rel}:{line} a password is case-folded "
                    f"before comparison -- this silently shrinks the "
                    f"effective password space (Passw0rd and PASSW0RD "
                    f"become equivalent). Compare the raw value instead, "
                    f'or `frob:waive WEBSEC224 reason="..."` with a real '
                    f"justification"
                ),
            )
        )
    return findings


# frob:doc docs/modules/webapp-websec-password.md#public-api
# frob:ticket T-5353
def websec_password_findings(root: Path) -> tuple[WebsecPasswordFinding, ...]:
    """WEBSEC218-224: every password-policy/storage finding under
    `root`.

    Short-circuits to `()` when `frob.webapp._detect.detect_frameworks`
    reports no web framework at all -- the same contract every
    WEBSEC/COMPLY/A11Y/SEO/WEBPERF family in this repo uses (T-5302).
    """
    root = Path(root)
    if not detect_frameworks(root):
        _log.debug("websec_password: no framework detected at %s, skipping scan", root)
        return ()

    findings: list[WebsecPasswordFinding] = []
    findings.extend(_email_verification_findings(root))
    findings.extend(_breach_password_findings(root))
    findings.extend(_weak_hash_findings(root))
    findings.extend(_ecb_mode_findings(root))
    findings.extend(_static_iv_findings(root))
    findings.extend(_default_account_findings(root))
    findings.extend(_case_folded_compare_findings(root))

    _log.info("websec_password: %d finding(s) under %s", len(findings), root)
    return tuple(findings)


# frob:doc docs/modules/webapp-websec-password.md#public-api
# frob:ticket T-5353
def websec_findings(
    root: Path, frameworks: frozenset[FrameworkKind]
) -> tuple[Violation, ...]:
    """`frob.gates._taint_gate.taint_gate`'s module-discovery hook
    (T-5308): every `frob.webapp._websec_*` module exposing a
    module-level `websec_findings(root, frameworks) -> tuple[Violation,
    ...]` is auto-discovered and folded into `taint_gate`'s scan, so
    this WEBSEC218-224 family never needs its own `gates/__init__.py`/
    `_taint_gate.py` edit. `frameworks` is the caller's own
    already-computed `detect_frameworks(root)` result (avoids a second
    detect call per discovered module) -- an empty set short-circuits
    to `()`, same contract as `websec_password_findings`.
    """
    if not frameworks:
        _log.debug(
            "websec_password: no framework detected at %s, skipping scan (hook)", root
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
        for finding in websec_password_findings(root)
    )
