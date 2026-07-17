"""Data shapes and errors for frob.vet (docs/modules/vet.md is authoritative).

Covers the lockfile-conformance slice (VET001, VET011, VET-JS lifecycle
scripts, typosquat distance, VET005 osv-scanner adapter) plus the T-0008
capability-scan slice built on top of it: capability/obfuscation signals on
`PackageVerdict`, `capability_diff` for VET003 escalation, and the ecosystem
rules in `_ecosystem.py`. See "Implementation notes" in docs/modules/vet.md for what
of the full design (VET007-VET010, most of VET-C, dynamic detonation) is
still out of scope.
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
    "capability_diff",
]


# frob:doc docs/modules/vet.md#public-api
class Dependency(BaseModel):
    """One (ecosystem, name, version) tuple resolved from a lockfile."""

    model_config = ConfigDict(frozen=True)

    ecosystem: str
    name: str
    version: str
    # non-registry resolution target (git+/http(s)/file: URL), when the
    # lockfile records one -- feeds VET-JS004 "declarable-only" sources.
    # Empty string means "resolved from the normal registry" (the common case).
    resolved: str = ""


# frob:doc docs/modules/vet.md#public-api
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


# frob:doc docs/modules/vet.md#public-api
class VetReport(BaseModel):
    """The merged result of a `frob vet` scan: per-package verdicts and violations."""

    model_config = ConfigDict(frozen=True)

    verdicts: tuple[PackageVerdict, ...] = ()
    violations: tuple[Violation, ...] = ()
    enforce: bool = False
    advisory_only: bool = False
    skipped: tuple[str, ...] = ()


# frob:doc docs/modules/vet.md#public-api
def capability_diff(prev: PackageVerdict, cur: PackageVerdict) -> tuple[str, ...]:
    """Capabilities `cur` has that `prev` did not -- the VET003 escalation
    signal (docs/modules/vet.md "Public API"). Order-stable (sorted) for diffable
    output; empty when `cur` added nothing new."""
    added = sorted(cur.capabilities - prev.capabilities)
    return tuple(added)


# frob:doc docs/modules/vet.md#public-api
class HookVerdict(BaseModel):
    """One package's --hook-mode verdict against a not-yet-installed package."""

    model_config = ConfigDict(frozen=True)

    package: str
    ecosystem: str
    verdict: str  # "ok" | "quarantine" | "typosquat" | "advisory" | "unverified"
    message: str
    blocked: bool


# frob:doc docs/modules/vet.md#public-api
class VetConfig(BaseModel):
    """The `[vet]` table plus `[vet.allow]`, loaded from frob.toml."""

    model_config = ConfigDict(frozen=True)

    present: bool = False
    enforce: bool = False
    osv: bool = False
    quarantine_days: int = 14
    registry_base_url: str | None = None
    allow: Mapping[str, tuple[str, ...] | bool] = {}


# frob:doc docs/modules/vet.md#public-api
class HookAction(StrEnum):
    """A parsed --hook command's disposition before any network check."""

    INSTALL = "install"
    IGNORE = "ignore"


# frob:doc docs/modules/vet.md#public-api
class VetError(ErrorSet):
    """Fallible outcomes of frob.vet operations."""

    LockfileUnsupported = "No parser for this lockfile format"
    SourceUnavailable = "Package source not in local caches; rerun with --fetch"
    CacheCorrupt = "vet cache unreadable; delete .frob/vet.db to rebuild"
    ConfigMalformed = "frob.toml [vet]/[vet.allow] table is malformed"
