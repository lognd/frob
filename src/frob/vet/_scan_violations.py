"""frob.vet._scan_violations -- the per-rule Violation constructor family
(T-1420 LARGE001 split of `_scan.py`): VET001/VET002/VET003/VET004/VET006/
VET011 and the quarantine check each build one `Violation` (or `None`) from
a `Dependency` plus whatever signal that rule cares about. Split verbatim
out of `frob.vet._scan` -- same per-family extraction pattern as this
repo's other LARGE001 splits (directives intact, zero caller-visible
behavior change). Kept together because every one of these is a pure
"decide + format one Violation" leaf with no I/O of its own, as opposed to
`_scan.py`'s orchestration (locating source, running the scan, threading
results through the parallel/sequential dependency loop) that stays behind.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from frob.gates._models import Severity, Violation
from frob.vet import _cache, _registry
from frob.vet._models import Dependency, PackageVerdict, VetConfig, capability_diff

if TYPE_CHECKING:
    from frob.strata import CveFingerprint


def _lockfile_name(dep: Dependency, root: Path) -> str:
    """Placeholder lockfile-name projection -- currently just `dep.ecosystem`."""
    return dep.ecosystem


def _vet011_violation(
    dep: Dependency, root: Path, severity: Severity, message: str
) -> Violation:
    """A VET011 quarantine/verification violation for `dep`."""
    return Violation(
        rule="VET011",
        severity=severity,
        file=str(_lockfile_name(dep, root)),
        line=0,
        message=message,
    )


# frob:enforces SC-DETECTION-QUARANTINE-WINDOW
# frob:enforces CHK-GATE-VET011
def _quarantine_violation(
    dep: Dependency, root: Path, cfg: VetConfig, cache_path: Path
) -> Violation | None:
    """VET011: ERROR if newly published within the cooldown window, WARN if
    the publish date could not be verified (never a hard block offline)."""
    lookup = _registry._fetch_publish_date(
        dep.ecosystem,
        dep.name,
        dep.version,
        cache_path=cache_path,
        base_url=cfg.registry_base_url,
    )
    if not lookup.ok:
        return _vet011_violation(
            dep,
            root,
            Severity.WARN,
            f"{dep.name}@{dep.version}: could not verify publish date",
        )
    if lookup.published_at is None:
        return None
    age_days = (datetime.now(UTC) - lookup.published_at.astimezone(UTC)).days
    if age_days < cfg.quarantine_days:
        return _vet011_violation(
            dep,
            root,
            Severity.ERROR,
            (
                f"{dep.name}@{dep.version}: quarantined: published {age_days} "
                f"day(s) ago; add to [vet.allow] after review"
            ),
        )
    return None


# frob:enforces CHK-GATE-VET001
def _vet001_violation(
    dep: Dependency, cfg: VetConfig, lockfile_name: str
) -> Violation | None:
    """VET001: an enforced [vet] config with no [vet.allow] entry for `dep`."""
    if not cfg.present or dep.name in cfg.allow:
        return None
    return Violation(
        rule="VET001",
        severity=Severity.ERROR,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}@{dep.version}: no [vet.allow] entry; "
            f"add `{dep.name} = true` (or a reason list) after review"
        ),
    )


# frob:invariant INV-025
# frob:tests tests/test_vet.py::TestObfuscationEnsemble.test_high_entropy_string_flagged
# frob:enforces SC-DETECTION-OBFUSCATED-SOURCE
# frob:enforces SC-DETECTION-ENTROPY-BLOB
# frob:enforces SC-DETECTION-TROJAN-SOURCE
# frob:enforces SC-DETECTION-HEX-IDENTIFIER-RATIO
# frob:enforces CHK-GATE-VET004
def _vet004_violation(
    dep: Dependency, lockfile_name: str, signals: list[str]
) -> Violation:
    """VET004: one or more obfuscation/decode-to-exec signals fired."""
    return Violation(
        rule="VET004",
        severity=Severity.ERROR,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}@{dep.version}: obfuscation signal(s): {', '.join(signals)}"
        ),
    )


# frob:enforces CHK-GATE-VET006
def _vet006_violation(
    dep: Dependency, lockfile_name: str, matches: tuple[CveFingerprint, ...]
) -> Violation:
    """VET006 (T-0153): one or more `frob.strata.CVE_FINGERPRINTS` needles
    matched in this dependency's source -- a code-level "this LOOKS LIKE a
    canonical vulnerable-usage class" signal, distinct from VET005's
    dependency-VERSION-shaped osv advisory join (docs/strata/threat.md
    #cve-fingerprints-code-level-pattern-catalog-t-0153)."""
    names = ", ".join(sorted(f"{m.id} ({m.cwe_id})" for m in matches))
    return Violation(
        rule="VET006",
        severity=Severity.WARN,
        file=lockfile_name,
        line=0,
        message=f"{dep.name}@{dep.version}: cve fingerprint match(es): {names}",
    )


# frob:enforces SC-ATTACK-INSTALL-SCRIPT-ABUSE
# frob:enforces SC-DETECTION-MAINTAINER-INSTALLHOOK-NET
# frob:enforces CHK-GATE-VET002
def _vet002_violation(
    dep: Dependency, cfg: VetConfig, lockfile_name: str, capabilities: set[str]
) -> Violation | None:
    """VET002: an observed capability not present in the package's declaration."""
    declared = cfg.allow.get(dep.name)
    if not isinstance(declared, tuple):
        return None
    undeclared = sorted(capabilities - set(declared))
    if not undeclared:
        return None
    return Violation(
        rule="VET002",
        severity=Severity.ERROR,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}@{dep.version}: observed capability "
            f"not declared: {', '.join(undeclared)}"
        ),
    )


# frob:enforces CHK-GATE-VET003
def _vet003_violation(
    dep: Dependency,
    cache_path: Path,
    lockfile_name: str,
    capabilities: set[str],
    signals: list[str],
    artifact_hash: str,
) -> Violation | None:
    """VET003: a version bump that adds a capability vs the stored verdict."""
    previous = _cache._latest_verdict(cache_path, dep.ecosystem, dep.name)
    if previous is None or previous.artifact_hash == artifact_hash:
        return None
    current = PackageVerdict(
        name=dep.name,
        version=dep.version,
        ecosystem=dep.ecosystem,
        artifact_hash=artifact_hash,
        capabilities=frozenset(capabilities),
        signals=tuple(signals),
    )
    added = capability_diff(previous, current)
    if not added:
        return None
    return Violation(
        rule="VET003",
        severity=Severity.ERROR,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}: version bump {previous.version} -> "
            f"{dep.version} adds capability: {', '.join(added)}"
        ),
    )
