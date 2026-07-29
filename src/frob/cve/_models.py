"""Pydantic v2 shapes for CVE Record Format v5 (docs/modules/cve.md is
authoritative). Mirrors the subset of the schema published at
github.com/CVEProject/cvelistV5/blob/main/schema/CVE_Record_Format.json
that frob actually consumes: identity/state, CNA/ADP containers, affected
products with version-range semantics, CWE-bearing problem types, CVSS
v3.1/v4.0 metrics, references, and descriptions.

Deliberately permissive: every model ignores unknown extra fields (the
real-world corpus grows new optional fields constantly; a strict schema
would break on every upstream release). What is NOT tolerated is a missing
REQUIRED field -- `cveMetadata.cveId`/`state`, `containers.cna`, an
`affected[].versions[]` entry missing `version`/`status`, and so on raise a
real pydantic ValidationError, which `parse_record` (`_parser.py`) turns
into a typed `CveError.MalformedRecord` -- never a silent partial parse.
"""
# frob:waive INV006 preset="split-carried-prose"

# frob:ticket T-0146
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "AdpContainer",
    "Affected",
    "CnaContainer",
    "CveContainers",
    "CveError",
    "CveMetadata",
    "CveRecord",
    "CveState",
    "Cvss",
    "Description",
    "Metric",
    "ProblemType",
    "ProblemTypeDescription",
    "Reference",
    "Version",
]


# frob:doc docs/modules/cve.md#public-api
class CveState(StrEnum):
    """A CVE Record's lifecycle state -- the only two values the v5 schema
    defines. `REJECTED` records still parse fully (they retain an id and
    dates); callers decide whether to skip them."""

    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"


# frob:doc docs/modules/cve.md#public-api
class CveError(ErrorSet):
    """Fallible outcomes of frob.cve parsing operations."""

    NotFound = "record path does not exist"
    Unreadable = "record path could not be read (permissions/IO error)"
    NotJson = "record file is not valid JSON"
    MalformedRecord = "record JSON does not satisfy the required CVE v5 structure"
    MirrorPathInvalid = "mirror root is not a directory"


# frob:doc docs/modules/cve.md#public-api
class CveMetadata(BaseModel):
    """Identity and lifecycle dates for one CVE Record (`cveMetadata`)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    cveId: str
    assignerOrgId: str = ""
    state: CveState
    dateReserved: str = ""
    datePublished: str = ""
    dateUpdated: str = ""
    dateRejected: str = ""


# frob:doc docs/modules/cve.md#public-api
class Version(BaseModel):
    """One entry in `affected[].versions[]`: a single version or a range
    boundary (`lessThan`/`lessThanOrEqual`), with the vendor's own
    `versionType` (semver, custom, git commit, ...) and `status` (affected
    or unaffected -- ranges can carve out unaffected sub-ranges)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    version: str
    status: str
    lessThan: str | None = None
    lessThanOrEqual: str | None = None
    versionType: str = ""


# frob:doc docs/modules/cve.md#public-api
class Affected(BaseModel):
    """One affected-product entry (`containers.cna.affected[]` /
    `containers.adp[].affected[]`): vendor/product plus its version ranges
    and the container's default status for versions the range list does
    not cover."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    vendor: str = ""
    product: str = ""
    defaultStatus: str = "unknown"
    versions: tuple[Version, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class ProblemTypeDescription(BaseModel):
    """One `problemTypes[].descriptions[]` entry: a human description
    optionally tagged with a CWE id (`cweId` is absent for free-text
    weakness descriptions that predate/skip CWE mapping)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    lang: str = "en"
    description: str = ""
    cweId: str | None = None
    type: str = ""


# frob:doc docs/modules/cve.md#public-api
class ProblemType(BaseModel):
    """One `problemTypes[]` entry: a group of weakness descriptions
    (usually one, occasionally several per-language/per-taxonomy)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    descriptions: tuple[ProblemTypeDescription, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class Cvss(BaseModel):
    """One CVSS score object (the `cvssV3_1`/`cvssV4_0` value inside a
    `metrics[]` entry). `version`/`vectorString` are the only fields the
    schema always requires; `baseScore`/`baseSeverity` are optional in the
    wild (some ADP containers report a vector with no numeric score)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    version: str
    vectorString: str
    baseScore: float | None = None
    baseSeverity: str | None = None


# frob:doc docs/modules/cve.md#public-api
class Metric(BaseModel):
    """One `metrics[]` entry. The schema allows several CVSS versions (and
    other, non-CVSS metric types this module does not model) side by side
    on the same entry; only `cvssV3_1`/`cvssV4_0` are extracted here."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    cvssV3_1: Cvss | None = None
    cvssV4_0: Cvss | None = None


# frob:doc docs/modules/cve.md#public-api
class Reference(BaseModel):
    """One `references[]` entry: a URL plus optional name/tags."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    url: str
    name: str = ""
    tags: tuple[str, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class Description(BaseModel):
    """One `descriptions[]` entry: a language-tagged summary."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    lang: str = "en"
    value: str = ""


# frob:doc docs/modules/cve.md#public-api
class CnaContainer(BaseModel):
    """The mandatory `containers.cna` container: the assigning CNA's own
    view of the vulnerability (affected products, problem types, metrics,
    references, descriptions)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    affected: tuple[Affected, ...] = ()
    problemTypes: tuple[ProblemType, ...] = ()
    metrics: tuple[Metric, ...] = ()
    references: tuple[Reference, ...] = ()
    descriptions: tuple[Description, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class AdpContainer(BaseModel):
    """One `containers.adp[]` entry: an Authorized Data Publisher's
    supplemental view (e.g. CISA-ADP, VulnCheck) -- same inner shape as
    the CNA container, added independently and possibly more than once."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    affected: tuple[Affected, ...] = ()
    problemTypes: tuple[ProblemType, ...] = ()
    metrics: tuple[Metric, ...] = ()
    references: tuple[Reference, ...] = ()
    descriptions: tuple[Description, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class CveContainers(BaseModel):
    """`containers`: the mandatory CNA container plus zero or more ADP
    containers. A REJECTED record's `cna` is typically near-empty (the
    schema still requires the key to be present)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    cna: CnaContainer
    adp: tuple[AdpContainer, ...] = ()


# frob:doc docs/modules/cve.md#public-api
class CveRecord(BaseModel):
    """One parsed CVE Record Format v5 JSON document -- the top-level
    `parse_record` return shape."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    dataType: str = "CVE_RECORD"
    dataVersion: str = "5.0"
    cveMetadata: CveMetadata
    containers: CveContainers
