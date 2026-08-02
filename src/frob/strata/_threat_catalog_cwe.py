"""strata `std.cwe` catalog data: the OWASP Top-10 subset (`CWE_CATALOG`)
and CWE Top-25 subset (`CWE_TOP_25_CATALOG`/`CWE_TOP_25_OUT_OF_SCOPE`),
plus their view memberships (`VIEWS`/`CWE_TOP_25_VIEWS`) (T-1420 split
from `_threat.py`, verbatim relocation -- WHY: pure catalog data, no
runtime check, previously sitting inside the same file as the quality
catalog and every checker function that reads them both). See
docs/strata/threat.md#the-catalog-stdcwe for what these entries mean."""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive PII012 reason="CWE catalog entry prose names credential/secret weakness categories (CWE-798 etc.); catalog DATA about vulnerability classes, not a PII-carrying surface"  # noqa: E501

from __future__ import annotations

from ._models import Rung
from ._threat_models import OutOfScopeEntry, WeaknessEntry

# frob:doc docs/strata/threat.md#the-catalog-stdcwe
# The OWASP Top-10 subset shipped as phase-A data (docs/strata/threat.md
# #phasing "the OWASP Top-10 subset as data"). Every precondition/mitigation
# pair below is transcribed from the charter's "core reframe" table, which
# itself cites MITRE CWE ids -- the pins/digest-verified ingestion pipeline
# the charter's closing section describes is a build-step follow-up (out of
# scope here; noted as a cut, not silently dropped).
CWE_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-79",
        title="Improper Neutralization of Input During Web Page Generation",
        cite="https://cwe.mitre.org/data/definitions/79.html",
        capability_kind="html_render",
        mitigation="output_encoding",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-89",
        title="Improper Neutralization of Special Elements used in an SQL Command",
        cite="https://cwe.mitre.org/data/definitions/89.html",
        capability_kind="sql",
        mitigation="parameterization",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-78",
        title="Improper Neutralization of Special Elements used in an OS Command",
        cite="https://cwe.mitre.org/data/definitions/78.html",
        capability_kind="exec",
        mitigation="argument_confinement",
        rung=Rung.L4,
    ),
    # T-0401 (docs/audits/strata.md G3): `eval` was globally
    # `BenignCapability`-excused with the (false) reason "no CWE_CATALOG
    # entry targets dynamic code evaluation" -- `CWE_TOP_25_CATALOG`'s
    # CWE-94 IS that entry (joined to `eval` there too, same section), but
    # `owasp-top-10` (this catalog, `VIEWS`) does not include CWE-94 at all
    # (G6: the default security view is narrower than cwe-top-25, a
    # SEPARATE disclosed gap, not fixed here). So `eval` also needs a join
    # WITHIN this catalog's own vocabulary for THREAT002 to classify it
    # under the default view -- CWE-78 is the closest existing id (a code-
    # execution sink, same "kernel model does not distinguish an OS-command
    # sink from a code-eval sink" reasoning CWE-94's own `exec` join already
    # uses), so a second row shares its id with a different
    # `capability_kind`, the SAME multi-kind-per-weakness convention
    # CWE-89/CWE-639 already establish for `sql`.
    WeaknessEntry(
        id="CWE-78",
        title="Improper Neutralization of Special Elements used in an OS Command",
        cite="https://cwe.mitre.org/data/definitions/78.html",
        capability_kind="eval",
        mitigation="argument_confinement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-22",
        title="Improper Limitation of a Pathname to a Restricted Directory",
        cite="https://cwe.mitre.org/data/definitions/22.html",
        capability_kind=None,  # flow-to-filesystem-path-sink precondition, not a
        # capability kind the charter's auto-instantiate table lists (phase B/C
        # sink taxonomy territory, docs/strata/threat.md#capabilities-drag-in
        # -obligations)
        mitigation="path_confinement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-918",
        title="Server-Side Request Forgery (SSRF)",
        cite="https://cwe.mitre.org/data/definitions/918.html",
        capability_kind="fetch_url",
        mitigation="allowlist_mediation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-502",
        title="Deserialization of Untrusted Data",
        cite="https://cwe.mitre.org/data/definitions/502.html",
        capability_kind="deserialize",
        mitigation="schema_validation",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-922",
        title="Insecure Storage of Sensitive Information",
        cite="https://cwe.mitre.org/data/definitions/922.html",
        capability_kind="client_storage",
        mitigation="clearance_boundary",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-352",
        title="Cross-Site Request Forgery (CSRF)",
        cite="https://cwe.mitre.org/data/definitions/352.html",
        capability_kind=None,  # state-changing-endpoint precondition, not a
        # capability kind; phase B/C sink taxonomy territory
        mitigation="anti_csrf_token",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-798",
        title="Use of Hard-coded Credentials",
        cite="https://cwe.mitre.org/data/definitions/798.html",
        capability_kind=None,  # secret-resting-at-low-clearance precondition,
        # already the lattice's own clearance-violation refusal; no capability
        # kind fires it
        mitigation="clearance_boundary",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-611",
        title="Improper Restriction of XML External Entity Reference",
        cite="https://cwe.mitre.org/data/definitions/611.html",
        capability_kind=None,  # T-0189 (T-0153 review follow-up): a
        # parser-configuration precondition (an XML parser resolving a
        # DOCTYPE-declared external entity), not a `may` atom KIND the
        # charter's capability-instantiation table lists -- the same
        # "citation-only, capability_kind=None" shape CWE-22/352/798 above
        # already use for a precondition the kernel has no auto-instantiate
        # join for yet; still cataloged so THREAT001 can cite it and
        # `_cve_fingerprint.py`'s CVEFP001 drift-lock can join a fingerprint
        # against it.
        mitigation="external_entity_disabled",
        rung=Rung.L4,
    ),
)

#: T-0143/T-0345 (docs/strata/threat.md#the-catalog-stdcwe): the
#: `cwe-top-25` view, transcribed from the 2025 MITRE CWE Top 25 Most
#: Dangerous Software Weaknesses (https://cwe.mitre.org/top25/archive/2025/
#: 2025_cwe_top25.html, pinned release year 2025 -- T-0345 bumped this from
#: the stale 2023 pin two releases behind; staleness review against a newer
#: release is the charter's obligation, docs/strata/threat.md#the-catalog-
#: stdcwe "a versioned vocabulary pack ... pinned to a MITRE CWE release ...
#: staleness past a review bound is a gate warning"). Seven of the 25 ids
#: are already cataloged in `CWE_CATALOG` above (CWE-79/89/78/22/918/502/
#: 352) -- reused here, not duplicated (charter: no duplication). Two more
#: are genuinely new obligations (`CWE_TOP_25_CATALOG`, below --
#: `capability_kind` where the charter's instantiation semantics apply):
#: CWE-94 (unchanged from the 2023 pin, reuses CWE-78's `exec` join) and
#: CWE-639 (2025-list-new; reuses `QUALITY_CATALOG`'s existing `sql`-join
#: entry rather than duplicating it, the SAME disclosed-reuse convention
#: CWE-94 already follows). The remaining 16 are honest `OutOfScopeEntry`
#: rows (`CWE_TOP_25_OUT_OF_SCOPE`) whose preconditions the kernel model
#: has no vocabulary for yet: memory-safety ids (no pointer/buffer/
#: allocator model -- now six of them: CWE-787/416/125/476 carried over
#: plus 2025-list-new CWE-120/121/122, all buffer-overflow variants of the
#: SAME missing buffer/bounds model), an authn/authz-boundary group (no
#: endpoint/route + authn/authz predicate concept, same gap
#: `SEC-ROUTE-AUTHZ-001` above already names -- CWE-862/863/306 carried
#: over plus 2025-list-new CWE-284 (the generic parent of CWE-862/863 with
#: no precondition of its own, the SAME generic-parent shape CWE-20
#: already discloses) and CWE-200 (2025-list-new, `Exposure of Sensitive
#: Information`; docs/design/registry/weaknesses.yaml's independent
#: CWE-1000 disposition sweep classifies this id the same way,
#: `out-of-scope:authn-authz-boundary-predicate`, cross-checked here to
#: avoid re-litigating a judgment that sweep already made)), a file-upload
#: id (no content-type-validation sink), a generic-input-validation id (no
#: structural precondition, same "needs hand-written assert claims" class
#: as CWE-840, docs/strata/threat.md#what-is-honestly-not-covered), a
#: duplicate-coverage id (CWE-77, the generic parent of CWE-78's already-
#: cataloged OS-command instance -- disclosed as non-duplicated, the SAME
#: discipline the module docstring above applies to stored XSS), and one
#: 2025-list-new resource-exhaustion id (CWE-770, needs a resource-
#: allocation/rate-limiting model the kernel does not carry). Dropped from
#: the 2023 pin (no longer 2025-list members, so no longer `cwe-top-25`
#: obligations at all -- their `OutOfScopeEntry`/`CWE_CATALOG` rows are
#: removed, not archived, since this view's membership is the CITED
#: release's, not a running union of every release ever pinned):
#: CWE-798 (still in `CWE_CATALOG` above, just no longer a top-25 member),
#: CWE-287/190/119/362/269/276 (were `OutOfScopeEntry` rows here only,
#: removed outright).
# frob:doc docs/strata/threat.md#the-catalog-stdcwe
# frob:ticket T-0143
# frob:ticket T-0345
# frob:ticket T-0401
# frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_is_classified_not_benign_excused  # noqa: E501
# frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_fires_a_real_cwe94_obligation  # noqa: E501
# frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_discharges_with_a_real_mitigation_claim  # noqa: E501
CWE_TOP_25_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-94",
        title="Improper Control of Generation of Code ('Code Injection')",
        cite="https://cwe.mitre.org/data/definitions/94.html",
        capability_kind="exec",  # reuses CWE-78's SAME exec capability join:
        # the kernel model does not distinguish an OS-command sink from a
        # code-eval sink, so both weaknesses fire on the same precondition,
        # exactly the CWE-639/CWE-89 "sql" precedent below.
        mitigation="code_execution_sandboxing",
        rung=Rung.L4,
    ),
    # T-0401 (docs/audits/strata.md G3): `eval` was globally
    # `BenignCapability`-excused with the reason "no CWE_CATALOG entry
    # targets dynamic code evaluation as a sink" -- false; CWE-94 IS
    # exactly that entry, it was simply never joined to the `eval`
    # capability kind (only to `exec`). A SECOND `WeaknessEntry` row
    # sharing CWE-94's id but a different `capability_kind` is the SAME
    # multi-kind-per-weakness convention `capability_kind="sql"` already
    # uses twice (`CWE-89` above, `CWE-639`/`QUALITY_CATALOG`'s own `sql`
    # entry) -- `_entries_by_capability_kind` keys by kind, not id, so both
    # rows correctly fire the identical `weakness:CWE-94:<node>` discharge
    # obligation (one Claim satisfies both firings). Dropping the benign
    # excuse means a node/file with dynamic `eval`/`compile`/`__import__`
    # now fires a REAL, dischargeable THREAT002/THREAT003 obligation
    # instead of passing silently.
    WeaknessEntry(
        id="CWE-94",
        title="Improper Control of Generation of Code ('Code Injection')",
        cite="https://cwe.mitre.org/data/definitions/94.html",
        capability_kind="eval",
        mitigation="code_execution_sandboxing",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-639",
        title="Authorization Bypass Through User-Controlled Key",
        cite="https://cwe.mitre.org/data/definitions/639.html",
        capability_kind="sql",  # reuses QUALITY_CATALOG's SAME sql
        # capability join (see that entry's comment) -- disclosed reuse,
        # not duplication, the SAME convention CWE-94 above follows;
        # `cwe-top-25` needs its own entry since `THREAT001` checks
        # `CWE_CATALOG + CWE_TOP_25_CATALOG`, not `QUALITY_CATALOG`.
        mitigation="tenant_scoping",
        rung=Rung.L4,
    ),
)

#: T-0143/T-0345: the 16 CWE Top 25 (2025) ids whose precondition the
#: kernel cannot yet express, each with a SPECIFIC missing-concept reason
#: (never a generic "not supported") -- see `CWE_TOP_25_CATALOG`'s comment
#: above for the grouping this follows.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:ticket T-0143
# frob:ticket T-0345
CWE_TOP_25_OUT_OF_SCOPE: tuple[OutOfScopeEntry, ...] = (
    OutOfScopeEntry(
        id="CWE-787",
        reason="out-of-bounds write needs a buffer/allocation/bounds model "
        "the kernel has no vocabulary for -- it models data flow and trust, "
        "not memory layout",
        caught_by=(
            "none -- kernel has no buffer/allocation/bounds model; not compensated by "
            "any other frob mechanism (documented gap)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-416",
        reason="use-after-free needs an allocator/object-lifetime model the "
        "kernel does not carry -- no node/flow concept of allocation or "
        "deallocation exists",
        caught_by=(
            "none -- kernel has no allocator/object-lifetime model; not compensated by "
            "any other frob mechanism (documented gap)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-20",
        reason="improper input validation names no structural precondition "
        "of its own (it is the generic parent of the specific sink-typed "
        "injection ids already cataloged) -- needs a hand-written `assert` "
        "claim per site, the same class as CWE-840, docs/strata/threat.md"
        "#what-is-honestly-not-covered",
        caught_by=(
            "the specific sink-typed injection CWEs already in CWE_CATALOG (e.g. "
            "CWE-79/CWE-89/CWE-78) that this generic parent's instances actually fire "
            "through"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-125",
        reason="out-of-bounds read needs the same buffer/bounds model "
        "CWE-787 needs and the kernel does not carry",
        caught_by=(
            "none -- kernel has no buffer/bounds model (same gap as CWE-787); not "
            "compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-434",
        reason="unrestricted dangerous file upload needs a file-upload sink "
        "and a content-type-validation boundary predicate the kernel model "
        "has no field for",
        caught_by=(
            "none -- kernel has no file-upload sink / content-type-"
            "validation boundary; not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-862",
        reason="missing authorization needs an endpoint/route concept and "
        "an authz-boundary predicate the kernel model has no field for -- "
        "the same gap SEC-ROUTE-AUTHZ-001 above already names",
        caught_by=(
            "none -- kernel has no endpoint/route + authz-boundary concept; not "
            "compensated elsewhere (documented gap)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-476",
        reason="NULL pointer dereference needs a pointer/nullability model "
        "the kernel does not carry -- it has no concept of a dereferenceable "
        "reference at all",
        caught_by=(
            "none -- kernel has no pointer/nullability model; not "
            "compensated elsewhere (documented gap)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-77",
        reason="generic command injection is the parent category of "
        "CWE-78's already-cataloged OS-command instance, firing on the SAME "
        "exec-capability precondition with no kernel-detectable distinction "
        "-- a second entry would duplicate the identical fire path rather "
        "than name a genuinely distinct obligation, the same non-"
        "duplication disclosure this module applies to stored XSS",
        caught_by=(
            "CWE-78 in CWE_CATALOG (the already-cataloged OS-command "
            "instance firing on the identical exec-capability precondition)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-306",
        reason="missing authentication for a critical function needs the "
        "same endpoint/route + authn-boundary concept CWE-862 needs and "
        "the kernel does not carry",
        caught_by=(
            "none -- kernel has no endpoint/route + authn-boundary "
            "concept (same gap as CWE-862); not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-863",
        reason="incorrect authorization needs the same endpoint/route + "
        "authz-boundary concept CWE-862 needs and the kernel does not carry",
        caught_by=(
            "none -- kernel has no endpoint/route + authz-boundary "
            "concept (same gap as CWE-862); not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-120",
        reason="classic buffer overflow needs the same buffer/bounds model "
        "CWE-787/125 need and the kernel does not carry",
        caught_by=(
            "none -- kernel has no buffer/bounds model (same gap as CWE-787/125); not "
            "compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-121",
        reason="stack-based buffer overflow needs the same buffer/bounds "
        "model CWE-787/125/120 need and the kernel does not carry",
        caught_by=(
            "none -- kernel has no buffer/bounds model (same gap as CWE-787/125/120); "
            "not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-122",
        reason="heap-based buffer overflow needs the same buffer/bounds "
        "model CWE-787/125/120 need and the kernel does not carry",
        caught_by=(
            "none -- kernel has no buffer/bounds model (same gap as CWE-787/125/120); "
            "not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-284",
        reason="improper access control names no structural precondition "
        "of its own (it is the generic parent of CWE-862/863's specific "
        "authz-boundary preconditions) -- needs the same endpoint/route + "
        "authz-boundary concept CWE-862/863 need, the SAME generic-parent "
        "disclosure CWE-20 already applies to input validation",
        caught_by=(
            "none -- generic parent of CWE-862/863, both themselves out-of-scope for "
            "the same endpoint/route + authz-boundary gap; not compensated elsewhere"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-770",
        reason="allocation of resources without limits or throttling needs "
        "a resource-budget/rate-limiting model the kernel does not carry -- "
        "it has no concept of a bounded allocation or a throttle boundary",
        caught_by=(
            "none -- kernel has no resource-budget/rate-limiting model; "
            "not compensated elsewhere (documented gap)"
        ),
    ),
    OutOfScopeEntry(
        id="CWE-200",
        reason="exposure of sensitive information to an unauthorized actor "
        "needs an endpoint/route + authz-boundary predicate concept the "
        "kernel model has no field for -- the same gap SEC-ROUTE-AUTHZ-001/"
        "CWE-862/863/284 above already name; docs/design/registry/"
        "weaknesses.yaml's independent CWE-1000 disposition sweep "
        "classifies this id the same way (out-of-scope:authn-authz-"
        "boundary-predicate)",
        caught_by=(
            "none -- kernel has no endpoint/route + authz-boundary "
            "concept (same gap as CWE-862/863/284); not compensated "
            "elsewhere"
        ),
    ),
)

#: T-0143/T-0345: the full 25-id `cwe-top-25` membership, literal so
#: THREAT001 checks it against the CITED release regardless of which
#: catalog tuples a caller passes (mirrors `owasp-top-10`'s derive-from-
#: `CWE_CATALOG` convenience being unavailable here since this view spans
#: two catalog tuples, docs/strata/threat.md#the-catalog-stdcwe).
_CWE_TOP_25_IDS: frozenset[str] = frozenset(
    {
        "CWE-79",
        "CWE-89",
        "CWE-352",
        "CWE-862",
        "CWE-787",
        "CWE-22",
        "CWE-416",
        "CWE-125",
        "CWE-78",
        "CWE-94",
        "CWE-120",
        "CWE-434",
        "CWE-476",
        "CWE-121",
        "CWE-502",
        "CWE-122",
        "CWE-863",
        "CWE-20",
        "CWE-284",
        "CWE-200",
        "CWE-306",
        "CWE-918",
        "CWE-77",
        "CWE-639",
        "CWE-770",
    }
)

#: Baseline VIEWS: the id set a selected view holds the catalog to. Phase A
#: ships one view, the OWASP Top-10 subset actually cataloged above;
#: `owasp-asvs`/`cwe-1000` remain deliberately unstubbed -- see docs/
#: strata/threat.md#the-catalog-stdcwe for the recorded decision (ASVS is a
#: verification standard, not a weakness list; cwe-1000 is a ~900-entry
#: research view where transcription without kernel preconditions would be
#: out-of-scope spam) -- so THREAT001 never lies about a view it cannot
#: check. `cwe-top-25` (T-0143) is intentionally NOT merged into this dict:
#: `_audit.py::DEFAULT_SECURITY_VIEWS` iterates `tuple(VIEWS)` and checks
#: every member against the bare `CWE_CATALOG` default -- exactly the
#: `QUALITY_CATALOG`/`QUALITY_VIEWS` split's rationale above, reused here
#: since `cwe-top-25` needs the combined `CWE_CATALOG + CWE_TOP_25_CATALOG`
#: catalog, not the default alone (see `CWE_TOP_25_VIEWS` below).
# frob:doc docs/strata/threat.md#the-catalog-stdcwe
VIEWS: dict[str, frozenset[str]] = {
    "owasp-top-10": frozenset(entry.id for entry in CWE_CATALOG),
}

#: T-0143: `cwe-top-25`'s view table, kept separate from `VIEWS` (comment
#: above) -- a caller checking the Top-25 baseline passes this explicitly,
#: mirroring `QUALITY_VIEWS`'s convention exactly.
# frob:doc docs/strata/threat.md#the-catalog-stdcwe
# frob:ticket T-0143
CWE_TOP_25_VIEWS: dict[str, frozenset[str]] = {
    "cwe-top-25": _CWE_TOP_25_IDS,
}
