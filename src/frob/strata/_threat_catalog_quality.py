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
# Phase E (T-0114, docs/strata/threat.md#phasing item E): the anti-pattern
# families table's rows that map onto EXISTING kernel detectables with NO
# new precondition logic -- a `capability_kind` join THREAT002/THREAT003
# already run (dynamic ORM scope reuses the SAME `sql` capability CWE-89
# fires on, just a different cited id/mitigation), or a citation-only entry
# (`capability_kind=None`, the CWE-22/352/798 precedent above) whose actual
# firing/discharge lives in another already-shipped module -- capacity/
# budget arithmetic (T-0066) for the single-dependency-bottleneck row, the
# std.infra immutable/cdn machinery for the static-hosting row -- so THREAT001
# catalog completeness can cite and prove baseline coverage of them without
# THREAT002/THREAT003 re-detecting what those modules already refute.
# Kept in a SEPARATE tuple from `CWE_CATALOG` (not appended to it) so the
# `owasp-top-10` view -- built directly from `CWE_CATALOG`'s ids above --
# never silently grows to include non-OWASP quality rows; a caller checking
# the quality baseline passes this catalog explicitly.
#
# Stored XSS (the table's third security-family row) needs NO catalog
# addition at all: `_discharges_as_chokepoint`'s `NoFlow(src=foreign,
# dst=node_id)` is evaluated over `reachable`, which is already transitive
# -- a foreign flow through an intermediate store to an `html_render` sink
# is the SAME multi-hop path the existing CWE-79 entry already covers, so
# the persistent/two-hop variant is the SAME obligation, not a new one
# (disclosed here rather than duplicated as a second entry with the same
# precondition shape).
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
        # T-0188 (docs/strata/threat.md#cve-fingerprints-code-level-pattern-
        # catalog-t-0153, "curated, not exhaustive"): honest views
        # placement -- neither `CWE_CATALOG` (the verified 8-id `owasp-
        # top-10` transcription) nor `CWE_TOP_25_CATALOG` (the verified
        # 2023 MITRE Top 25 membership, `_CWE_TOP_25_IDS` above -- CWE-295
        # is NOT one of the 25) claims this id without a fresh, dated
        # re-verification against those specific pinned lists; adding it
        # there would silently widen a view whose membership this module's
        # own docstrings describe as independently checked. Cataloged here
        # in `QUALITY_CATALOG` instead (already home to other
        # `family="security"` rows, e.g. CWE-639 above) with NO `QUALITY_
        # VIEWS` membership -- mirrors CWE-639/REL-001's own precedent of a
        # catalog entry that need not belong to any named baseline view
        # (`check_catalog_completeness` is per-view, not "every entry must
        # have a view", `TestQualityFamilies` in test_threat.py). No
        # `capability_kind`: TLS certificate-verification bypass (`verify=
        # False` and its cross-language siblings) is not a `may`-capability
        # auto-instantiation shape (`_effects.py::_may_kind` has no
        # tls-verification kind) -- it is fired exclusively by the
        # `std.cve` fingerprint layer (`_cve_fingerprint.py`'s
        # FP-TLS-VERIFY-* entries) matching the literal disable-verification
        # needle, the SAME "citation-only, discharge lives elsewhere"
        # shape CWE-798/352 already use in `CWE_CATALOG` above.
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

#: T-0171: the union sink taxonomy across EVERY family catalog this module
#: ships (`CWE_CATALOG`/`CWE_TOP_25_CATALOG`/`QUALITY_CATALOG`) -- the
#: single home `check_capability_completeness` classifies a `may`
#: capability kind against, regardless of which family's VIEW is being
#: audited. Before this, `_audit.py::_evaluate_family` passed each family's
#: OWN narrower catalog to `check_capability_completeness`, so a capability
#: kind classified in `CWE_CATALOG` (security) but absent from `QUALITY_
#: CATALOG` (e.g. `exec`, `deserialize`, `fetch_url` -- QUALITY_CATALOG has
#: no entry mapped to those kinds at all, comment above `DEFAULT_BENIGN_
#: CAPABILITIES`) fired THREAT002 against every quality-family view too,
#: demanding a per-repo `BenignCapability` excuse for a capability that is
#: NOT unclassified -- it is simply irrelevant to the quality family's
#: obligation table. Classification ("is this kind a recognized sink
#: ANYWHERE in the taxonomy") and relevance ("does THIS family's catalog
#: fire an obligation for it") are different questions; THREAT001/THREAT003
#: still resolve per-family (a family's obligations are only the entries
#: its own catalog declares), but THREAT002 -- "every capability kind is
#: classified" (threat.md#the-exhaustiveness-proof-the-point, item 2) --
#: was never meant to mean "classified by THIS family's subset of the
#: taxonomy"; the taxonomy itself is one thing, split into per-family
#: catalogs only for view-membership bookkeeping (docs/strata/
#: threat.md#beyond-security-the-anti-pattern-families).
# frob:doc docs/strata/threat.md#phasing
ALL_CATALOG: tuple[WeaknessEntry, ...] = (
    CWE_CATALOG + CWE_TOP_25_CATALOG + QUALITY_CATALOG
)

# frob:doc docs/strata/threat.md#phasing
# The table's remaining rows whose precondition needs GENUINELY new
# detection -- a flow-attribute predicate (`compressed`, `batch`,
# `optimistic`), a boundary-kind predicate over CORS-specific fields
# (`cors origin any` + "carries credentials"), or an endpoint/route
# concept the kernel model has no node/flow field for at all -- rather
# than a join over an existing `capability_kind`, `NoFlow`, or Node/Flow
# attribute the kernel already extracts. Charter law 1 (no new kernel
# primitive) plus this ticket's scope (catalog data + existing-detectable
# plumbing only) means these are cataloged as an explicit, reasoned
# out-of-scope rather than forced through a precondition that does not
# actually exist yet -- an honest gap, not a silent one (docs/strata/
# threat.md#what-is-honestly-not-covered).
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
#: #beyond-security-the-anti-pattern-families): each view's member set is
#: the table's rows for that family, whether discharged by a `QUALITY_
#: CATALOG` entry or explicitly excused by `QUALITY_OUT_OF_SCOPE` --
#: THREAT001 (`check_catalog_completeness`) proves the SAME "every id
#: named or explicitly out-of-scope" exhaustiveness per family, unmodified,
#: by passing the family's view name + `QUALITY_CATALOG` +
#: `QUALITY_OUT_OF_SCOPE` as its `catalog`/`out_of_scope` arguments -- no
#: new checker, per docs/strata/threat.md#phasing item E ("reuses A-C
#: machinery; adds no kernel"). No `compatibility`-family view is stubbed:
#: the charter's concrete anti-pattern table (docs/strata/threat.md
#: #beyond-security-the-anti-pattern-families) names zero compatibility
#: rows, so a `compat-baseline` view would lie about what it checks (the
#: SAME "never stub an unshipped view" rule `VIEWS` above already follows
#: for `cwe-top-25`/`owasp-asvs`/`cwe-1000`).
# frob:doc docs/strata/threat.md#beyond-security-the-anti-pattern-families
QUALITY_VIEWS: dict[str, frozenset[str]] = {
    "web-performance-baseline": frozenset(
        {"PERF-002", "PERF-COMPRESS-001", "PERF-BATCH-001", "PERF-OPTIMISTIC-001"}
    ),
    "reliability-baseline": frozenset({"REL-001"}),
    "web-quality-security-baseline": frozenset(
        {"CWE-639", "SEC-CORS-001", "SEC-ROUTE-AUTHZ-001"}
    ),
}
