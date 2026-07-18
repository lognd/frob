"""`std.cve` fingerprints: a code-LEVEL pattern catalog for canonical
vulnerable-usage classes (T-0153, docs/strata/threat.md#cve-fingerprints-
code-level-pattern-catalog-t-0153).

Distinct from the version-matching CVE join `frob.vet._cve`/`_containment`
already run (T-0110/T-0146/T-0147: "does this pinned dependency VERSION
carry a known CVE"): a `CveFingerprint` is a source-code NEEDLE, following
`frob.vet._capability`'s recall-over-precision substring philosophy
(module docstring there) plus the T-0151 dot-exclusion lesson (a needle
must not fire on a dotted method access that merely shares a name with a
dangerous bare call) -- so the scanner can flag "this code, or vetted
dependency source, LOOKS LIKE the shape of a canonical vulnerability
class" even when no dependency-version CVE match exists at all (first-party
code, or a dependency whose osv-scanner advisory has not been filed yet).

Each `CveFingerprint.cwe_id` joins the EXISTING `std.cwe` catalog
(`_threat.py::CWE_CATALOG` + `CWE_TOP_25_CATALOG` + `QUALITY_CATALOG`) --
`check_fingerprint_catalog_drift` fails loudly (CVEFP001) on any fingerprint
naming a `cwe_id` the joined catalog does not carry, so a fingerprint can
never silently cite a CWE id that was renamed or removed out from under it
(the same drift-lock discipline `WeaknessEntry.capability_kind`'s join to
`_effects.py::_may_kind` already follows).

Curated set, deliberately smaller than the ticket's "10-15" upper bound:
every entry below cites a REAL, independently-verified CVE (web-searched
against NVD/vendor/Snyk sources at authoring time, never hand-guessed from
memory) for the pattern class it fingerprints. A handful of the ticket's
suggested example classes are deliberately NOT shipped here rather than
force-fit with a low-confidence or fabricated citation:

- TLS `verify=False` (CWE-295), weak-hash password storage (CWE-916), and
  XML external entities (CWE-611): no `WeaknessEntry` for CWE-295, CWE-916,
  or CWE-611 exists in ANY catalog tuple yet (`CWE_CATALOG`/
  `CWE_TOP_25_CATALOG`/`QUALITY_CATALOG`) -- shipping a fingerprint for any
  of the three would fail `check_fingerprint_catalog_drift` outright by
  this module's OWN drift-lock rule, confirming they must wait for a
  `WeaknessEntry` (a separate, catalog-scoped ticket) before a fingerprint
  can honestly join them.
- JNDI-style lookup injection (the Log4Shell class): Log4Shell is a
  Java/JNDI-specific shape with no equivalent construct in any of the four
  languages `frob.vet._capability` scans (python/typescript/rust/c-cpp) --
  a fingerprint with no genuine needle in a scanned language would be
  undetectable data, not a real pattern-match capability.

Nine fingerprints ship, each with a needle in a language the vet scanner
actually covers. TLS `verify=False`, weak-hash password storage, and XXE
are tracked as an honest, disclosed gap (this docstring) rather than
silently dropped; a follow-up ticket adding the missing CWE-295, CWE-916,
and CWE-611 `WeaknessEntry` rows would unblock all three.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typani.result import Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._threat import CWE_CATALOG, CWE_TOP_25_CATALOG, QUALITY_CATALOG, WeaknessEntry

_log = get_logger(__name__)


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
class CveFingerprint(BaseModel):
    """One `std.cve` fingerprint: a code-level pattern for a canonical
    vulnerable-usage class, joined to the `std.cwe` catalog by `cwe_id` and
    cited by at least one REAL CVE (`cve`, never hand-transcribed/fabricated
    -- module docstring). `needles` follows `frob.vet._capability`'s
    recall-over-precision substring philosophy: a false positive here is an
    extra flagged line for a human to dismiss, a false negative is a missed
    attack class."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "FP-EXEC-SHELL-001"
    title: str
    cve: tuple[str, ...] = Field(min_length=1)  # real CVE id(s), e.g. "CVE-2014-6271"
    cwe_id: str  # joins WeaknessEntry.id in the CWE catalog union (drift-locked)
    language: str  # "python" | "typescript" | "rust" | "c-cpp" (vet's language bucket)
    needles: tuple[str, ...] = Field(min_length=1)
    remediation: str


#: The joined CWE catalog every `CveFingerprint.cwe_id` must resolve
#: against -- the SAME three tuples `_audit.py`'s security/quality loops
#: already treat as the catalog union, kept in one place so a future
#: catalog addition/removal is felt here automatically (charter: no
#: duplication).
_JOINED_CWE_CATALOG: tuple[WeaknessEntry, ...] = (
    CWE_CATALOG + CWE_TOP_25_CATALOG + QUALITY_CATALOG
)

# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
# frob:ticket T-0153
CVE_FINGERPRINTS: tuple[CveFingerprint, ...] = (
    CveFingerprint(
        id="FP-EXEC-SHELL-001",
        title="subprocess/os.system with shell=True and interpolated input",
        cve=("CVE-2014-6271",),  # Shellshock: bash function-definition parsing
        # let an attacker-controlled environment variable inject a trailing
        # command -- the canonical exemplar of "a shell interprets
        # attacker-influenced text", the exact shape shell=True string
        # interpolation reproduces in application code.
        cwe_id="CWE-78",
        language="python",
        needles=("shell=True",),
        remediation="pass args as a list with shell=False (the default); "
        "never format untrusted input into a shell command string",
    ),
    CveFingerprint(
        id="FP-XSS-JQUERY-001",
        title="cross-domain ajax response executed as script/html with no dataType",
        cve=("CVE-2015-9251",),  # jQuery < 3.0.0: a cross-domain ajax
        # response is executed via jQuery.globalEval even with no dataType
        # option set, an XSS primitive from an untrusted response body.
        cwe_id="CWE-79",
        language="typescript",
        needles=(".html(", "dangerouslySetInnerHTML", "document.write("),
        remediation="set dataType explicitly on cross-origin requests; "
        "encode/sanitize any untrusted string before it reaches .html()/"
        "dangerouslySetInnerHTML/document.write",
    ),
    CveFingerprint(
        id="FP-PATH-TAR-001",
        title="tarfile.extractall() with no member-path filtering",
        cve=("CVE-2007-4559",),  # Python tarfile's extract/extractall trust
        # a TarInfo member's own name, letting a crafted archive traverse
        # via "../" and overwrite files outside the target directory.
        cwe_id="CWE-22",
        language="python",
        needles=(".extractall(",),
        remediation="pass filter='data' (Python 3.12+) or manually reject "
        "any TarInfo member whose resolved path escapes the target "
        "directory before extracting",
    ),
    CveFingerprint(
        id="FP-DESERIALIZE-YAML-001",
        title="yaml.load() without an explicit SafeLoader",
        cve=("CVE-2017-18342",),  # PyYAML < 5.1: yaml.load() defaults to a
        # loader that can construct and execute arbitrary Python objects
        # from the YAML document, a direct RCE primitive on untrusted input.
        cwe_id="CWE-502",
        language="python",
        needles=("yaml.load(",),
        remediation="use yaml.safe_load()/yaml.load(data, Loader="
        "yaml.SafeLoader) -- never the bare, loader-less yaml.load()",
    ),
    CveFingerprint(
        id="FP-DESERIALIZE-PICKLE-001",
        title="pickle.loads() on network-received or otherwise untrusted bytes",
        cve=("CVE-2025-32444",),  # vLLM's recv_pyobj() over an unauthenticated
        # ZeroMQ socket internally calls pickle.loads() on whatever bytes
        # arrive -- pickle's __reduce__ protocol turns deserialization
        # itself into arbitrary code execution, CVSS 10.0.
        cwe_id="CWE-502",
        language="python",
        needles=("pickle.loads(", "pickle.load("),
        remediation="never unpickle data from an untrusted or network-"
        "exposed source; use a schema-validated format (json, protobuf) "
        "or hmac-sign the payload and verify before unpickling",
    ),
    CveFingerprint(
        id="FP-SQLI-STRFMT-001",
        title="SQL built by string formatting/concatenation of request data",
        cve=("CVE-2012-2661",),  # Ruby on Rails ActiveRecord: nested query
        # parameters reached a `where` clause unparameterized, letting an
        # attacker inject arbitrary SQL -- a cross-ecosystem exemplar of the
        # SAME "unparameterized, request-influenced SQL text" shape this
        # fingerprint's needles target in Python's DB-API, disclosed here
        # rather than silently presented as Python-specific.
        cwe_id="CWE-89",
        language="python",
        needles=('.execute(f"', ".execute('%s'", '.execute("%s'),
        remediation="use parameterized queries (cursor.execute(query, "
        "params)) -- never f-strings/%-formatting/concatenation to build "
        "SQL text from request-influenced values",
    ),
    CveFingerprint(
        id="FP-SSRF-FETCH-001",
        title="outbound fetch of a request-controlled URL with no allowlist",
        cve=("CVE-2021-21973",),  # VMware vCenter's vRealize Operations
        # plugin proxied a caller-supplied URL with no destination
        # validation, an SSRF letting an unauthenticated caller reach
        # internal-only endpoints -- a cross-ecosystem exemplar of the
        # exact "unvalidated outbound URL" shape these needles target.
        cwe_id="CWE-918",
        language="python",
        needles=("requests.get(url", "requests.post(url", "urlopen(url"),
        remediation="validate the destination host/scheme against an "
        "explicit allowlist before the outbound request, or route through "
        "a mediating proxy that enforces one",
    ),
    CveFingerprint(
        id="FP-CODEEVAL-TEMPLATE-001",
        title="dynamic Function()/template-engine compilation of an "
        "attacker-influenced settings value",
        cve=("CVE-2021-23358",),  # underscore.js template(): an attacker-
        # controlled settings.variable string is concatenated into the
        # body of a `new Function(...)` call, letting it break out of the
        # intended string context and inject arbitrary JS.
        cwe_id="CWE-94",
        language="typescript",
        needles=("new Function(",),
        remediation="never build a Function()/eval() body from a runtime-"
        "configurable or request-influenced string; use a template engine "
        "with a fixed, non-configurable variable name and auto-escaping",
    ),
    CveFingerprint(
        id="FP-HARDCODED-CRED-001",
        title="a literal password/secret assigned to an authentication-"
        "looking variable",
        cve=("CVE-2015-7755",),  # Juniper ScreenOS: a hardcoded backdoor
        # password (disguised as a debug format string) shipped in
        # firmware, granting SSH/Telnet authentication bypass to anyone who
        # discovered the literal -- the canonical hardcoded-credential
        # exemplar, cross-ecosystem, disclosed as such.
        cwe_id="CWE-798",
        language="python",
        needles=('password = "', "password: str = '", 'PASSWORD = "'),
        remediation="load credentials from an environment variable or a "
        "secrets manager at runtime -- never a source-literal string",
    ),
)

#: T-0153: the `cve-fingerprint-catalog` view, kept as a SEPARATE table
#: from `_threat.py::VIEWS`/`CWE_TOP_25_VIEWS` (following those tables'
#: OWN precedent of never silently widening an existing default view,
#: docs/strata/threat.md#the-catalog-stdcwe) -- a caller checking fingerprint
#: catalog completeness passes this explicitly.
# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
CVE_FINGERPRINT_VIEWS: dict[str, frozenset[str]] = {
    "cve-fingerprint-catalog": frozenset(entry.id for entry in CVE_FINGERPRINTS),
}


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
class FingerprintViolation(BaseModel):
    """One CVEFP001 finding: a fingerprint id citing a `cwe_id` the joined
    `std.cwe` catalog does not carry -- never a silent gap (module docstring)."""

    model_config = ConfigDict(frozen=True)

    rule: str = "CVEFP001"
    fingerprint_id: str
    cwe_id: str
    detail: str = ""


def _drift_violation(entry: CveFingerprint) -> FingerprintViolation:
    """CVEFP001 violation helper: deny-by-default unjoined `cwe_id`."""
    _log.warning(
        "cve_fingerprint: CVEFP001 %s cites %s, absent from the joined std.cwe catalog",
        entry.id,
        entry.cwe_id,
    )
    return FingerprintViolation(
        fingerprint_id=entry.id,
        cwe_id=entry.cwe_id,
        detail=f"fingerprint {entry.id!r} cites {entry.cwe_id!r}, which no "
        "WeaknessEntry in CWE_CATALOG + CWE_TOP_25_CATALOG + QUALITY_CATALOG "
        "carries",
    )


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
def check_fingerprint_catalog_drift(
    fingerprints: tuple[CveFingerprint, ...] = CVE_FINGERPRINTS,
    cwe_catalog: tuple[WeaknessEntry, ...] = _JOINED_CWE_CATALOG,
) -> Result[tuple[FingerprintViolation, ...], StrataError]:
    """CVEFP001: every `CveFingerprint.cwe_id` must join a real `WeaknessEntry`
    in `cwe_catalog` (default: `CWE_CATALOG + CWE_TOP_25_CATALOG +
    QUALITY_CATALOG`) -- a fingerprint citing an unknown/renamed/removed CWE
    id fails loudly rather than silently drifting (module docstring, mirroring
    `WeaknessEntry.capability_kind`'s join discipline to `_effects.py::
    _may_kind`)."""
    cataloged = {entry.id for entry in cwe_catalog}
    violations = tuple(
        _drift_violation(entry)
        for entry in fingerprints
        if entry.cwe_id not in cataloged
    )
    _log.info(
        "cve_fingerprint: checked %d fingerprint(s) against %d cwe catalog "
        "entries -> %d violation(s)",
        len(fingerprints),
        len(cataloged),
        len(violations),
    )
    return Ok(violations)


__all__ = [
    "CVE_FINGERPRINTS",
    "CVE_FINGERPRINT_VIEWS",
    "CveFingerprint",
    "FingerprintViolation",
    "check_fingerprint_catalog_drift",
]
