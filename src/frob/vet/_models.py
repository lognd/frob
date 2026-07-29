"""Data shapes and errors for frob.vet (docs/modules/vet.md is authoritative).

Covers the lockfile-conformance slice (VET001, VET011, VET-JS lifecycle
scripts, typosquat distance, VET005 osv-scanner adapter) plus the T-0008
capability-scan slice built on top of it: capability/obfuscation signals on
`PackageVerdict`, `capability_diff` for VET003 escalation, and the ecosystem
rules in `_ecosystem.py`. See "Implementation notes" in docs/modules/vet.md for what
of the full design (VET007-VET010, most of VET-C, dynamic detonation) is
still out of scope.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

from frob.gates._models import Violation

__all__ = [
    "ClosedWorldAccounting",
    "Dependency",
    "HookVerdict",
    "ImportResolution",
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
# frob:waive COV007 reason="docs/modules/vet.md's Public API section individually \
# frob:describes this private enum by name (T-0529) -- a deliberate architecture doc, \
# not accidental drift onto a private helper"
class _HookAction(StrEnum):
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
    CveMirrorInvalid = (
        "CVE mirror path is configured but missing or unreadable "
        "(T-0147, see docs/modules/vet.md)"
    )


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0180
class ImportResolution(BaseModel):
    """One imported top-level module name's closed-world classification
    (T-0158 addendum 2 remainder): `"registry"` (matches a
    `DANGEROUS_OPERATIONS` library for the language), `"no-capability"`
    (a curated `NO_CAPABILITY_MODULES` stdlib entry), `"vetted"` (a
    locatable dependency scanned by the same capability engine and cached
    per package+version), or `"unknown"` -- the loud, never-silent failure
    case a plain-substring scanner cannot resolve any other way."""

    model_config = ConfigDict(frozen=True)

    import_name: str
    resolution: str  # "registry" | "no-capability" | "vetted" | "unknown"
    detail: str = ""


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0180
class ClosedWorldAccounting(BaseModel):
    """Full closed-world import accounting for one vetted package (T-0158
    addendum 2 remainder): every top-level import resolved to registry/
    no-capability/vetted/unknown, plus the audit accounting line count
    (N registry ops, M vetted libraries, K no-capability entries, J
    unknown) T-0158's addendum 2 describes. `source_available=False` means
    the package's source could not be located locally -- an honest "could
    not check", never silently treated as zero unknowns."""

    model_config = ConfigDict(frozen=True)

    ecosystem: str
    name: str
    version: str
    resolutions: tuple[ImportResolution, ...] = ()
    source_available: bool = True

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    @property
    def registry_count(self) -> int:
        """Imports resolved against a `DANGEROUS_OPERATIONS` registry library."""
        return sum(1 for r in self.resolutions if r.resolution == "registry")

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    @property
    def no_capability_count(self) -> int:
        """Imports resolved against the curated `NO_CAPABILITY_MODULES` set."""
        return sum(1 for r in self.resolutions if r.resolution == "no-capability")

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    @property
    def vetted_count(self) -> int:
        """Imports resolved to a locatable dependency scanned+cached by the
        same capability engine."""
        return sum(1 for r in self.resolutions if r.resolution == "vetted")

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    @property
    def unknown_count(self) -> int:
        """Imports that resolved to NONE of registry/no-capability/vetted --
        the closed-world proof's failure count; non-zero means the proof
        does not hold for this package."""
        return sum(1 for r in self.resolutions if r.resolution == "unknown")

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    @property
    def closed(self) -> bool:
        """True iff every import resolved (`unknown_count == 0`) AND the
        source was actually available to walk -- an unavailable source
        can never claim closure by omission."""
        return self.source_available and self.unknown_count == 0

    # frob:doc docs/modules/vet.md#closed-world-import-accounting-t-0180
    def accounting_line(self) -> str:
        """The human-readable audit line T-0158 addendum 2 describes:
        'N registry ops, M vetted libraries, K explicit no-capability
        entries, J unknown' for `name@version`."""
        prefix = f"{self.ecosystem}/{self.name}@{self.version}"
        if not self.source_available:
            return f"{prefix}: source unavailable, closed-world accounting skipped"
        library_noun = "library" if self.vetted_count == 1 else "libraries"
        return (
            f"{prefix}: "
            f"{self.registry_count} registry op(s), "
            f"{self.vetted_count} vetted {library_noun}, "
            f"{self.no_capability_count} explicit no-capability entries, "
            f"{self.unknown_count} unknown"
        )
