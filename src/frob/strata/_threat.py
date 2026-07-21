"""strata obligation catalog phases A-C: `std.cwe` + weakness/capability
grammar + THREAT001-THREAT005 (docs/strata/threat.md,
T-0109/T-0111/T-0112/T-0113).

Phase A (T-0111, design-level only, docs/strata/threat.md#phasing): a CWE
weakness is cataloged as structured data (`WeaknessEntry.cite` names the
authoritative source url, never hand-transcribed); a capability kind on a
`Node.may` atom auto-instantiates the weakness obligations the charter's
capability table maps it to. THREAT001 (catalog completeness): every CWE
id a selected baseline VIEW names has a catalog entry or an explicit
`out_of_scope` entry. THREAT003 (discharge completeness): every FIRED
obligation (a node declares the `may` kind that drags it in) has a
corresponding `Claim`, evaluated at or above the catalog's required rung,
never REFUTED, and -- if assumed -- owned with a review date.

Phase B (T-0112, docs/strata/threat.md#phasing item B) adds THREAT002
(precondition/capability completeness), still model-level: every
capability kind a node declares via `may` is CLASSIFIED -- it names a
sink the catalog recognizes (`_entries_by_capability_kind`, the same join
`_fired_obligations` uses) or is explicitly excused by a `BenignCapability` entry,
mirroring THREAT001's `OutOfScopeEntry`. Unclassified is a violation,
deny-by-default (charter law 2) -- the "never forget" mechanism (threat.md
#the-exhaustiveness-proof-the-point, item 2).

Phase C (T-0113, docs/strata/threat.md#phasing item C) closes the
code-level half phase B deferred, in two independent pieces:

1. Code-level capability classification/declaration (THREAT004/THREAT005):
   `check_effect_completeness` joins `_effects.py::extract_effects`'s
   observed net/fs/exec sinks into the SAME taxonomy join
   (`_entries_by_capability_kind`) THREAT002 and `_fired_obligations`
   already use. An observed sink whose owning node declares no matching
   `may` capability is THREAT004 (reusing `check_capability_conformance`'s
   join, not re-detecting it); an observed sink whose kind the catalog
   does not recognize (and no `BenignCapability` excuses it) is THREAT005
   -- the code-level mirror of THREAT002's model-level "every capability
   ... is classified" (threat.md#the-exhaustiveness-proof-the-point, item
   2). Still v0's kind-only join (`_effects.py`'s own documented scope
   cut: no destination-scoped capability grammar yet).

2. Mitigation chokepoint verification (still THREAT003, tightened twice):
   a Claim named `weakness:<cwe-id>:<node-id>` used to be accepted as a
   discharge purely by existing at the right rung -- it could be ANY
   claim body, "declared somewhere" (threat.md#phasing item C) rather
   than a proof the mitigation actually interposes on every path from a
   foreign source to the firing node.

   Round 1 required the body to be a `NoFlow(src=<foreign>, dst=<node_id>)`
   claim -- the shape `_eval_noflow` (`_claims.py`) already proves over the
   closure engine's boundary-aware `reachable` (a flow carrying ANY
   `Boundary` stops the influence walk, docs/strata/kernel.md). Review
   round 2 caught the gap this leaves: `reachable`'s barrier test does not
   look at a boundary's `direction`/`predicate` at all, so a PROVED
   `NoFlow` says only "SOME boundary sits on every path" -- a `declassify`
   boundary with an unrelated `predicate` (e.g. `"legal_review_signed_off"`
   discharging a CWE-79 `output_encoding` obligation) proves the SAME
   `NoFlow` a genuine `endorse output_encoding` boundary would. "Declared
   somewhere" had shrunk from "any claim" to "any boundary of any kind",
   still not the catalog's actual `needs mitigation <name>` requirement.

   `_mitigation_is_chokepoint` closes this: it isolates the boundaries
   that carry the catalog's EXACT required mitigation
   (`direction=ENDORSE` and `predicate == entry.mitigation`,
   `_matching_boundary_ids`) and re-evaluates the SAME `NoFlow` claim on a
   model copy with every OTHER boundary removed (`_restricted_to_
   boundaries`) -- still the SAME `evaluate_claims`/`_eval_noflow`/
   `reachable` call, no new closure primitive. If the claim still
   PROVES/EVIDENCES over that restricted model, the correctly-kinded
   boundaries alone are sufficient to cut every path the closure walks:
   a genuine chokepoint, not a boundary of convenience. Quantifier
   documented on `_mitigation_is_chokepoint` itself (not "every path is
   independently proved cut by a matching boundary" -- see its docstring
   for the precise cut this makes and does not make).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._claims import evaluate_claims
from ._code_binding import CodeBinding, is_managed
from ._effects import (
    CapabilityViolation,
    ObservedEffect,
    _may_kind,
    check_capability_conformance,
    extract_effects,
)
from ._errors import StrataError
from ._models import (
    BoundaryDirection,
    Claim,
    ClaimResult,
    KernelModel,
    Node,
    NoFlow,
    Rung,
    Verdict,
)

_log = get_logger(__name__)

#: Evidence ladder order, low to high (docs/strata/evidence.md); reused to
#: compare a declared claim's required_rung against a catalog entry's.
_RUNG_ORDER: tuple[Rung, ...] = (Rung.L1, Rung.L2, Rung.L3, Rung.L4, Rung.L5)


# frob:doc docs/strata/threat.md#the-catalog-stdcwe
# frob:doc docs/guides/extending/threat-catalog.md#threat-catalog
class WeaknessEntry(BaseModel):
    """One `std.cwe` catalog entry: a conditional obligation predicated on
    a capability being present in the model (docs/strata/threat.md#the-
    core-reframe). `capability_kind` is the `may` atom KIND (matching
    `_effects.py::_may_kind`'s convention) whose declaration auto-
    instantiates this obligation (docs/strata/threat.md#capabilities-drag-
    in-obligations); `None` when phase A has no capability-driven
    precondition detector for this id yet (CSRF, hardcoded credentials --
    still cataloged for THREAT001, never fired by THREAT003 in phase A).
    """

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "CWE-79"
    title: str
    cite: str  # authoritative source url, never hand-transcribed
    family: str = "security"
    capability_kind: str | None = None
    mitigation: str = ""  # required mitigation/boundary predicate name
    rung: Rung = Rung.L4


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class OutOfScopeEntry(BaseModel):
    """A baseline CWE id explicitly excluded from the catalog, with a
    reason -- satisfies THREAT001 without a `WeaknessEntry` (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point, item 1). `caught_by`
    (T-0381) is mandatory: an exclusion without a named compensating
    control (the gate/rule/mechanism that catches the excused CWE
    elsewhere) is an unaccounted-for gap, not an honest exclusion."""

    model_config = ConfigDict(frozen=True)

    id: str
    reason: str
    caught_by: str = Field(min_length=1)


# frob:doc docs/strata/threat.md#phasing
# frob:doc docs/guides/extending/benign-capabilities.md#benign-capabilities
class BenignCapability(BaseModel):
    """A `may` capability KIND explicitly excused from THREAT002's sink
    taxonomy, with a reason -- mirrors `OutOfScopeEntry` for THREAT001
    (docs/strata/threat.md#phasing item B); an unmapped kind must be
    named here or THREAT002 fails closed on it. `caught_by` (T-0381) is
    mandatory: an excuse without a named compensating control (the gate/
    rule/mechanism that catches the excused capability elsewhere) is an
    unaccounted-for gap, not an honest exclusion."""

    model_config = ConfigDict(frozen=True)

    kind: str
    reason: str = Field(min_length=1)
    caught_by: str = Field(min_length=1)


#: T-0150: `may` capability kinds `_selfconform.py`'s SYS100/SYS101 measure
#: via `frob.vet._capability`'s scanner vocabulary (net/fs-write-derived
#: "fs"/eval/env/ffi/install-hook) that name NO `CWE_CATALOG`/
#: `QUALITY_CATALOG` `capability_kind` at all (the catalog's kinds --
#: html_render/sql/exec/fetch_url/deserialize/client_storage -- are a
#: DIFFERENT, CWE-sink-shaped vocabulary, docs/strata/threat.md#the-
#: catalog-stdcwe). Declaring these on `design/frob.strata`'s nodes (so
#: SYS100/SYS101 can reconcile them) would otherwise fail THREAT002 on
#: every one of them ("matches no sink taxonomy entry") with NO way to
#: excuse it, since `BenignCapability` is a Python-side argument neither
#: `evaluate_exhaustiveness` (`_audit.py`) nor `audit_claim` (`_sysdoc.py`,
#: DOC003's model-side half) wired to a default until now. `exec` IS
#: listed below too, despite having a real `CWE_CATALOG` entry (CWE-78) --
#: `_evaluate_family` (`_audit.py`) passes the SAME `benign` tuple to BOTH
#: the security (`CWE_CATALOG`) and quality (`QUALITY_CATALOG`) family
#: loops, and `QUALITY_CATALOG` has no `exec`-mapped entry at all;
#: `check_capability_completeness`'s `known` set is catalog-derived, so
#: `exec` already being `known` for the security loop makes this entry a
#: no-op there (`excused` is consulted only for kinds NOT already known) --
#: it only takes effect for the quality loop, where it is a genuine gap in
#: `QUALITY_CATALOG`'s vocabulary, not a security exemption.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
DEFAULT_BENIGN_CAPABILITIES: tuple[BenignCapability, ...] = (
    BenignCapability(
        kind="exec",
        reason=(
            "already classified as CWE-78 in CWE_CATALOG (the security "
            "family); this entry only affects the QUALITY_CATALOG loop, "
            "which has no exec-mapped weakness at all -- module docstring "
            "above explains why this is a no-op for the security loop"
        ),
        caught_by=(
            "CWE-78 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
    BenignCapability(
        kind="net",
        reason=(
            "tier-2 net-effect capability (T-0079 _KIND_MAP); no CWE_CATALOG "
            "entry targets bare outbound network calls as a sink on their own "
            "(SSRF/fetch_url is the catalog's closest analog and is a distinct, "
            "already-classified kind)"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets bare outbound network "
            "calls as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="fs",
        reason=(
            "tier-2 filesystem-write capability (T-0079 _KIND_MAP, from vet's "
            "fs-write); no CWE_CATALOG entry targets local filesystem writes "
            "as a sink on their own (CWE-22 path traversal is a distinct, "
            "flow-to-path-sink precondition, capability_kind=None)"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem writes "
            "as a sink on their own; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="fs-read",
        reason=(
            "T-0018 (graphite adoption): tier-2 filesystem-read capability, "
            "the read-only sibling of the fs-write-derived 'fs' kind above "
            "(frob.vet._capability_registry, split so a read-only node is "
            "not forced to declare a write-shaped capability it does not "
            "have); no CWE_CATALOG entry targets local filesystem reads as a "
            "sink on their own, same rationale as 'fs' above"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets local filesystem reads "
            "as a sink on their own (same gap as 'fs'); not compensated "
            "elsewhere"
        ),
    ),
    BenignCapability(
        kind="env",
        reason=(
            "vet dependency-vetting signal (environment-variable read "
            "access); no CWE_CATALOG entry targets environment-variable "
            "reads as a sink"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets environment-variable "
            "reads as a sink; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="ffi",
        reason=(
            "vet dependency-vetting signal (ctypes/extern C usage); no "
            "CWE_CATALOG entry targets FFI/native-extension boundaries as a "
            "sink in v0's catalog"
        ),
        caught_by=(
            "none -- no CWE_CATALOG entry targets FFI/native-extension "
            "boundaries as a sink in v0's catalog; not compensated elsewhere"
        ),
    ),
    BenignCapability(
        kind="install-hook",
        reason=(
            "vet dependency-vetting signal (setuptools packaging install "
            "hooks); no CWE_CATALOG entry targets packaging install hooks as "
            "a sink -- this is a dependency-supply-chain concern `frob vet` "
            "itself already flags, not a CWE-catalog weakness"
        ),
        caught_by=(
            "frob vet's dependency-supply-chain scan -- the mechanism that "
            "already flags packaging install hooks"
        ),
    ),
    # T-0158: `deserialize`/`fetch_url` ARE mapped in `CWE_CATALOG` (CWE-502/
    # CWE-918, the security family) but have NO `QUALITY_CATALOG` entry at
    # all -- same "distinct family, distinct vocabulary" shape the module
    # docstring already explains for `exec`/`net`/`fs` above. Without these
    # two entries the QUALITY_CATALOG loop alone would flag both kinds as
    # unmapped (THREAT002), even though the security loop already accounts
    # for them via a real CWE with a real discharge obligation.
    BenignCapability(
        kind="deserialize",
        reason=(
            "already classified as CWE-502 in CWE_CATALOG (the security "
            "family); QUALITY_CATALOG has no deserialization-mapped entry "
            "at all -- this entry only affects the QUALITY_CATALOG loop"
        ),
        caught_by=(
            "CWE-502 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
    BenignCapability(
        kind="fetch_url",
        reason=(
            "already classified as CWE-918 in CWE_CATALOG (the security "
            "family); QUALITY_CATALOG has no SSRF/fetch-mapped entry at "
            "all -- this entry only affects the QUALITY_CATALOG loop"
        ),
        caught_by=(
            "CWE-918 in CWE_CATALOG (the security family); this entry "
            "only affects the QUALITY_CATALOG loop"
        ),
    ),
)


# frob:doc docs/strata/threat.md#per-repo-benign-capability-declarations
# frob:doc docs/guides/extending/benign-capabilities.md#per-repo-declarations
# frob:ticket T-0017
def load_repo_benign_capabilities(
    root: Path,
) -> Result[tuple[BenignCapability, ...], StrataError]:
    """T-0017 (graphite adoption): the per-repo `.strata`-consuming-repo
    excuse channel `DEFAULT_BENIGN_CAPABILITIES` alone could not provide --
    a consuming repo genuinely has a capability kind (`html_render`,
    `client_storage`, ...) that maps to no `CWE_CATALOG`/`QUALITY_CATALOG`
    sink in ITS model, but the only excuse mechanism was this module's own
    hardcoded Python tuple, which no downstream repo can edit. Reads
    `frob.toml`'s `[[strata.benign_capabilities]]` array of tables (the same
    array-of-tables shape `frob.policy`'s `[[policy.*]]` already uses for
    repo-declared rules) -- each entry needs `kind`, a non-blank `reason`,
    and a non-blank `caught_by` (T-0381: the compensating gate/rule/
    mechanism that catches the excused capability elsewhere, or an honest
    "none" disclosure) (deny-by-default, charter law 2: an excuse without a
    written reason is not honest). Returns `Ok(())` for a missing
    `frob.toml` or a missing `[strata]`/`benign_capabilities` table (no
    repo-declared excuses is a valid, common case, not an error) and
    `Err(StrataError.MalformedBenignConfig)` for a present-but-invalid
    table (unparseable TOML, or an entry missing `kind`/`reason`/
    `caught_by`) -- fails closed rather than silently dropping a malformed
    entry, the same posture `_load_policy`'s sibling loaders take. Callers
    combine the result with
    `DEFAULT_BENIGN_CAPABILITIES` (repo entries are ADDITIONAL excuses, never
    a replacement for the built-in tier-2 vocabulary excuses) before passing
    `benign=` to `evaluate_exhaustiveness`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.info("load_repo_benign_capabilities: no frob.toml at %s", toml_path)
        return Ok(())
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.error(
            "load_repo_benign_capabilities: could not parse %s: %s", toml_path, exc
        )
        return Err(StrataError.MalformedBenignConfig)

    entries = doc.get("strata", {}).get("benign_capabilities", [])
    if not isinstance(entries, list):
        _log.error(
            "load_repo_benign_capabilities: [strata.benign_capabilities] must "
            "be an array of tables, got %s",
            type(entries).__name__,
        )
        return Err(StrataError.MalformedBenignConfig)

    excuses: list[BenignCapability] = []
    for entry in entries:
        try:
            excuses.append(
                BenignCapability(
                    kind=entry["kind"],
                    reason=entry["reason"],
                    caught_by=entry["caught_by"],
                )
            )
        except (KeyError, TypeError, ValidationError) as exc:
            _log.error(
                "load_repo_benign_capabilities: malformed entry in %s: %s",
                toml_path,
                exc,
            )
            return Err(StrataError.MalformedBenignConfig)

    _log.info(
        "load_repo_benign_capabilities: loaded %d repo-declared excuse(s) from %s",
        len(excuses),
        toml_path,
    )
    return Ok(tuple(excuses))


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


def _entries_by_capability_kind(
    catalog: tuple[WeaknessEntry, ...],
) -> dict[str, tuple[WeaknessEntry, ...]]:
    """capability KIND (the `_effects.py::_may_kind` convention) -> the
    `catalog` entries its declaration auto-instantiates (docs/strata/
    threat.md#capabilities-drag-in-obligations). The ONE home this join is
    computed in: `_fired_obligations` (instantiation) and
    `check_capability_completeness` (THREAT002's sink taxonomy) both call
    this over the SAME `catalog` argument they were given, so a caller who
    passes a non-default catalog can never see the two checks diverge
    (charter: no duplication) -- there is no module-level cache keyed to
    `CWE_CATALOG` to go stale against a different catalog."""
    by_kind: dict[str, list[WeaknessEntry]] = {}
    for entry in catalog:
        if entry.capability_kind is not None:
            by_kind.setdefault(entry.capability_kind, []).append(entry)
    return {kind: tuple(entries) for kind, entries in by_kind.items()}


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ThreatViolation(BaseModel):
    """One THREAT001/THREAT002/THREAT003 finding: a rule id, an optional
    CWE id, an optional capability kind, an optional firing node, and a
    human detail -- never a silent gap. THREAT002 sets `capability` and
    leaves `cwe` empty (no CWE is implicated -- the capability itself is
    unclassified); THREAT001/THREAT003 leave `capability` `None`."""

    model_config = ConfigDict(frozen=True)

    rule: str  # "THREAT001" | "THREAT002" | "THREAT003"
    cwe: str = ""
    capability: str | None = None
    node: str | None = None
    detail: str = ""


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
class ThreatReport(BaseModel):
    """Every THREAT001/THREAT003 violation, in rule-then-cwe-then-node order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ThreatViolation, ...] = ()


def _catalog_violation(view: str, cwe_id: str) -> ThreatViolation:
    """THREAT001 violation helper: deny-by-default unaddressed baseline CWE."""
    _log.warning("threat: THREAT001 %s has no catalog or out-of-scope entry", cwe_id)
    return ThreatViolation(
        rule="THREAT001",
        cwe=cwe_id,
        detail=f"baseline view {view!r} names {cwe_id} with no catalog "
        "or out-of-scope entry",
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def check_catalog_completeness(
    view: str,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    views: dict[str, frozenset[str]] | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT001: every CWE id the selected `view` names has a `WeaknessEntry`
    or an `OutOfScopeEntry`; an unaddressed baseline CWE is a violation
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point, item 1).

    Fails closed (`StrataError.UnknownReference`) on a `view` name the
    catalog does not ship -- a typo'd view must never silently pass as
    "nothing to check".
    """
    view_table = views if views is not None else VIEWS
    members = view_table.get(view)
    if members is None:
        _log.error("threat: unknown baseline view %r", view)
        return Err(StrataError.UnknownReference)

    cataloged = {entry.id for entry in catalog}
    excused = {entry.id for entry in out_of_scope}
    # frob:waive PERF004 reason="one sort of the view's member set, not per-iteration"
    ordered_members = sorted(members)
    violations = [
        _catalog_violation(view, cwe_id)
        for cwe_id in ordered_members
        if cwe_id not in cataloged and cwe_id not in excused
    ]
    return Ok(tuple(violations))


def _capability_violation(kind: str, node_id: str) -> ThreatViolation:
    """THREAT002 violation helper: deny-by-default unclassified capability
    kind (docs/strata/threat.md#phasing item B)."""
    _log.warning(
        "threat: THREAT002 capability %r on %s matches no sink taxonomy "
        "entry and no BenignCapability excuse",
        kind,
        node_id,
    )
    return ThreatViolation(
        rule="THREAT002",
        capability=kind,
        node=node_id,
        detail=f"capability kind {kind!r} matches no std.cwe sink taxonomy "
        "entry and no BenignCapability excuse",
    )


# frob:doc docs/strata/threat.md#phasing
# frob:waive ARCH001 reason="body is 9 lines of a single sorted-nodes/sorted-kinds classify-or-flag loop; the rest is the docstring explaining the T-0171 taxonomy-wide classification contract -- splitting the loop would hide, not clarify, the one join it performs" ceiling="40"  # noqa: E501
def check_capability_completeness(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    benign: tuple[BenignCapability, ...] = (),
    taxonomy: tuple[WeaknessEntry, ...] | None = None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT002: every capability kind a node declares via a `may` atom is
    classified -- it names a sink `taxonomy` recognizes (its
    `capability_kind`) or is explicitly excused by a `BenignCapability`;
    an unclassified kind is a violation, deny-by-default (docs/strata/
    threat.md#phasing item B). The model-level half of "every capability
    ... is classified" (threat.md#the-exhaustiveness-proof-the-point,
    item 2); the code-level half is phase C (module docstring).

    `taxonomy` defaults to `catalog` (pre-T-0171 behavior: classify only
    against the SAME catalog whose entries this call's `view` resolves
    obligations from) -- pass `ALL_CATALOG` (or any wider union) explicitly
    when checking a NARROWER per-family catalog (e.g. `QUALITY_CATALOG`)
    so a capability kind classified elsewhere in the taxonomy (security's
    `CWE_CATALOG`) is not misreported as unclassified just because this
    family's own catalog has no entry for it (T-0171: THREAT002 fired in
    quality views for capabilities the taxonomy classifies, just not in
    QUALITY_CATALOG's narrower vocabulary -- classification is a taxonomy-
    wide fact, not a per-family one; see `ALL_CATALOG`'s comment).

    "Classified" means: a `may` kind present in `_entries_by_capability_
    kind(taxonomy)` -- when `taxonomy is None` this is the SAME join
    `_fired_obligations` computes over the same `catalog` argument, so the
    pre-T-0171 default can never diverge from what actually fires (charter:
    no duplication)."""
    known = frozenset(
        _entries_by_capability_kind(taxonomy if taxonomy is not None else catalog)
    )
    excused = {entry.kind for entry in benign}

    violations: list[ThreatViolation] = []
    for node in sorted(model.nodes, key=lambda n: n.id):
        kinds = sorted({_may_kind(atom) for atom in node.may})
        for kind in kinds:
            if kind not in known and kind not in excused:
                violations.append(_capability_violation(kind, node.id))
    return Ok(tuple(violations))


#: T-0382: a `caught_by` string is honest about naming NO compensating
#: control -- "not caught anywhere yet" -- when it starts with this marker,
#: e.g. `"none -- no CWE_CATALOG entry targets ..."` (many existing
#: `DEFAULT_BENIGN_CAPABILITIES`/`*_OUT_OF_SCOPE` entries use this exact
#: convention already). `check_caught_by_integrity` never fails an honest
#: "none" -- fabricating a control reference to dodge the check would be
#: worse than admitting the gap; converting each honest "none" into a real
#: enforced check or a genuine compensating control is T-0383's job, not
#: this one's.
# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
CAUGHT_BY_NONE_MARKER = "none"

#: A rule-id-shaped token: 2-10 uppercase letters then 3+ digits, matching
#: this repo's own gate-rule naming convention (`THREAT002`, `SEC110`,
#: `PII010`, ...) -- `frob.gates._KNOWN_GATE_RULES`'s own id shape. Kept
#: local to this module (no import from `frob.gates`, which already
#: imports `frob.strata` -- importing back would cycle); callers that know
#: the live gate-rule set (`frob.gates`) pass it in as `known_rule_ids`.
_RULE_ID_TOKEN = re.compile(r"\b([A-Z]{2,10}[0-9]{3})\b")

#: A CWE-id-shaped token, e.g. "CWE-78" -- verified against this module's
#: own `WeaknessEntry` catalogs (`ALL_CATALOG` by default), never a
#: separately hand-maintained id list (charter: no duplication).
_CWE_ID_TOKEN = re.compile(r"\b(CWE-\d+)\b")


def _caught_by_referenced_tokens(
    caught_by: str,
) -> tuple[frozenset[str], frozenset[str]]:
    """Every rule-id-shaped and CWE-id-shaped token a `caught_by` string
    mentions, as `(rule_ids, cwe_ids)` -- the set `check_caught_by_
    integrity` verifies each actually resolves to a real control."""
    return (
        frozenset(_RULE_ID_TOKEN.findall(caught_by)),
        frozenset(_CWE_ID_TOKEN.findall(caught_by)),
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:tests tests/unit/strata/test_threat.py::TestCaughtByUnresolvedTokens.test_unknown_rule_id_is_unresolved  # noqa: E501
def caught_by_unresolved_tokens(
    caught_by: str,
    known_rule_ids: frozenset[str] = frozenset(),
    cataloged_ids: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Public (T-0382) sibling of `check_caught_by_integrity`'s per-entry
    resolution step: every rule-id-/CWE-id-shaped token `caught_by`
    references that resolves to NEITHER `known_rule_ids` (the live
    gate-rule-id set) NOR `cataloged_ids` (a catalog's own id set) --
    empty means every referenced token resolved (or none was referenced
    at all). Exists so `_compliance.py`'s own caught_by family
    (`OutOfScopeRegulation.caught_by`, COMPLIANCE004) can verify its
    excuses identically to `check_caught_by_integrity`'s THREAT006
    without duplicating the token-extraction regexes or the deny-by-
    default resolution rule (charter: no duplication) -- callers still
    own the `CAUGHT_BY_NONE_MARKER` honest-disclosure short-circuit
    themselves, this function does not special-case it."""
    rule_ids, cwe_ids = _caught_by_referenced_tokens(caught_by)
    return (rule_ids - known_rule_ids) | (cwe_ids - cataloged_ids)


def _caught_by_violation(
    entry_id: str, caught_by: str, unresolved: frozenset[str]
) -> ThreatViolation:
    """THREAT006 violation helper: `caught_by` names a rule id or CWE id
    that resolves to no real registered control -- deny-by-default, an
    excuse referencing a fabricated control is worse than one honestly
    naming none at all (`CAUGHT_BY_NONE_MARKER`)."""
    named = ", ".join(sorted(unresolved))
    _log.warning(
        "threat: THREAT006 %s caught_by %r references unknown control(s): %s",
        entry_id,
        caught_by,
        named,
    )
    return ThreatViolation(
        rule="THREAT006",
        cwe=entry_id if entry_id.startswith("CWE-") else "",
        detail=f"{entry_id} caught_by {caught_by!r} references unknown "
        f"control(s) that do not exist: {named}",
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def check_caught_by_integrity(
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = (),
    known_rule_ids: frozenset[str] = frozenset(),
    catalog: tuple[WeaknessEntry, ...] = ALL_CATALOG,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT006 (T-0382): every `OutOfScopeEntry`/`BenignCapability.
    caught_by` that names a rule-id- or CWE-id-shaped token must reference
    a control that actually exists -- a typo'd or fabricated reference is
    a violation, deny-by-default (an excused CWE/capability "caught
    nowhere" must be visible, not silently trusted, docs/strata/threat.md
    #the-exhaustiveness-proof-the-point). An honest `"none -- ..."`
    `caught_by` (`CAUGHT_BY_NONE_MARKER`) never fails this check -- it is
    already declaring the gap, not hiding it; free text with no
    recognizable rule-id/CWE-id token is not checked further (this pass
    verifies REFERENCES resolve, it does not grade prose).

    `known_rule_ids` is the live gate-rule-id set (`frob.gates.
    _KNOWN_GATE_RULES`) -- passed in by the caller rather than imported,
    since `frob.gates` already imports `frob.strata` (import direction
    would cycle otherwise). Passing the default empty set means no
    rule-id-shaped token can ever resolve, so a caller wanting real rule-id
    verification must supply it explicitly."""
    cataloged_cwes = frozenset(entry.id for entry in catalog)
    violations: list[ThreatViolation] = []
    for entry_id, caught_by in (
        *((e.id, e.caught_by) for e in out_of_scope),
        *((e.kind, e.caught_by) for e in benign),
    ):
        if caught_by.strip().lower().startswith(CAUGHT_BY_NONE_MARKER):
            continue
        unresolved = caught_by_unresolved_tokens(
            caught_by, known_rule_ids, cataloged_cwes
        )
        if unresolved:
            violations.append(_caught_by_violation(entry_id, caught_by, unresolved))
    return Ok(tuple(violations))


def _fired_obligations(
    model: KernelModel, catalog: tuple[WeaknessEntry, ...]
) -> list[tuple[str, WeaknessEntry]]:
    """Every (node_id, WeaknessEntry) pair whose obligation fires: the node
    declares a `may` atom of the entry's `capability_kind`."""
    by_kind = _entries_by_capability_kind(catalog)

    fired: list[tuple[str, WeaknessEntry]] = []
    for node in model.nodes:
        kinds = {_may_kind(atom) for atom in node.may}
        for kind in kinds:
            for entry in by_kind.get(kind, ()):
                fired.append((node.id, entry))
    return fired


def _rung_at_least(have: Rung, need: Rung) -> bool:
    """Whether `have` sits at or above `need` on the evidence ladder."""
    return _RUNG_ORDER.index(have) >= _RUNG_ORDER.index(need)


def _discharge_claim_id(cwe_id: str, node_id: str) -> str:
    """The naming convention a discharging `Claim.id` must follow: `weakness:
    <cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe) -- one
    canonical home for the format so THREAT003 and any future authoring
    surface never disagree (charter: no duplication)."""
    return f"weakness:{cwe_id}:{node_id}"


def _discharge_violation(
    entry: WeaknessEntry, node_id: str, detail: str
) -> ThreatViolation:
    """THREAT003 violation helper: deny-by-default undischarged obligation."""
    _log.warning(
        "threat: THREAT003 %s on %s undischarged: %s", entry.id, node_id, detail
    )
    return ThreatViolation(rule="THREAT003", cwe=entry.id, node=node_id, detail=detail)


# frob:doc docs/strata/threat.md#phasing
_FOREIGN_TRUST = "foreign"


# frob:doc docs/strata/threat.md#phasing
def _discharges_as_chokepoint(
    nodes_by_id: dict[str, Node], node_id: str, claim: Claim
) -> bool:
    """Whether `claim` PROVES a mitigation boundary sits on every path from a
    foreign source to `node_id`, not merely "declared somewhere" (docs/
    strata/threat.md#phasing item C, T-0113).

    Requires `claim.body` to be a `NoFlow(src=<foreign>, dst=node_id)` --
    exactly the shape `_eval_noflow` (`_claims.py`) already proves over the
    closure engine's boundary-aware `reachable`: a REFUTED verdict there
    means some path survives with no boundary in the way, and
    `_check_one_discharge` already rejects a REFUTED claim, so requiring
    THIS shape is what turns "a claim exists" into "the mitigation is a
    proven chokepoint" -- no new detection, no new closure call, the SAME
    `NoFlow` evaluation every other flow-cutting claim in the kernel
    already relies on. `src` may name the `"foreign"` trust level directly
    (expands to every foreign-trust node, `_claims.py::_expand`) or a
    single node whose own declared `trust` is `"foreign"`.
    """
    if not isinstance(claim.body, NoFlow):
        return False
    if claim.body.dst != node_id:
        return False
    src = claim.body.src
    if src == _FOREIGN_TRUST:
        return True
    src_node = nodes_by_id.get(src)
    return src_node is not None and src_node.trust == _FOREIGN_TRUST


def _matching_boundary_ids(model: KernelModel, entry: WeaknessEntry) -> frozenset[str]:
    """Boundary ids that carry the EXACT mitigation `entry` requires: an
    `ENDORSE`-direction boundary (a chokepoint raises integrity, it never
    lowers confidentiality -- `declassify` is the opposite operation and
    can never be a weakness mitigation, docs/strata/kernel.md#data-models)
    whose `predicate` equals `entry.mitigation` (the catalog's `needs
    mitigation <name>` clause, docs/strata/threat.md#the-catalog-stdcwe).

    A boundary of the wrong direction, or an `endorse` boundary with an
    unrelated predicate (e.g. `"legal_review_signed_off"` sitting in for a
    CWE-79 `output_encoding` requirement), is excluded -- review round 2's
    gap: `_eval_noflow`'s `reachable` treats ANY boundary as a barrier
    regardless of kind, so without this filter a claim could be "proved"
    by a boundary that mitigates nothing relevant to this weakness.
    """
    return frozenset(
        boundary.id
        for boundary in model.boundaries
        if boundary.direction is BoundaryDirection.ENDORSE
        and boundary.predicate == entry.mitigation
    )


def _restricted_to_boundaries(
    model: KernelModel, keep_ids: frozenset[str], claim: Claim
) -> KernelModel:
    """`model` with every boundary NOT in `keep_ids` removed and `claims`
    narrowed to just `claim` -- the input to `_mitigation_is_chokepoint`'s
    re-evaluation (docs/strata/threat.md#phasing item C). Narrowing
    `claims` to one is an optimization only (`evaluate_claims` would
    otherwise re-evaluate every other claim in the model against the
    restricted boundary set for no reason this check needs)."""
    kept = tuple(b for b in model.boundaries if b.id in keep_ids)
    return model.model_copy(update={"boundaries": kept, "claims": (claim,)})


# frob:doc docs/strata/threat.md#phasing
def _claim_holds(model: KernelModel, claim: Claim) -> bool:
    """Whether `claim` evaluates PROVED/EVIDENCED (`evaluate_claims`) over
    `model` -- the one place `_mitigation_is_chokepoint` calls into the
    closure engine, reused for both the vacuous-path short-circuit and the
    matching-boundary re-evaluation below (charter: no duplication)."""
    result = evaluate_claims(model)
    if result.is_err:
        _log.warning(
            "threat: mitigation-chokepoint re-evaluation for %s failed: %s",
            claim.id,
            result.danger_err,
        )
        return False
    for claim_result in result.danger_ok:
        if claim_result.claim_id == claim.id:
            return claim_result.verdict in (Verdict.PROVED, Verdict.EVIDENCED)
    return False


# Whether the boundaries carrying `entry`'s EXACT required mitigation
# (`_matching_boundary_ids`) are, by themselves, sufficient to make
# `claim`'s `NoFlow` hold -- i.e. the catalog-correct mitigation is a
# genuine chokepoint, not merely one boundary among several (of possibly
# unrelated kinds) that happen to also block a path (docs/strata/
# threat.md#phasing item C, review round 2). This comment (not the
# docstring) carries the explanation so frob-arch's long-function line
# count reflects the code, not the essay (same pattern as gates/
# __init__.py's `_match_waiver`).
#
# Vacuous-path short-circuit FIRST: if `claim` already holds with EVERY
# boundary removed (`_restricted_to_boundaries(model, frozenset(),
# claim)`), no path from the claim's source to its sink exists in the
# closure AT ALL -- the `NoFlow` is proved by absence of a flow, not by
# any boundary, so there is nothing for a mitigation to be a chokepoint
# ON. Requiring a matching boundary in this case would reject models
# that were already correctly PROVED before phase C's tightening
# (`_check_one_discharge`'s pre-T-0113 fixtures declare no flows/
# boundaries at all) -- a real regression, not the reviewer-flagged gap.
#
# Otherwise, re-evaluates the SAME claim (`_claim_holds`, so the SAME
# `_eval_noflow`/`reachable` closure walk `_discharges_as_chokepoint`'s
# round-1 shape check already leans on) over a model copy with every
# OTHER boundary removed (`_restricted_to_boundaries`) -- no new closure
# primitive, no new `strata_core` call.
#
# Quantifier: this is "the matching boundaries alone cut the closure the
# SAME `NoFlow` walk already computes" -- sound (a PROVED result here
# means the matching boundaries really do interpose on every path
# `reachable` traverses, since removing MORE boundaries can only ADD
# reachability, never remove it) but not maximal: a path blocked ONLY by
# a non-matching boundary (with no matching boundary anywhere on it) is
# invisible to per-path attribution, since `FactBase.reachable` reports
# reachability, not which specific boundary blocked which specific path
# (docs/strata/kernel.md#fact-base). If EVERY path happens to carry a
# matching boundary, this proves True exactly; if only SOME paths do
# while others are saved solely by a non-matching boundary, this proves
# False (the restricted-model NoFlow is REFUTED, since removing the
# non-matching boundary that had been covering that path reopens it) --
# which is the conservative, deny-by-default direction (charter law 2).
# No unsound acceptance is possible; the disclosed gap is precision, not
# soundness: a model needing a per-path (rather than per-model)
# mitigation-kind proof is out of v0's scope, noted here and in
# threat.md rather than silently assumed away.
def _mitigation_is_chokepoint(
    model: KernelModel, entry: WeaknessEntry, claim: Claim
) -> bool:
    """Whether the catalog-correct mitigation for `entry` is a genuine
    chokepoint for `claim`, not merely one boundary among several that
    happens to also block a path -- see the comment above this def."""
    if _claim_holds(_restricted_to_boundaries(model, frozenset(), claim), claim):
        return True
    matching = _matching_boundary_ids(model, entry)
    if not matching:
        return False
    return _claim_holds(_restricted_to_boundaries(model, matching, claim), claim)


def _check_discharge_shape_and_rung(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    nodes_by_id: dict[str, Node],
) -> ThreatViolation | None:
    """First two `_check_one_discharge` gates: `claim` must prove a
    mitigation-chokepoint SHAPE (`_discharges_as_chokepoint`) and must be
    evaluated at or above the catalog's required rung -- split out of
    `_check_one_discharge` so its long-function line count reflects the
    per-gate logic, not one 40-line if-chain (frob-arch long-function)."""
    if not _discharges_as_chokepoint(nodes_by_id, node_id, claim):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} does not prove a mitigation chokepoint -- "
            f"body must be NoFlow(src=<foreign source>, dst={node_id!r})",
        )
    if not _rung_at_least(claim.required_rung, entry.rung):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} required_rung {claim.required_rung.value} "
            f"below catalog rung {entry.rung.value}",
        )
    return None


def _check_discharge_assumed_and_refuted(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    results_by_id: dict[str, ClaimResult],
) -> ThreatViolation | None:
    """Middle two `_check_one_discharge` gates: an `assumed` claim must
    carry an owner/review date, and a claim with a resolved verdict must
    not be REFUTED -- see `_check_one_discharge`'s comment for why the
    mitigation-kind check (which follows this pair) skips assumed claims
    entirely rather than living in this same helper."""
    if claim.assumed and (claim.owner is None or claim.review is None):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} is assumed with no owner/review date",
        )
    result = results_by_id.get(claim_id)
    if result is not None and result.verdict is Verdict.REFUTED:
        return _discharge_violation(
            entry, node_id, f"claim {claim_id!r} is REFUTED: {result.detail}"
        )
    return None


# The mitigation-kind check (`_mitigation_is_chokepoint`) is skipped for
# an `assumed` claim, exactly like the REFUTED check above it: an assumed
# claim is a human-owned TCB entry never run through the closure at all
# (`_claims.py::evaluate_claims` short-circuits assumed claims to the
# `ASSUMED` verdict before touching `_eval_noflow`), so there is no
# closure-derived proof to inspect for boundary kind -- the owner/review
# gate a few lines up is the only accountability an assume gets, same as
# every other claim form in this module.
#
# It is ALSO skipped when `node_id` names a `managed` node (T-0172,
# `_code_binding.py::is_managed`): a managed node is external, pure-config
# infrastructure declared to have no scannable code, so there is no
# tier-2 code-modeled boundary for `_mitigation_is_chokepoint` to inspect
# either -- "no tier-2 conformance; obligations shift to config evidence
# or assumes" (docs/strata/surface.md#key-construct-semantics). The claim
# still has to exist, prove a chokepoint shape (`_discharges_as_chokepoint`
# above), and clear the catalog rung -- only the boundary-KIND proof is
# exempted, same as an assume gets.
def _check_discharge_mitigation_kind(
    entry: WeaknessEntry,
    node_id: str,
    claim: Claim,
    claim_id: str,
    nodes_by_id: dict[str, Node],
    model: KernelModel,
) -> ThreatViolation | None:
    """Last `_check_one_discharge` gate: for a non-assumed claim on a
    non-managed node, the proven chokepoint must be of the catalog's
    required mitigation KIND (`_mitigation_is_chokepoint`) -- see the
    comment above this def for why assumed/managed claims skip it."""
    node = nodes_by_id.get(node_id)
    node_is_managed = node is not None and is_managed(node)
    if (
        not claim.assumed
        and not node_is_managed
        and not _mitigation_is_chokepoint(model, entry, claim)
    ):
        return _discharge_violation(
            entry,
            node_id,
            f"claim {claim_id!r} proves a chokepoint but not of the required "
            f"mitigation kind -- no ENDORSE boundary with predicate "
            f"{entry.mitigation!r} is sufficient alone to block every path",
        )
    return None


def _check_one_discharge(
    entry: WeaknessEntry,
    node_id: str,
    claims_by_id: dict[str, Claim],
    results_by_id: dict[str, ClaimResult],
    nodes_by_id: dict[str, Node],
    model: KernelModel,
) -> ThreatViolation | None:
    """One fired obligation's discharge check: present, shaped as a proven
    mitigation chokepoint of the CORRECT kind, not REFUTED, at or above the
    catalog's required rung, and -- if assumed -- owned with a review date
    (docs/strata/threat.md#the-exhaustiveness-proof-the-point, item 3;
    chokepoint shape + mitigation-kind check added phase C, docs/strata/
    threat.md#phasing item C). The four gates run in this exact order via
    `_check_discharge_shape_and_rung`, `_check_discharge_assumed_and_refuted`,
    and `_check_discharge_mitigation_kind` -- see each helper's docstring/
    comment for what it checks and why.
    """
    claim_id = _discharge_claim_id(entry.id, node_id)
    claim = claims_by_id.get(claim_id)
    if claim is None:
        return _discharge_violation(
            entry, node_id, f"no claim {claim_id!r} discharges this obligation"
        )
    violation = _check_discharge_shape_and_rung(
        entry, node_id, claim, claim_id, nodes_by_id
    )
    if violation is not None:
        return violation
    violation = _check_discharge_assumed_and_refuted(
        entry, node_id, claim, claim_id, results_by_id
    )
    if violation is not None:
        return violation
    return _check_discharge_mitigation_kind(
        entry, node_id, claim, claim_id, nodes_by_id, model
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
def check_discharge_completeness(
    model: KernelModel,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT003: every FIRED weakness obligation (a node declares the `may`
    capability kind that drags it in) is discharged by a `Claim` named
    `weakness:<cwe-id>:<node-id>` (docs/strata/threat.md#the-core-reframe),
    evaluated at or above the catalog's required rung and never REFUTED; a
    dangling or under-evidenced obligation is a violation (docs/strata/
    threat.md#the-exhaustiveness-proof-the-point, item 3).

    Runs `evaluate_claims` to resolve verdicts for claims that are present;
    a missing claim never reaches evaluation -- that is itself the
    violation, deny-by-default (charter law 2).
    """
    fired = _fired_obligations(model, catalog)
    if not fired:
        _log.info("threat: THREAT003 no fired obligations (no matching capabilities)")
        return Ok(())

    indexed = _index_claims_and_results(model)
    if indexed.is_err:
        return Err(indexed.danger_err)
    claims_by_id, nodes_by_id, results_by_id = indexed.danger_ok

    violations: list[ThreatViolation] = []
    for node_id, entry in sorted(fired, key=lambda pair: (pair[1].id, pair[0])):
        violation = _check_one_discharge(
            entry, node_id, claims_by_id, results_by_id, nodes_by_id, model
        )
        if violation is not None:
            violations.append(violation)
    return Ok(tuple(violations))


def _index_claims_and_results(
    model: KernelModel,
) -> Result[
    tuple[dict[str, Claim], dict[str, Node], dict[str, ClaimResult]], StrataError
]:
    """Build the three id-keyed lookups `check_discharge_completeness` needs
    per fired obligation (claims, nodes, evaluated results) -- split out so
    that function's line count reflects the per-obligation loop, not the
    one-time index setup (frob-arch long-function)."""
    claims_by_id = {claim.id: claim for claim in model.claims}
    nodes_by_id = {node.id: node for node in model.nodes}
    results = evaluate_claims(model)
    if results.is_err:
        return Err(results.danger_err)
    results_by_id = {r.claim_id: r for r in results.danger_ok}
    return Ok((claims_by_id, nodes_by_id, results_by_id))


def _undeclared_sink_violation(violation: CapabilityViolation) -> ThreatViolation:
    """THREAT004 violation helper: an observed sink whose owning node declares
    no `may` capability of the matching kind -- the code-level "undeclared
    capability in code is an error" kicker (docs/strata/threat.md
    #capabilities-drag-in-obligations)."""
    _log.warning(
        "threat: THREAT004 %s:%d %s effect (%s) on %s has no declared may "
        "capability of that kind",
        violation.file,
        violation.line,
        violation.kind,
        violation.needle,
        violation.component,
    )
    return ThreatViolation(
        rule="THREAT004",
        capability=violation.kind,
        node=violation.component,
        detail=f"observed {violation.kind} effect at {violation.file}:"
        f"{violation.line} ({violation.needle!r}) has no declared may "
        "capability of that kind",
    )


def _unclassified_sink_violation(effect: ObservedEffect, owner: str) -> ThreatViolation:
    """THREAT005 violation helper: an extracted sink whose kind the catalog
    does not recognize and no `BenignCapability` excuses -- the code-level
    mirror of THREAT002 (docs/strata/threat.md#phasing item C)."""
    _log.warning(
        "threat: THREAT005 %s:%d %s effect (%s) on %s matches no std.cwe sink "
        "taxonomy entry and no BenignCapability excuse",
        effect.file,
        effect.line,
        effect.kind,
        effect.needle,
        owner,
    )
    return ThreatViolation(
        rule="THREAT005",
        capability=effect.kind,
        node=owner,
        detail=f"observed {effect.kind} effect at {effect.file}:{effect.line} "
        f"({effect.needle!r}) matches no std.cwe sink taxonomy entry and no "
        "BenignCapability excuse",
    )


# frob:doc docs/strata/threat.md#phasing
def check_effect_completeness(
    model: KernelModel,
    binding: CodeBinding,
    root: Path,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    benign: tuple[BenignCapability, ...] = (),
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """THREAT004 + THREAT005: the code-level half of "every capability ...
    is classified" phase B deferred (docs/strata/threat.md#phasing item C,
    T-0113) -- joins `_effects.py`'s extracted net/fs/exec sinks into the
    SAME taxonomy join THREAT002 uses (`_entries_by_capability_kind`), over
    the SAME `catalog`/`benign` arguments, so code-level and model-level
    classification can never diverge (charter: no duplication).

    THREAT004 reuses `check_capability_conformance`'s undeclared-capability
    join directly (no re-detection): an observed sink on a node with no
    matching `may` declaration. THREAT005 is the sink-classification half:
    an observed sink whose `kind` names no `capability_kind` the `catalog`
    recognizes, unless a `BenignCapability` excuses it.
    """
    known = frozenset(_entries_by_capability_kind(catalog))
    excused = {entry.kind for entry in benign}

    conformance = check_capability_conformance(model, binding, root)
    undeclared = tuple(_undeclared_sink_violation(v) for v in conformance.violations)

    unclassified = tuple(
        _unclassified_sink_violation(effect, binding.owner[effect.file])
        for effect in extract_effects(binding, root)
        if effect.kind not in known and effect.kind not in excused
    )
    return Ok(undeclared + unclassified)


def _run_all_completeness_checks(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    benign: tuple[BenignCapability, ...],
    binding: CodeBinding | None,
    root: Path | None,
) -> Result[tuple[ThreatViolation, ...], StrataError]:
    """Run THREAT001+002 (catalog/capability), THREAT003 (discharge), and --
    when both `binding` and `root` are given -- THREAT004+005 (effect), in
    that exact order, short-circuiting on the first `Err` -- split out of
    `evaluate_threats` so its own line count reflects the entrypoint seam,
    not the four-check sequence (frob-arch long-function)."""
    catalog_violations = check_catalog_completeness(view, catalog, out_of_scope)
    if catalog_violations.is_err:
        return Err(catalog_violations.danger_err)
    capability_violations = check_capability_completeness(model, catalog, benign)
    if capability_violations.is_err:
        return Err(capability_violations.danger_err)
    discharge_violations = check_discharge_completeness(model, catalog)
    if discharge_violations.is_err:
        return Err(discharge_violations.danger_err)
    effect_violations: tuple[ThreatViolation, ...] = ()
    if binding is not None and root is not None:
        effects_result = check_effect_completeness(
            model, binding, root, catalog, benign
        )
        if effects_result.is_err:
            return Err(effects_result.danger_err)
        effect_violations = effects_result.danger_ok
    return Ok(
        (
            *catalog_violations.danger_ok,
            *capability_violations.danger_ok,
            *discharge_violations.danger_ok,
            *effect_violations,
        )
    )


# frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
# frob:waive TEST005 reason="evaluate_threats 83.3% branch cover, debt T-0160"
def evaluate_threats(
    model: KernelModel,
    view: str,
    catalog: tuple[WeaknessEntry, ...] = CWE_CATALOG,
    out_of_scope: tuple[OutOfScopeEntry, ...] = (),
    benign: tuple[BenignCapability, ...] = (),
    binding: CodeBinding | None = None,
    root: Path | None = None,
) -> Result[ThreatReport, StrataError]:
    """The strata-level threat-audit entrypoint: THREAT001 + THREAT002 +
    THREAT003 over `model` against the selected baseline `view` (docs/
    strata/threat.md#the-exhaustiveness-proof-the-point); THREAT004 +
    THREAT005 (the code-level join, T-0113) run too when both `binding`
    and `root` are given -- omitted by default since design-level-only
    callers have no code tree to bind (charter law 2: an absent join is
    never silently assumed clean, it is simply not run; a caller wanting
    the full phase C proof must pass both). Gate wiring (`frob check`
    surfacing this as a diagnostic) is a follow-up once T-0080's sys_gate
    lands -- this function is the seam that follow-up calls into, kept
    deliberately gate-agnostic (no `src/frob/gates` import here).
    """
    all_violations_result = _run_all_completeness_checks(
        model, view, catalog, out_of_scope, benign, binding, root
    )
    if all_violations_result.is_err:
        return Err(all_violations_result.danger_err)
    all_violations = all_violations_result.danger_ok
    _log_pre_discharge_obligation_count(view, catalog, out_of_scope, all_violations)
    return Ok(ThreatReport(violations=all_violations))


# T-0217: this is the RAW pre-discharge obligation count across all four
# completeness checks (catalog/capability/discharge/effect) -- callers
# such as `frob sys plan` only turn THREAT003 violations into obligation
# tickets, and `frob sys doc` renders a per-CWE PROVED/ASSUMED matrix
# from a DIFFERENT reduction of this same data. At INFO level this line
# printed right before a "0 obligation ticket(s)" / "PROVED" summary and
# read as contradictory (a nonzero count next to a zero/clean verdict)
# even though nothing was wrong -- the two numbers answer different
# questions. Demoted to DEBUG so default-verbosity output only shows the
# post-discharge verdict; `-v`/`-vv` still surface this detail.
def _log_pre_discharge_obligation_count(
    view: str,
    catalog: tuple[WeaknessEntry, ...],
    out_of_scope: tuple[OutOfScopeEntry, ...],
    all_violations: tuple[ThreatViolation, ...],
) -> None:
    """DEBUG-level log of `evaluate_threats`'s raw pre-discharge obligation
    count -- see the comment above this def for why it is DEBUG, not INFO."""
    _log.debug(
        "threat: obligations evaluated view=%r catalog=%d out_of_scope=%d -> "
        "%d pre-discharge obligation(s) (not all become tickets; see caller's "
        "own post-discharge count/verdict)",
        view,
        len(catalog),
        len(out_of_scope),
        len(all_violations),
    )


__all__ = [
    "ALL_CATALOG",
    "CWE_CATALOG",
    "CWE_TOP_25_CATALOG",
    "CWE_TOP_25_OUT_OF_SCOPE",
    "CWE_TOP_25_VIEWS",
    "DEFAULT_BENIGN_CAPABILITIES",
    "QUALITY_CATALOG",
    "QUALITY_OUT_OF_SCOPE",
    "QUALITY_VIEWS",
    "VIEWS",
    "BenignCapability",
    "OutOfScopeEntry",
    "ThreatReport",
    "ThreatViolation",
    "WeaknessEntry",
    "CAUGHT_BY_NONE_MARKER",
    "caught_by_unresolved_tokens",
    "check_capability_completeness",
    "check_catalog_completeness",
    "check_caught_by_integrity",
    "check_discharge_completeness",
    "check_effect_completeness",
    "evaluate_threats",
    "load_repo_benign_capabilities",
]
