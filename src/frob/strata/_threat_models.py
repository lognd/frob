"""strata threat catalog models: one catalog entry (`WeaknessEntry`), one
out-of-scope disclosure (`OutOfScopeEntry`), and one excused capability
(`BenignCapability`) -- the record shapes every `_threat_catalog_*` module
builds its data from (T-1420 split from `_threat.py`, verbatim relocation
-- WHY: three small model classes were sitting in the same 2500-line file
as the checker logic and every data catalog that consumes them, pushing
the file well past LARGE001's threshold; models have no behavior of their
own, so they get the smallest possible home). See docs/strata/threat.md
#the-catalog-stdcwe for what these entries mean."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ._models import Rung


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
    unaccounted-for gap, not an honest exclusion. `family` (T-0511, strata
    audit G12) is `None` for the built-in `DEFAULT_BENIGN_CAPABILITIES`
    tuple (each entry's own comment already documents, by hand, which
    family it is a no-op for -- audited once at authoring time) but
    MANDATORY ("security" | "quality") for every repo-declared excuse
    `load_repo_benign_capabilities` loads -- a repo excuse names WHICH
    catalog family it claims the kind is unclassified in, and that claim
    is verified at load time (`_family_catalog_for`), not merely trusted:
    an excuse for a kind ALREADY classified in the family it targets is
    rejected outright, distinguishing a genuinely cross-family excuse
    (e.g. `client_storage` excused for `family="quality"`, legitimately
    unmapped there despite being CWE_CATALOG-classified security-side --
    the T-0017 case) from an illegitimate same-family excuse that would
    silently mask a real, already-known sink."""

    model_config = ConfigDict(frozen=True)

    kind: str
    reason: str = Field(min_length=1)
    caught_by: str = Field(min_length=1)
    family: str | None = None


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
