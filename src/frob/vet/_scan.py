"""`scan_tree`: the full-lockfile `frob vet` pass (docs/vet.md "Mechanics").

Runs VET001 (allow conformance), VET011 (cooldown quarantine), VET-JS
(lifecycle scripts), typosquat distance, and VET005 (osv-scanner, opt-in)
over every dependency in the project's lockfile.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.vet import (
    _cache,
    _capability,
    _ecosystem,
    _lifecycle,
    _obfuscation,
    _osv,
    _registry,
    _source,
    _typosquat,
)
from frob.vet._allow import load_vet_config
from frob.vet._lockfile import find_lockfile, parse_lockfile
from frob.vet._models import (
    Dependency,
    PackageVerdict,
    VetError,
    VetReport,
    capability_diff,
)

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "vet.db"


def _artifact_hash(source_dir: Path, *, max_files: int = 500) -> str:
    """sha256 over sorted (relpath, content) pairs -- the content address the
    verdict cache keys on (docs/vet.md "Verdict cache")."""
    digest = hashlib.sha256()
    files = sorted(p for p in source_dir.rglob("*") if p.is_file())[:max_files]
    for path in files:
        try:
            digest.update(path.relative_to(source_dir).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        except OSError as exc:
            _log.debug("vet: skipping unreadable %s during hashing: %s", path, exc)
    return digest.hexdigest()


def _is_allowed(dep: Dependency, allow: dict) -> bool:
    return dep.name in allow


def _quarantine_violation(
    dep: Dependency, root: Path, cfg, cache_path: Path
) -> Violation | None:
    """VET011: ERROR if newly published within the cooldown window, WARN if
    the publish date could not be verified (never a hard block offline)."""
    lookup = _registry.fetch_publish_date(
        dep.ecosystem,
        dep.name,
        dep.version,
        cache_path=cache_path,
        base_url=cfg.registry_base_url,
    )
    if not lookup.ok:
        return Violation(
            rule="VET011",
            severity=Severity.WARN,
            file=str(_lockfile_name(dep, root)),
            line=0,
            message=f"{dep.name}@{dep.version}: could not verify publish date",
        )
    if lookup.published_at is None:
        return None
    age_days = (datetime.now(UTC) - lookup.published_at.astimezone(UTC)).days
    if age_days < cfg.quarantine_days:
        return Violation(
            rule="VET011",
            severity=Severity.ERROR,
            file=str(_lockfile_name(dep, root)),
            line=0,
            message=(
                f"{dep.name}@{dep.version}: quarantined: published {age_days} "
                f"day(s) ago; add to [vet.allow] after review"
            ),
        )
    return None


def _lockfile_name(dep: Dependency, root: Path) -> str:
    return dep.ecosystem


def scan_tree(root: Path, *, fetch: bool = True) -> Result[VetReport, VetError]:
    """Full-lockfile vet pass: allow conformance, quarantine, typosquat,
    JS lifecycle scripts, and the optional osv-scanner adapter."""
    lockfile = find_lockfile(root)
    if lockfile is None:
        _log.warning(
            "vet: no supported lockfile (uv.lock, package-lock.json, "
            "pnpm-lock.yaml, Cargo.lock) under %s",
            root,
        )
        return Err(VetError.LockfileUnsupported)

    parsed = parse_lockfile(lockfile)
    if parsed.is_err:
        return Err(parsed.danger_err)
    deps = parsed.danger_ok
    _log.info("vet: scanning %d dependency(ies) from %s", len(deps), lockfile)

    cfg = load_vet_config(root)
    cache_path = root / _CACHE_REL

    violations: list[Violation] = []
    verdicts: list[PackageVerdict] = []
    skipped: list[str] = []

    if not cfg.present:
        _log.info("vet: no [vet] section; advisory-only mode")

    new_deps = [d for d in deps if not _is_allowed(d, dict(cfg.allow))]

    for dep in deps:
        capabilities: set[str] = set()
        signals: list[str] = []
        artifact_hash = ""

        allowed = _is_allowed(dep, dict(cfg.allow))
        if cfg.present and not allowed:
            violations.append(
                Violation(
                    rule="VET001",
                    severity=Severity.ERROR,
                    file=lockfile.name,
                    line=0,
                    message=(
                        f"{dep.name}@{dep.version}: no [vet.allow] entry; "
                        f"add `{dep.name} = true` (or a reason list) after review"
                    ),
                )
            )

        # -- capability scan (docs/vet.md "Mechanics") -------------------
        source_dir = _source.locate_source(root, dep.ecosystem, dep.name, dep.version)
        if source_dir is None:
            signals.append("source-unavailable")
            _log.info(
                "vet: %s/%s@%s: source unavailable locally; empty capability set",
                dep.ecosystem,
                dep.name,
                dep.version,
            )
        else:
            artifact_hash = _artifact_hash(source_dir)
            observed, decode_to_exec = _capability.scan_directory_capabilities(
                source_dir
            )
            capabilities |= observed
            if decode_to_exec:
                signals.append("decode-to-exec")

            obfuscation_signals = _obfuscation.scan_directory_obfuscation(source_dir)
            signals.extend(obfuscation_signals)
            if obfuscation_signals or decode_to_exec:
                violations.append(
                    Violation(
                        rule="VET004",
                        severity=Severity.ERROR,
                        file=lockfile.name,
                        line=0,
                        message=(
                            f"{dep.name}@{dep.version}: obfuscation signal(s): "
                            f"{', '.join(signals)}"
                        ),
                    )
                )

            # -- VET002: observed capability not declared --------------
            declared = cfg.allow.get(dep.name)
            if isinstance(declared, tuple):
                undeclared = sorted(capabilities - set(declared))
                if undeclared:
                    violations.append(
                        Violation(
                            rule="VET002",
                            severity=Severity.ERROR,
                            file=lockfile.name,
                            line=0,
                            message=(
                                f"{dep.name}@{dep.version}: observed capability "
                                f"not declared: {', '.join(undeclared)}"
                            ),
                        )
                    )

            # -- VET003: escalation vs previously stored verdict --------
            previous = _cache.latest_verdict(cache_path, dep.ecosystem, dep.name)
            if previous is not None and previous.artifact_hash != artifact_hash:
                current_verdict = PackageVerdict(
                    name=dep.name,
                    version=dep.version,
                    ecosystem=dep.ecosystem,
                    artifact_hash=artifact_hash,
                    capabilities=frozenset(capabilities),
                    signals=tuple(signals),
                )
                added = capability_diff(previous, current_verdict)
                if added:
                    violations.append(
                        Violation(
                            rule="VET003",
                            severity=Severity.ERROR,
                            file=lockfile.name,
                            line=0,
                            message=(
                                f"{dep.name}: version bump {previous.version} -> "
                                f"{dep.version} adds capability: {', '.join(added)}"
                            ),
                        )
                    )

            # -- ecosystem-specific cheap rules -------------------------
            if dep.ecosystem == "pypi":
                violations.extend(
                    _ecosystem.python_rules(dep, source_dir, lockfile.name)
                )
            elif dep.ecosystem == "cargo":
                violations.extend(_ecosystem.rust_rules(dep, source_dir, lockfile.name))

            if artifact_hash:
                _cache.store_verdict(
                    cache_path,
                    PackageVerdict(
                        name=dep.name,
                        version=dep.version,
                        ecosystem=dep.ecosystem,
                        artifact_hash=artifact_hash,
                        capabilities=frozenset(capabilities),
                        signals=tuple(signals),
                    ),
                )

        if dep.ecosystem == "npm":
            js_violation = _ecosystem.npm_non_registry_rule(dep, lockfile.name)
            if js_violation is not None:
                violations.append(js_violation)

        if dep in new_deps and fetch:
            quarantine_v = _quarantine_violation(dep, root, cfg, cache_path)
            if quarantine_v is not None:
                violations.append(quarantine_v)
                if quarantine_v.severity is Severity.ERROR:
                    signals.append("quarantined")

            typosquat_of = _typosquat.find_typosquat(dep.ecosystem, dep.name)
            if typosquat_of is not None:
                violations.append(
                    Violation(
                        rule="VET-JS003",
                        severity=Severity.ERROR,
                        file=lockfile.name,
                        line=0,
                        message=(f"{dep.name}: possible typosquat of {typosquat_of}"),
                    )
                )
                signals.append("typosquat")

        verdicts.append(
            PackageVerdict(
                name=dep.name,
                version=dep.version,
                ecosystem=dep.ecosystem,
                capabilities=frozenset(capabilities),
                signals=tuple(signals),
            )
        )

    if lockfile.name in ("package-lock.json", "pnpm-lock.yaml"):
        hooks = _lifecycle.scan_lifecycle_scripts(root)
        if not (root / "node_modules").is_dir():
            skipped.append("VET-JS: no node_modules present")
        for name, scripts in hooks.items():
            if name in dict(cfg.allow):
                continue
            violations.append(
                Violation(
                    rule="VET-JS",
                    severity=Severity.ERROR,
                    file="node_modules",
                    line=0,
                    message=(
                        f"{name}: lifecycle script(s) {', '.join(scripts)} "
                        f"not in [vet.allow]"
                    ),
                )
            )

    if cfg.osv:
        if not _osv.is_available():
            skipped.append("VET005: osv-scanner not on PATH")
        else:
            advisories = _osv.run_osv_scan(lockfile)
            if advisories is None:
                skipped.append("VET005: osv-scanner invocation failed")
            else:
                for adv in advisories:
                    fixed_note = (
                        f"; fixed in {adv.fixed_version}" if adv.fixed_version else ""
                    )
                    violations.append(
                        Violation(
                            rule="VET005",
                            severity=Severity.ERROR,
                            file=lockfile.name,
                            line=0,
                            message=(
                                f"{adv.package}@{adv.version}: {adv.advisory_id}"
                                f"{fixed_note}"
                            ),
                        )
                    )
    else:
        skipped.append("VET005: osv disabled ([vet].osv = false)")

    report = VetReport(
        verdicts=tuple(verdicts),
        violations=tuple(violations),
        enforce=cfg.enforce,
        advisory_only=not cfg.present,
        skipped=tuple(skipped),
    )
    _log.info(
        "vet: scan complete: %d verdict(s), %d violation(s), enforce=%s",
        len(verdicts),
        len(violations),
        cfg.enforce,
    )
    return Ok(report)


__all__ = ["scan_tree"]
