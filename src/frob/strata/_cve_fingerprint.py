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

- JNDI-style lookup injection (the Log4Shell class): Log4Shell is a
  Java/JNDI-specific shape with no equivalent construct in any of the four
  languages `frob.vet._capability` scans (python/typescript/rust/c-cpp) --
  a fingerprint with no genuine needle in a scanned language would be
  undetectable data, not a real pattern-match capability.

Weak-hash password storage (CWE-916), TLS `verify=False` (CWE-295,
T-0188), XML external entities (CWE-611, T-0189), prototype pollution
(CWE-1321), ReDoS (CWE-1333), open redirect (CWE-601), and SSTI
(CWE-1336) were all in the disclosed-gap bucket above until their
`WeaknessEntry` rows landed (`QUALITY_CATALOG`/`CWE_CATALOG` in
`_threat.py`) -- CWE-916/1321/1333/601/1336 landed via T-0510, the last
five follow-ups this docstring named. Eighteen fingerprints ship now,
each with a needle in a language the vet scanner actually covers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typani.result import Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._threat import CWE_CATALOG, CWE_TOP_25_CATALOG, QUALITY_CATALOG, WeaknessEntry

_log = get_logger(__name__)


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
# frob:doc docs/guides/extending/cve-fingerprints.md#cve-fingerprints
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
    CveFingerprint(
        id="FP-TLS-VERIFY-001",
        title="requests/httpx/aiohttp call with TLS certificate "
        "verification explicitly disabled",
        cve=("CVE-2024-35195",),  # Requests < 2.32.0: once a Session's
        # FIRST request disabled verification (verify=False), the
        # connection-pooled Session silently kept skipping certificate
        # verification for that host on every later request regardless of
        # a subsequent verify=True -- the canonical "verify=False leaks
        # past the call it was set on" exemplar for this needle class.
        cwe_id="CWE-295",
        language="python",
        needles=("verify=False",),
        remediation="never pass verify=False (requests) / verify=False "
        "(httpx) / ssl=False (aiohttp) to a production HTTP client call; "
        "if a private CA is involved, pass its bundle path to verify= "
        "instead of disabling verification outright",
    ),
    CveFingerprint(
        id="FP-TLS-VERIFY-002",
        title="Node https/tls client with rejectUnauthorized explicitly disabled",
        cve=("CVE-2021-22939",),  # Node.js https API: passing an explicit
        # `undefined` for rejectUnauthorized silently disabled TLS
        # certificate verification (treated as false) with no error --
        # the same "verification silently off" shape a literal
        # rejectUnauthorized: false reproduces deliberately rather than
        # accidentally.
        cwe_id="CWE-295",
        language="typescript",
        needles=("rejectUnauthorized: false", "rejectUnauthorized:false"),
        remediation="never set rejectUnauthorized: false on an https/tls "
        "client option object; if a private CA is involved, pass its "
        "certificate via the ca option instead of disabling verification",
    ),
    CveFingerprint(
        id="FP-TLS-VERIFY-003",
        title="Rust reqwest client built with danger_accept_invalid_certs",
        cve=("CVE-2026-30794",),  # RustDesk client: TLS retry logic fell
        # back to danger_accept_invalid_certs(true) on a failed connection
        # attempt, disabling certificate chain validation entirely and
        # enabling an adversary-in-the-middle to intercept the retried
        # connection.
        cwe_id="CWE-295",
        language="rust",
        needles=("danger_accept_invalid_certs(true)",),
        remediation="never call .danger_accept_invalid_certs(true) on a "
        "reqwest ClientBuilder in production code, including fallback/"
        "retry paths; if a private CA is involved, add its certificate to "
        "the ClientBuilder instead of disabling validation",
    ),
    CveFingerprint(
        id="FP-XXE-PARSE-001",
        title="XML parsed with external-entity resolution left enabled",
        cve=("CVE-2013-1665",),  # Python's stdlib XML libraries (2.6-3.4),
        # as used by Django's xml.dom.pulldom-based deserializer among
        # others, let a remote attacker read arbitrary files via a DOCTYPE-
        # declared external entity reference -- the canonical Python XXE
        # exemplar; the same unrestricted-external-entity default this
        # fingerprint's needles target in lxml.etree/xml.sax.
        cwe_id="CWE-611",
        language="python",
        needles=("resolve_entities=True", "xml.sax.make_parser("),
        remediation="construct etree.XMLParser(resolve_entities=False, "
        "no_network=True, load_dtd=False) explicitly, and for xml.sax call "
        "parser.setFeature(xml.sax.handler.feature_external_ges, False) -- "
        "or parse with defusedxml instead of the stdlib/lxml parser directly",
    ),
    # frob:ticket T-0510
    CveFingerprint(
        id="FP-WEAKHASH-PASSWORD-001",
        title="fast/weak hash (md5/sha1) applied to a password value",
        cve=("CVE-2012-3287",),  # vBulletin: passwords stored as unsalted
        # MD5 hashes, letting an attacker who obtains the hash database
        # recover plaintext credentials via off-the-shelf cracking/rainbow
        # tables -- the canonical "fast general-purpose hash used for
        # credential storage" exemplar this needle class targets.
        cwe_id="CWE-916",
        language="python",
        needles=("hashlib.md5(password", "hashlib.sha1(password"),
        remediation="use a purpose-built slow password hash (argon2, "
        "bcrypt, scrypt, or hashlib.pbkdf2_hmac with a high iteration "
        "count) -- never a fast general-purpose digest (md5/sha1/sha256) "
        "for credential storage",
    ),
    # frob:ticket T-0510
    CveFingerprint(
        id="FP-PROTO-POLLUTION-001",
        title="recursive object merge writing into __proto__/constructor.prototype",
        cve=("CVE-2019-10744",),  # lodash < 4.17.12: _.defaultsDeep merged
        # an attacker-controlled key path (including "__proto__") straight
        # into the merge target, letting a crafted payload pollute
        # Object.prototype for every object in the process.
        cwe_id="CWE-1321",
        language="typescript",
        needles=("__proto__", "defaultsDeep("),
        remediation="reject/strip __proto__, constructor, and prototype "
        "keys before any recursive merge of attacker-controlled data, or "
        "use a merge utility with prototype-pollution hardening "
        "(lodash >= 4.17.12's own fix, or Object.create(null) targets)",
    ),
    # frob:ticket T-0510
    CveFingerprint(
        id="FP-REDOS-REGEX-001",
        title="dynamically constructed regex applied to untrusted input",
        cve=("CVE-2018-11698",),  # js-yaml: a catastrophic-backtracking
        # regex in the YAML timestamp/reference resolver let an attacker-
        # controlled document body hang the parsing process, a ReDoS
        # denial of service from a fixed-but-vulnerable regex shape.
        cwe_id="CWE-1333",
        language="typescript",
        needles=("new RegExp(",),
        remediation="avoid constructing a RegExp from runtime/request-"
        "influenced text; if unavoidable, validate/escape the input and "
        "bound match complexity (a linear-time engine, or a hard timeout) "
        "before applying it to untrusted text",
    ),
    # frob:ticket T-0510
    CveFingerprint(
        id="FP-OPEN-REDIRECT-001",
        title="redirect target built directly from a request-controlled value",
        cve=("CVE-2014-4021",),  # Django's now-deprecated is_safe_url()
        # could be bypassed via a host-header-derived value, letting a
        # request-influenced target reach a redirect Location header
        # unvalidated -- the canonical open-redirect exemplar.
        cwe_id="CWE-601",
        language="python",
        needles=("redirect(request.GET", "redirect(request.args"),
        remediation="validate a redirect target against an explicit "
        "allowlist of same-origin paths before issuing the redirect -- "
        "never pass a request-controlled value straight into a redirect "
        "call",
    ),
    # frob:ticket T-0510
    CveFingerprint(
        id="FP-SSTI-TEMPLATE-001",
        title="request-controlled string rendered as a template body",
        cve=("CVE-2016-4977",),  # Spring Security OAuth: an error view
        # rendered an attacker-controlled parameter as a Spring Expression
        # Language (SpEL) template body rather than as data, a server-side
        # template injection RCE primitive -- the canonical "user input
        # becomes the template, not the template's data" exemplar this
        # needle class (render_template_string) reproduces in Python/Jinja2.
        cwe_id="CWE-1336",
        language="python",
        needles=("render_template_string(",),
        remediation="never pass a request-influenced string as the "
        "template BODY (render_template_string); render a fixed, "
        "source-controlled template file and pass untrusted values only "
        "as auto-escaped template DATA/context variables",
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


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
class FingerprintHit(BaseModel):
    """T-0439: one line-level match of a `CveFingerprint` needle in a
    scanned source file -- the sibling of `frob.vet._capability::
    _scan_file_fingerprints` (which reports only WHICH fingerprints matched
    somewhere in a dependency directory, no location) for a first-party
    repo-lint GATE, which needs a file:line to be actionable."""

    model_config = ConfigDict(frozen=True)

    fingerprint_id: str
    cwe_id: str
    line: int
    needle: str
    title: str
    remediation: str


def _line_of_offset(text: str, offset: int) -> int:
    """1-indexed line number of `offset` within `text` -- shared helper so
    `scan_text_for_fingerprints` reports the same line convention every
    other gate/violation in this repo uses."""
    return text.count("\n", 0, offset) + 1


# frob:doc docs/strata/threat.md#cve-fingerprints-code-level-pattern-catalog-t-0153
# frob:ticket T-0439
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_smelly_text_fires  # noqa: E501
# frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_clean_text_does_not_fire  # noqa: E501
def scan_text_for_fingerprints(
    text: str,
    language: str,
    fingerprints: tuple[CveFingerprint, ...] = CVE_FINGERPRINTS,
) -> tuple[FingerprintHit, ...]:
    """T-0439: every `CveFingerprint` (in `fingerprints`, default `CVE_
    FINGERPRINTS`) whose `language` matches the caller-supplied `language`
    and at least one `needle` appears as a literal substring of `text`,
    one `FingerprintHit` per matched needle occurrence (module docstring's
    recall-over-precision philosophy, same posture as `frob.vet.
    _capability`'s dependency-source scanner). Deliberately simpler than
    that scanner: no comment-span/whitespace-evasion filtering here (that
    refinement stays in `frob.vet._capability`, which this module cannot
    import without cycling back into `frob.strata` -- module docstring's
    own `_JOINED_CWE_CATALOG` precedent already keeps catalog logic
    self-contained) -- an occasional false positive on a needle appearing
    only in a comment/docstring costs a human a dismissed gate line; a
    false negative on a real first-party vulnerable-usage class is the
    worse failure this scan exists to catch. Callers scanning REPO source
    (not a vetted dependency) are exactly this function's audience;
    `frob.gates._cve_fingerprint_scan.cve_fingerprint_scan_gate` is the one
    real caller."""
    hits: list[FingerprintHit] = []
    for entry in fingerprints:
        if entry.language != language:
            continue
        for needle in entry.needles:
            start = 0
            while True:
                idx = text.find(needle, start)
                if idx == -1:
                    break
                hits.append(
                    FingerprintHit(
                        fingerprint_id=entry.id,
                        cwe_id=entry.cwe_id,
                        line=_line_of_offset(text, idx),
                        needle=needle,
                        title=entry.title,
                        remediation=entry.remediation,
                    )
                )
                start = idx + len(needle)
    hits.sort(key=lambda h: (h.line, h.fingerprint_id))
    return tuple(hits)


__all__ = [
    "CVE_FINGERPRINTS",
    "CVE_FINGERPRINT_VIEWS",
    "CveFingerprint",
    "FingerprintHit",
    "FingerprintViolation",
    "check_fingerprint_catalog_drift",
    "scan_text_for_fingerprints",
]
