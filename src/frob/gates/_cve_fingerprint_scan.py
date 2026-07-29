"""SEC-CVE-FINGERPRINT-001 (T-0439): a `frob check` gate over first-party
repo source, scanning it for the `frob.strata._cve_fingerprint.
CVE_FINGERPRINTS` needle corpus -- the canonical vulnerable-usage-class
patterns (unsafe shell invocation, unsafe YAML/pickle deserialization,
...), each citing a REAL CVE and joined to the `std.cwe` catalog
(`_cve_fingerprint.py` module docstring). This docstring deliberately does
not spell out the needle strings themselves (T-0151/T-0439 self-match
false-positive class below) -- see `_cve_fingerprint.py`'s own
`CVE_FINGERPRINTS` table for the literal needles.

Distinct from two existing, narrower uses of the same catalog:

- `frob.strata._cve_fingerprint.check_fingerprint_catalog_drift` (CVEFP001)
  only checks the CATALOG for drift (does every `cwe_id` still join a real
  `WeaknessEntry`) -- it never scans any source text.
- `frob.vet._capability._scan_file_fingerprints` scans a THIRD-PARTY
  dependency's local source (via `frob vet`) and reports only WHICH
  fingerprints matched somewhere in that dependency, with no file:line --
  vet's audience is "should we vet-allow this dependency", not "fix this
  line".

This gate is the missing first-party-source-lint sibling: every
git-tracked repo file gets language-bucketed (mirroring `frob.vet.
_capability`'s own `_EXT_LANGUAGE` extension table -- duplicated here
rather than imported, the same small-helper-not-worth-the-coupling call
`frob.gates._walk_lint`'s own docstring already makes for `_dotted_prefix`)
and scanned via `frob.strata._cve_fingerprint.scan_text_for_fingerprints`,
which returns a `FingerprintHit` per needle occurrence WITH a line number.
"""
# frob:waive INV006 preset="split-carried-prose"

# frob:ticket T-0439
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.gates._parse_failures import local_parse001_violation
from frob.gates._tracked_files import tracked_files as _shared_tracked_files
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.strata._cve_fingerprint import FingerprintHit

_log = get_logger(__name__)

#: extension -> language bucket, matching `CveFingerprint.language`'s four
#: values (`frob.vet._capability._EXT_LANGUAGE`'s own set, duplicated per
#: this module's docstring rather than imported across packages for one
#: small table).
_EXT_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
    ".c": "c-cpp",
    ".h": "c-cpp",
    ".cc": "c-cpp",
    ".cpp": "c-cpp",
    ".cxx": "c-cpp",
    ".hpp": "c-cpp",
    ".hh": "c-cpp",
}

#: This module's own file, plus `_cve_fingerprint.py` itself -- both
#: legitimately contain every needle as literal string DATA (the catalog
#: definition, this module's own docstring/table), the same self-match
#: false-positive class `frob.vet._capability`'s module docstring (T-0151
#: part b) already documents; excluded from scanning rather than silently
#: producing a locked, permanently-noisy self-hit.
_SELF_EXCLUDED_FILES = frozenset(
    {
        "src/frob/gates/_cve_fingerprint_scan.py",
        "src/frob/strata/_cve_fingerprint.py",
    }
)


def _language_for(rel_path: str) -> str | None:
    """The scanned language bucket for `rel_path`'s extension, or `None`
    for an extension this gate does not scan."""
    suffix = "." + rel_path.rsplit(".", 1)[-1] if "." in rel_path else ""
    return _EXT_LANGUAGE.get(suffix)


# frob:ticket T-0897
def _parse001_violation(rel_path: str, reason: str) -> Violation:
    """PARSE001 `Violation` for a file this gate's own read could not get
    through (T-0897): delegates to `frob.gates._parse_failures.
    local_parse001_violation` (extracted T-0861) with this gate's own
    capability-loss clause so SEC-CVE-FINGERPRINT-001's message stays
    distinct while the rule id/severity/message shape is the ONE shared
    home."""
    return local_parse001_violation(
        rel_path,
        reason,
        "SEC-CVE-FINGERPRINT-001 cannot scan it for a vulnerable-usage fingerprint",
        unparseable_word="unreadable",
    )


def _hit_violation(rel_path: str, hit: "FingerprintHit") -> Violation:
    """The `SEC-CVE-FINGERPRINT-001` `Violation` for one matched needle."""
    _log.warning(
        "SEC-CVE-FINGERPRINT-001: %s:%d fingerprint %s (%s) matched needle %r",
        rel_path,
        hit.line,
        hit.fingerprint_id,
        hit.cwe_id,
        hit.needle,
    )
    return Violation(
        rule="SEC-CVE-FINGERPRINT-001",
        severity=Severity.WARN,
        file=rel_path,
        line=hit.line,
        message=(
            f"SEC-CVE-FINGERPRINT-001: {rel_path}:{hit.line} matches CVE "
            f"fingerprint {hit.fingerprint_id} ({hit.title}, {hit.cwe_id}) via "
            f"needle {hit.needle!r} -- {hit.remediation}, or "
            f'`frob:waive SEC-CVE-FINGERPRINT-001 reason="..."` if this is a '
            f"confirmed false positive"
        ),
    )


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
# frob:ticket T-0439
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_smelly_file_fires  # noqa: E501
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_clean_file_does_not_fire  # noqa: E501
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_self_excluded_files_not_scanned  # noqa: E501
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_undecodable_file_fires_parse001  # noqa: E501
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_undecodable_file_under_graph_exclude_is_silent  # noqa: E501
# frob:ticket T-0897
# frob:enforces CHK-GATE-SEC-CVE-FINGERPRINT-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-EXEC-SHELL-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-XSS-JQUERY-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-PATH-TAR-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-DESERIALIZE-YAML-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-DESERIALIZE-PICKLE-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-SQLI-STRFMT-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-SSRF-FETCH-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-CODEEVAL-TEMPLATE-001
# frob:enforces SEC-CVE-FINGERPRINT-FP-HARDCODED-CRED-001
# frob:enforces SEC-CVE-FINGERPRINT-CWE-295-TLS-VERIFY
# frob:enforces SEC-CVE-FINGERPRINT-CWE-916-WEAK-HASH
# frob:enforces SEC-CVE-FINGERPRINT-CWE-611-XXE
# frob:enforces SEC-CVE-FINGERPRINT-CWE-1321-PROTO-POLLUTION
# frob:enforces SEC-CVE-FINGERPRINT-CWE-1333-REDOS
# frob:enforces SEC-CVE-FINGERPRINT-CWE-601-OPEN-REDIRECT
# frob:enforces SEC-CVE-FINGERPRINT-CWE-1336-SSTI
def cve_fingerprint_scan_gate(root: Path) -> tuple[Violation, ...]:
    """SEC-CVE-FINGERPRINT-001 (module docstring): every git-tracked,
    language-bucketed source file under `root` scanned for a `CVE_
    FINGERPRINTS` needle match via `scan_text_for_fingerprints`, one
    `Violation` per matched occurrence. Imports `frob.strata._cve_
    fingerprint` LAZILY (not at module scope) -- mirrors `frob.gates.
    __init__`'s own deferred-`frob.strata`-import convention (T-0135: a
    top-level import would pay the `strata_core` native-extension cost on
    every `frob check` invocation, even for a repo with no design dir at
    all). A file this gate cannot read fires PARSE001 instead of silently
    dropping out of the scan (T-0897), UNLESS the file matches a
    `[graph].exclude` glob (frob.toml) -- that config already carves the
    path out of frob's own obligation surface (e.g. `tests/fixtures/**`'s
    deliberately-broken parser fixtures), so PARSE001 stays silent there
    too."""
    from frob.strata._cve_fingerprint import scan_text_for_fingerprints

    root = Path(root)
    exclude_globs = load_exclude_globs(root)
    violations: list[Violation] = []
    scanned = 0
    for rel_path in _shared_tracked_files(root, caller="cve_fingerprint_scan_gate"):
        if rel_path in _SELF_EXCLUDED_FILES:
            _log.debug("cve_fingerprint_scan_gate: skipping self-excluded %s", rel_path)
            continue
        language = _language_for(rel_path)
        if language is None:
            continue
        try:
            text = (root / rel_path).read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            if is_excluded(rel_path, exclude_globs):
                # T-0897: `[graph].exclude` (frob.toml) already carves this
                # path out of frob's own obligation surface (e.g.
                # tests/fixtures/**'s deliberately-broken parser fixtures)
                # -- PARSE001 stays silent here, same as the graph-ingested
                # path already treats it, instead of forcing every such
                # fixture to carry its own waiver.
                _log.debug(
                    "cve_fingerprint_scan_gate: skipping excluded unreadable %s",
                    rel_path,
                )
                continue
            violations.append(_parse001_violation(rel_path, str(exc)))
            continue
        scanned += 1
        hits = scan_text_for_fingerprints(text, language)
        violations.extend(_hit_violation(rel_path, hit) for hit in hits)

    _log.info(
        "cve_fingerprint_scan_gate: scanned %d tracked file(s), %d violation(s)",
        scanned,
        len(violations),
    )
    return tuple(violations)


__all__ = ["cve_fingerprint_scan_gate"]
