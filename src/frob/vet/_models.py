"""Data shapes and errors for frob.vet (docs/vet.md is authoritative; MVP subset).

MVP note (docs/vet.md implementation notes): full tree-sitter capability
scanning, escalation diffs (VET002/VET003), and the first-party detector
battery (VET004/VET007-VET010) are 0.2.x. This module implements the
lockfile-conformance slice: VET001 (allow-list conformance), VET011
(cooldown quarantine), VET-JS (lifecycle scripts), typosquat distance, and
the osv-scanner adapter (VET005).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

from frob.gates._models import Violation

__all__ = [
    "Dependency",
    "HookVerdict",
    "PackageVerdict",
    "VetConfig",
    "VetError",
    "VetReport",
    "Violation",
]


class Dependency(BaseModel):
    """One (ecosystem, name, version) tuple resolved from a lockfile."""

    model_config = ConfigDict(frozen=True)

    ecosystem: str
    name: str
    version: str


class PackageVerdict(BaseModel):
    """One package's MVP verdict: name/version plus whatever signals fired.

    MVP note: `capabilities`/`artifact_hash` are populated only from the
    checks this slice implements (install-hook lifecycle scripts); the full
    tree-sitter capability set is 0.2.x.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    ecosystem: str
    artifact_hash: str = ""
    capabilities: frozenset[str] = frozenset()
    signals: tuple[str, ...] = ()


class VetReport(BaseModel):
    """The merged result of a `frob vet` scan: per-package verdicts and violations."""

    model_config = ConfigDict(frozen=True)

    verdicts: tuple[PackageVerdict, ...] = ()
    violations: tuple[Violation, ...] = ()
    enforce: bool = False
    advisory_only: bool = False
    skipped: tuple[str, ...] = ()


class HookVerdict(BaseModel):
    """One package's --hook-mode verdict against a not-yet-installed package."""

    model_config = ConfigDict(frozen=True)

    package: str
    ecosystem: str
    verdict: str  # "ok" | "quarantine" | "typosquat" | "advisory" | "unverified"
    message: str
    blocked: bool


class VetConfig(BaseModel):
    """The `[vet]` table plus `[vet.allow]`, loaded from frob.toml."""

    model_config = ConfigDict(frozen=True)

    present: bool = False
    enforce: bool = False
    osv: bool = False
    quarantine_days: int = 14
    registry_base_url: str | None = None
    allow: Mapping[str, tuple[str, ...] | bool] = {}


class HookAction(StrEnum):
    """A parsed --hook command's disposition before any network check."""

    INSTALL = "install"
    IGNORE = "ignore"


class VetError(ErrorSet):
    """Fallible outcomes of frob.vet operations."""

    LockfileUnsupported = "No parser for this lockfile format"
    SourceUnavailable = "Package source not in local caches; rerun with --fetch"
    CacheCorrupt = "vet cache unreadable; delete .frob/vet.db to rebuild"
    ConfigMalformed = "frob.toml [vet]/[vet.allow] table is malformed"
