"""frob.cve -- CVE Record Format v5 parser (docs/modules/cve.md).

Pydantic v2 models for the cvelistV5 record shape (cveMetadata, CNA/ADP
containers, affected products with version-range semantics, CWE-bearing
problem types, CVSS v3.1/v4.0 metrics) plus `parse_record`/`iter_mirror`
for reading a local mirror clone. Parser+models only -- matching parsed
records against a project's dependencies and linking CWEs to the strata
threat catalog is `frob vet`'s job (T-0147).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from frob.cve._models import (
    AdpContainer,
    Affected,
    CnaContainer,
    CveContainers,
    CveError,
    CveMetadata,
    CveRecord,
    CveState,
    Cvss,
    Description,
    Metric,
    ProblemType,
    ProblemTypeDescription,
    Reference,
    Version,
)
from frob.cve._parser import iter_mirror, parse_record

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
    "iter_mirror",
    "parse_record",
]
