"""strata quality-family threat catalog data: `QUALITY_CATALOG`/
`ALL_CATALOG`/`QUALITY_OUT_OF_SCOPE`/`QUALITY_VIEWS` -- the anti-pattern
families table's rows that map onto existing kernel detectables (T-1420
split from `_threat.py`, verbatim relocation -- WHY: pure catalog data,
no runtime check, previously sitting inside the same file as the CWE
catalog and every checker function that reads them both). See
docs/strata/threat.md#beyond-security-the-anti-pattern-families."""

from __future__ import annotations

from ._models import Rung
from ._threat_catalog_cwe import CWE_CATALOG, CWE_TOP_25_CATALOG
from ._threat_models import OutOfScopeEntry, WeaknessEntry

# frob:doc docs/strata/threat.md#beyond-security-the-anti-pattern-families
# see T-0114 for the history behind this
QUALITY_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-639",
        title="Authorization Bypass Through User-Controlled Key "
        "(dynamic ORM/query scoping)",
        cite="https://cwe.mitre.org/data/definitions/639.html",
        family="security",
        capability_kind="sql",  # reuses CWE-89's SAME sql capability join
        mitigation="tenant_scoping",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="REL-001",
        title="Single-dependency bottleneck on a latency-budgeted path",
        cite="docs/strata/breach.md",  # local doc citation: the budget
        # arithmetic this obligation reuses, not a CWE (no CWE id fits a
        # reliability anti-pattern) -- catalog-only, `capability_kind=None`
        # since the actual refutation is the existing capacity/budget
        # machinery (T-0066), not a THREAT002/THREAT003 capability join.
        family="reliability",
        capability_kind=None,
        mitigation="async_or_cached_fallback",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="PERF-002",
        title="Non-statically-hosted content served from compute/origin",
        cite="docs/strata/kernel.md",  # local doc citation: the std.infra
        # immutable/cdn machinery this obligation names, not a CWE.
        family="performance",
        capability_kind=None,
        mitigation="cdn_routing",
        rung=Rung.L3,
    ),
    WeaknessEntry(
        id="CWE-295",
        title="Improper Certificate Validation",
        cite="https://cwe.mitre.org/data/definitions/295.html",
        family="security",
        # see T-0188 for the history behind this
        capability_kind=None,
        mitigation="certificate_verification_enabled",
        rung=Rung.L4,
    ),
    # frob:ticket T-0510
    WeaknessEntry(
        id="CWE-916",
        title="Use of Password Hash With Insufficient Computational Effort",
        cite="https://cwe.mitre.org/data/definitions/916.html",
        family="security",
        # T-0510 (following CWE-295's precedent immediately above): a
        # fast-hash-for-password-storage precondition (hashlib.md5/sha1
        # applied to a credential) is not a `may`-capability
        # auto-instantiation shape either -- fired exclusively by the
        # `std.cve` fingerprint layer's FP-WEAKHASH-* needle, same
        # "citation-only, discharge lives elsewhere" shape.
        capability_kind=None,
        mitigation="strong_password_hash",
        rung=Rung.L4,
    ),
    # frob:ticket T-0510
    WeaknessEntry(
        id="CWE-1321",
        title="Improperly Controlled Modification of Object Prototype "
        "Attributes ('Prototype Pollution')",
        cite="https://cwe.mitre.org/data/definitions/1321.html",
        family="security",
        capability_kind=None,  # T-0510: unguarded recursive merge into an
        # object touching __proto__/constructor/prototype -- a JS/TS-
        # specific object-shape precondition with no `may` capability join;
        # discharged by the `std.cve` fingerprint layer only.
        mitigation="prototype_pollution_guard",
        rung=Rung.L4,
    ),
    # frob:ticket T-0510
    WeaknessEntry(
        id="CWE-1333",
        title="Inefficient Regular Expression Complexity (ReDoS)",
        cite="https://cwe.mitre.org/data/definitions/1333.html",
        family="security",
        capability_kind=None,  # T-0510: catastrophic-backtracking regex
        # applied to attacker-influenced input -- a pattern-shape
        # precondition, not a `may` capability; discharged by the
        # `std.cve` fingerprint layer only.
        mitigation="redos_safe_regex",
        rung=Rung.L4,
    ),
    # frob:ticket T-0510
    WeaknessEntry(
        id="CWE-601",
        title="URL Redirection to Untrusted Site ('Open Redirect')",
        cite="https://cwe.mitre.org/data/definitions/601.html",
        family="security",
        capability_kind=None,  # T-0510: a request-influenced value reaching
        # a redirect Location header unvalidated -- a flow-to-redirect-sink
        # precondition, capability_kind=None the same as CWE-22's
        # flow-to-filesystem-path-sink precedent above; discharged by the
        # `std.cve` fingerprint layer only.
        mitigation="redirect_target_allowlisted",
        rung=Rung.L4,
    ),
    # frob:ticket T-0510
    WeaknessEntry(
        id="CWE-1336",
        title="Improper Neutralization of Special Elements Used in a "
        "Template Engine (Server-Side Template Injection)",
        cite="https://cwe.mitre.org/data/definitions/1336.html",
        family="security",
        capability_kind=None,  # T-0510: user-controlled string rendered as
        # a template BODY rather than template data -- a flow-to-template-
        # sink precondition, no `may` capability join; discharged by the
        # `std.cve` fingerprint layer only.
        mitigation="template_input_not_body",
        rung=Rung.L4,
    ),
)

# frob:doc docs/strata/threat.md#phasing
# see T-0171 for the history behind this
ALL_CATALOG: tuple[WeaknessEntry, ...] = (
    CWE_CATALOG + CWE_TOP_25_CATALOG + QUALITY_CATALOG
)

# frob:doc docs/strata/threat.md#phasing
# see T-4719 for the full rationale
QUALITY_OUT_OF_SCOPE: tuple[OutOfScopeEntry, ...] = (
    OutOfScopeEntry(
        id="PERF-COMPRESS-001",
        reason="uncompressed JSON needs a `size`-threshold + "
        "structured-payload precondition over `Flow.size`/`Flow.transport` "
        "the kernel model carries but no phase-E check yet interprets as a "
        "compression obligation -- new precondition logic, out of T-0114 scope",
        caught_by="none -- no phase-E check interprets a compression "
        "obligation yet; not compensated elsewhere (T-0114 follow-up)",
    ),
    OutOfScopeEntry(
        id="PERF-BATCH-001",
        reason="one-at-a-time DB writes needs a per-item-vs-batch write "
        "cardinality distinction the kernel model does not carry on `Flow` "
        "today (no collection-cardinality attribute) -- new precondition, "
        "out of T-0114 scope",
        caught_by="none -- kernel has no collection-cardinality attribute "
        "on `Flow`; not compensated elsewhere (T-0114 follow-up)",
    ),
    OutOfScopeEntry(
        id="PERF-OPTIMISTIC-001",
        reason="un-optimistic rendering needs a synchronous `waits_for` "
        "render-to-response edge concept the kernel model has no field for "
        "-- new precondition, out of T-0114 scope",
        caught_by="none -- kernel has no synchronous `waits_for` render-to-"
        "response edge concept; not compensated elsewhere (T-0114 follow-up)",
    ),
    OutOfScopeEntry(
        id="SEC-CORS-001",
        reason="wide-open CORS needs a `cors origin any` boundary predicate "
        "cross-checked against the flow's data label carrying credentials "
        "-- a new boundary-kind predicate over CORS-specific fields the "
        "kernel model has no vocabulary for yet, out of T-0114 scope",
        caught_by="none -- kernel has no CORS-specific boundary-kind "
        "predicate vocabulary; not compensated elsewhere (T-0114 follow-up)",
    ),
    OutOfScopeEntry(
        id="SEC-ROUTE-AUTHZ-001",
        reason="loose backend URL rules (missing route-authorization, "
        "foreign-influenced redirect target) needs an endpoint/route "
        "concept and a redirect-target-taint precondition the kernel model "
        "has no field for -- new precondition, out of T-0114 scope",
        caught_by="none -- kernel has no endpoint/route + redirect-target-"
        "taint concept; not compensated elsewhere (T-0114 follow-up)",
    ),
)

#: Baseline VIEWS for the anti-pattern families (docs/strata/threat.md
# frob:doc docs/strata/threat.md#beyond-security-the-anti-pattern-families
# see T-4719 for the full rationale
QUALITY_VIEWS: dict[str, frozenset[str]] = {
    "web-performance-baseline": frozenset(
        {"PERF-002", "PERF-COMPRESS-001", "PERF-BATCH-001", "PERF-OPTIMISTIC-001"}
    ),
    "reliability-baseline": frozenset({"REL-001"}),
    "web-quality-security-baseline": frozenset(
        {"CWE-639", "SEC-CORS-001", "SEC-ROUTE-AUTHZ-001"}
    ),
}
