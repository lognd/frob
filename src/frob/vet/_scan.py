"""`scan_tree`: the full-lockfile `frob vet` pass (docs/modules/vet.md "Mechanics").

Runs VET001 (allow conformance), VET011 (cooldown quarantine), VET-JS
(lifecycle scripts), typosquat distance, and VET005 (osv-scanner, opt-in)
over every dependency in the project's lockfile.
"""

# frob:waive TEST005 reason="module line coverage 66.1%, debt T-0160"

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from typani import Err, Ok
from typani.result import Result

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.strata import CveFingerprint
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
from frob.vet._allow import _load_vet_config
from frob.vet._lockfile import _find_all_lockfiles, _parse_lockfile
from frob.vet._models import (
    Dependency,
    PackageVerdict,
    VetConfig,
    VetError,
    VetReport,
    capability_diff,
)

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "vet.db"


def _artifact_hash(source_dir: Path, *, max_files: int = 500) -> str:
    """sha256 over sorted (relpath, content) pairs -- the content address the
    verdict cache keys on (docs/modules/vet.md "Verdict cache")."""
    digest = hashlib.sha256()
    # frob:ticket T-0471
    files = sorted(iter_files(source_dir))[:max_files]
    for path in files:
        try:
            digest.update(path.relative_to(source_dir).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        except OSError as exc:
            _log.debug("vet: skipping unreadable %s during hashing: %s", path, exc)
    return digest.hexdigest()


def _lockfile_name(dep: Dependency, root: Path) -> str:
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


# frob:waive DUP001 reason="dup grouped this with frob.gates's \
# _doc001_orphan purely on generic Violation(...)-builder shape; different \
# gate family (dependency-vet vs doc-graph), unrelated rules"
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


def _scan_source(
    dep: Dependency,
    source_dir: Path,
    lockfile_name: str,
    cfg: VetConfig,
    cache_path: Path,
) -> tuple[set[str], list[str], list[Violation]]:
    """Capability + obfuscation + VET002/VET003 + ecosystem scan of a located
    dependency source. Returns `(capabilities, signals, violations)` and stores
    the fresh verdict for future escalation diffs."""
    artifact_hash = _artifact_hash(source_dir)
    capabilities, signals, violations = _capability_and_fingerprint_signals(
        dep, source_dir, lockfile_name
    )

    for maybe in (
        _vet002_violation(dep, cfg, lockfile_name, capabilities),
        _vet003_violation(
            dep, cache_path, lockfile_name, capabilities, signals, artifact_hash
        ),
    ):
        if maybe is not None:
            violations.append(maybe)

    violations.extend(_ecosystem_rules(dep, source_dir, lockfile_name))
    _store_verdict_if_hashed(dep, cache_path, artifact_hash, capabilities, signals)
    return capabilities, signals, violations


def _capability_and_fingerprint_signals(
    dep: Dependency, source_dir: Path, lockfile_name: str
) -> tuple[set[str], list[str], list[Violation]]:
    """Capability, obfuscation, and CVE-fingerprint scan of `source_dir`
    (VET004/VET006's inputs)."""
    signals: list[str] = []
    violations: list[Violation] = []

    observed, decode_to_exec = _capability._scan_directory_capabilities(source_dir)
    capabilities = set(observed)
    if decode_to_exec:
        signals.append("decode-to-exec")

    obfuscation_signals = _obfuscation._scan_directory_obfuscation(source_dir)
    signals.extend(obfuscation_signals)
    if obfuscation_signals or decode_to_exec:
        violations.append(_vet004_violation(dep, lockfile_name, signals))

    # T-0153: CVE fingerprint scan -- surfaces a VET006 finding (and a
    # "cve-fingerprint" signal, persisted onto the stored PackageVerdict
    # below) when a dependency's source matches a canonical vulnerable-
    # usage-class needle, independent of whether the dependency's PINNED
    # VERSION has a filed osv advisory (VET005's join).
    fingerprint_matches = _capability._scan_directory_fingerprints(source_dir)
    if fingerprint_matches:
        signals.append("cve-fingerprint")
        violations.append(_vet006_violation(dep, lockfile_name, fingerprint_matches))
    return capabilities, signals, violations


def _ecosystem_rules(
    dep: Dependency, source_dir: Path, lockfile_name: str
) -> list[Violation]:
    """Ecosystem-specific rule violations (pypi/cargo) for `dep`."""
    if dep.ecosystem == "pypi":
        return list(_ecosystem._python_rules(dep, source_dir, lockfile_name))
    if dep.ecosystem == "cargo":
        return list(_ecosystem._rust_rules(dep, source_dir, lockfile_name))
    return []


def _store_verdict_if_hashed(
    dep: Dependency,
    cache_path: Path,
    artifact_hash: str,
    capabilities: set[str],
    signals: list[str],
) -> None:
    """Persist the fresh `PackageVerdict` for future escalation diffs, if
    `source_dir` produced a real artifact hash."""
    if not artifact_hash:
        return
    _cache._store_verdict(
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


def _prehook_violations(
    dep: Dependency, root: Path, cfg: VetConfig, cache_path: Path, lockfile_name: str
) -> tuple[list[Violation], list[str]]:
    """VET011 quarantine + typosquat checks for a not-yet-allowed dependency."""
    violations: list[Violation] = []
    signals: list[str] = []
    quarantine_v = _quarantine_violation(dep, root, cfg, cache_path)
    if quarantine_v is not None:
        violations.append(quarantine_v)
        if quarantine_v.severity is Severity.ERROR:
            signals.append("quarantined")

    typosquat_of = _typosquat._find_typosquat(dep.ecosystem, dep.name)
    if typosquat_of is not None:
        violations.append(
            Violation(
                rule="VET-JS003",
                severity=Severity.ERROR,
                file=lockfile_name,
                line=0,
                message=f"{dep.name}: possible typosquat of {typosquat_of}",
            )
        )
        signals.append("typosquat")
    return violations, signals


def _process_dependency(
    dep: Dependency,
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    is_new: bool,
    fetch: bool,
) -> tuple[list[Violation], PackageVerdict]:
    """All per-dependency checks; returns its violations plus its verdict."""
    capabilities: set[str] = set()
    signals: list[str] = []
    violations: list[Violation] = []

    v001 = _vet001_violation(dep, cfg, lockfile.name)
    if v001 is not None:
        violations.append(v001)

    _scan_located_source(
        dep, root, lockfile, cfg, cache_path, capabilities, signals, violations
    )
    _apply_npm_and_prehook_checks(
        dep, root, cfg, cache_path, lockfile, is_new, fetch, violations, signals
    )

    verdict = PackageVerdict(
        name=dep.name,
        version=dep.version,
        ecosystem=dep.ecosystem,
        capabilities=frozenset(capabilities),
        signals=tuple(signals),
    )
    return violations, verdict


def _apply_npm_and_prehook_checks(
    dep: Dependency,
    root: Path,
    cfg: VetConfig,
    cache_path: Path,
    lockfile: Path,
    is_new: bool,
    fetch: bool,
    violations: list[Violation],
    signals: list[str],
) -> None:
    """Fold the npm non-registry rule and (for new deps, when fetching)
    prehook quarantine/typosquat violations into `violations`/`signals`,
    in place."""
    if dep.ecosystem == "npm":
        js_violation = _ecosystem._npm_non_registry_rule(dep, lockfile.name)
        if js_violation is not None:
            violations.append(js_violation)

    if is_new and fetch:
        pre_violations, pre_signals = _prehook_violations(
            dep, root, cfg, cache_path, lockfile.name
        )
        violations.extend(pre_violations)
        signals.extend(pre_signals)


def _source_unavailable_violation(dep: Dependency, lockfile_name: str) -> Violation:
    """T-0400 audit finding #1: a dependency `frob vet` never read must
    never be indistinguishable from one it read and found clean -- an
    honest, fail-CLOSED ERROR finding (mirrors `_timeout_verdict`'s
    already-honest VET-TIMEOUT shape) so an allow-listed package whose
    source is not present locally cannot silently pass as "approved"."""
    return Violation(
        rule="VET-SOURCE-UNAVAILABLE",
        severity=Severity.ERROR,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}@{dep.version}: source not found locally "
            f"(not installed/cached); capability scan could not run -- "
            f"this dependency was NEVER READ, not verified clean"
        ),
    )


def _scan_located_source(
    dep: Dependency,
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    capabilities: set[str],
    signals: list[str],
    violations: list[Violation],
) -> None:
    """Locate `dep`'s source and, if found, scan it, folding results (in
    place) into `capabilities`/`signals`/`violations`. T-0400: when source
    cannot be located this now appends a `VET-SOURCE-UNAVAILABLE` ERROR
    violation (fail-closed) instead of silently returning an empty,
    indistinguishable-from-clean capability set."""
    source_dir = _source._locate_source(root, dep.ecosystem, dep.name, dep.version)
    if source_dir is None:
        signals.append("source-unavailable")
        violations.append(_source_unavailable_violation(dep, lockfile.name))
        _log.warning(
            "vet: %s/%s@%s: source unavailable locally; NEVER SCANNED "
            "(fail-closed VET-SOURCE-UNAVAILABLE)",
            dep.ecosystem,
            dep.name,
            dep.version,
        )
        return
    caps, src_signals, src_violations = _scan_source(
        dep, source_dir, lockfile.name, cfg, cache_path
    )
    capabilities |= caps
    signals.extend(src_signals)
    violations.extend(src_violations)


def _timeout_verdict(
    dep: Dependency, lockfile_name: str
) -> tuple[Violation, PackageVerdict]:
    """T-0208: an honest TIMEOUT outcome for a dependency whose per-package
    budget expired -- never silently dropped from the report. WARN, not
    ERROR: a timeout means "not fully checked", not "found bad"."""
    violation = Violation(
        rule="VET-TIMEOUT",
        severity=Severity.WARN,
        file=lockfile_name,
        line=0,
        message=(
            f"{dep.name}@{dep.version}: per-package scan budget exceeded; "
            f"verdict incomplete"
        ),
    )
    verdict = PackageVerdict(
        name=dep.name,
        version=dep.version,
        ecosystem=dep.ecosystem,
        signals=("timeout",),
    )
    return violation, verdict


def _scan_dependencies(
    deps: tuple[Dependency, ...],
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    fetch: bool,
    *,
    timeout: float | None = None,
    jobs: int = 1,
) -> tuple[list[Violation], list[PackageVerdict]]:
    """Run every per-dependency check over `deps`, collecting violations/verdicts.

    `timeout` (T-0208), if set, bounds each package's `_process_dependency`
    call in its own thread; on expiry the package gets an honest TIMEOUT
    verdict (`_timeout_verdict`) instead of being silently skipped -- the
    thread itself is abandoned (Python cannot preempt a running thread) and
    the scan moves on. `jobs` > 1 runs packages concurrently in a thread
    pool: this is DISCLOSED as best-effort, not fully isolated -- the sqlite
    verdict cache (`_cache.py`) and the registry publish-date disk cache
    (`_registry.py`) both open short-lived per-call connections with no
    explicit cross-process/cross-thread locking beyond sqlite's own busy
    handling (already tolerant of a failed connect/write, logged and
    dropped, never fatal -- see `_cache._connect`). Under concurrent writes
    a verdict cache write can silently lose a race and be overwritten by
    another thread's write for the same key; this does not corrupt the
    cache or crash the scan, it just means the "most recent" write wins
    non-deterministically. `jobs=1` (the default) has none of this risk.
    Progress is logged at INFO as each package completes: `M/N name`."""
    allow = dict(cfg.allow)
    if jobs <= 1:
        return _scan_dependencies_sequential(
            deps, root, lockfile, cfg, cache_path, fetch, timeout, allow
        )
    return _scan_dependencies_parallel(
        deps, root, lockfile, cfg, cache_path, fetch, timeout, allow, jobs
    )


def _scan_dependencies_sequential(
    deps: tuple[Dependency, ...],
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    fetch: bool,
    timeout: float | None,
    allow: dict[str, tuple[str, ...] | bool],
) -> tuple[list[Violation], list[PackageVerdict]]:
    """`_scan_dependencies`'s `jobs<=1` path: one package at a time."""
    violations: list[Violation] = []
    verdicts: list[PackageVerdict] = []
    total = len(deps)
    for i, dep in enumerate(deps, start=1):
        _log.info("vet: package %d/%d %s", i, total, dep.name)
        is_new = dep.name not in allow
        dep_violations, verdict = _run_with_timeout(
            dep, root, lockfile, cfg, cache_path, is_new, fetch, timeout
        )
        violations.extend(dep_violations)
        verdicts.append(verdict)
    return violations, verdicts


def _scan_dependencies_parallel(
    deps: tuple[Dependency, ...],
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    fetch: bool,
    timeout: float | None,
    allow: dict[str, tuple[str, ...] | bool],
    jobs: int,
) -> tuple[list[Violation], list[PackageVerdict]]:
    """`_scan_dependencies`'s `jobs>1` path: a thread pool of best-effort
    concurrent per-package scans (see `_scan_dependencies`'s docstring for
    the concurrency-safety disclosure)."""
    violations: list[Violation] = []
    verdicts: list[PackageVerdict] = []
    total = len(deps)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [
            (
                dep,
                pool.submit(
                    _run_with_timeout,
                    dep,
                    root,
                    lockfile,
                    cfg,
                    cache_path,
                    dep.name not in allow,
                    fetch,
                    timeout,
                ),
            )
            for dep in deps
        ]
        for i, (dep, fut) in enumerate(futures, start=1):
            dep_violations, verdict = fut.result()
            _log.info("vet: package %d/%d %s", i, total, dep.name)
            violations.extend(dep_violations)
            verdicts.append(verdict)
    return violations, verdicts


# CORRECTNESS NOTE (review round 1 caught this): a `with
# ThreadPoolExecutor(...)` block's `__exit__` calls `shutdown(wait=True)`
# unconditionally, including when the body returns early on a timeout --
# so a naive `with pool: ... except FutureTimeoutError: return ...` still
# blocks the caller for the FULL underlying task duration, not `timeout`,
# defeating the entire point of this function. The pool is therefore
# constructed WITHOUT a `with` and explicitly `shutdown(wait=False)` on
# the timeout path so this function returns within ~`timeout` wall-clock
# as promised. The consequence: the abandoned worker thread is not joined
# and keeps running in the background for as long as `_process_dependency`
# takes (Python cannot preempt a running thread) -- for network calls this
# is typically seconds; for a pathological scan it could be the original
# hang, just no longer blocking the rest of the run. This is the same
# disclosed trade-off as `_scan_dependencies`' docstring, made concrete
# here.
def _run_with_timeout(
    dep: Dependency,
    root: Path,
    lockfile: Path,
    cfg: VetConfig,
    cache_path: Path,
    is_new: bool,
    fetch: bool,
    timeout: float | None,
) -> tuple[list[Violation], PackageVerdict]:
    """`_process_dependency`, bounded by `timeout` seconds when set. On
    expiry returns `_timeout_verdict` (T-0208) rather than raising or
    silently dropping the package."""
    if timeout is None:
        return _process_dependency(dep, root, lockfile, cfg, cache_path, is_new, fetch)

    pool = ThreadPoolExecutor(max_workers=1)
    fut = pool.submit(
        _process_dependency, dep, root, lockfile, cfg, cache_path, is_new, fetch
    )
    try:
        result = fut.result(timeout=timeout)
    except FutureTimeoutError:
        _log.warning(
            "vet: %s/%s@%s: exceeded %.1fs per-package timeout; "
            "recording TIMEOUT verdict (worker thread abandoned, not joined)",
            dep.ecosystem,
            dep.name,
            dep.version,
            timeout,
        )
        pool.shutdown(wait=False)
        violation, verdict = _timeout_verdict(dep, lockfile.name)
        return [violation], verdict
    pool.shutdown(wait=False)
    return result


def _lifecycle_violations(
    root: Path, cfg: VetConfig
) -> tuple[list[Violation], list[str]]:
    """VET-JS: node_modules lifecycle scripts not covered by [vet.allow]."""
    violations: list[Violation] = []
    skipped: list[str] = []
    hooks = _lifecycle._scan_lifecycle_scripts(root)
    if not (root / "node_modules").is_dir():
        skipped.append("VET-JS: no node_modules present")
    allow = dict(cfg.allow)
    for name, scripts in hooks.items():
        if name in allow:
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
    return violations, skipped


def _osv_violations(
    lockfile: Path, cfg: VetConfig
) -> tuple[list[Violation], list[str]]:
    """VET005: osv-scanner advisories, or a skipped-note when unavailable/off."""
    if not cfg.osv:
        return [], ["VET005: osv disabled ([vet].osv = false)"]
    if not _osv._is_available():
        return [], ["VET005: osv-scanner not on PATH"]
    advisories = _osv._run_osv_scan(lockfile)
    if advisories is None:
        return [], ["VET005: osv-scanner invocation failed"]
    violations: list[Violation] = []
    for adv in advisories:
        fixed_note = f"; fixed in {adv.fixed_version}" if adv.fixed_version else ""
        violations.append(
            Violation(
                rule="VET005",
                severity=Severity.ERROR,
                file=lockfile.name,
                line=0,
                message=f"{adv.package}@{adv.version}: {adv.advisory_id}{fixed_note}",
            )
        )
    return violations, []


def _collect_supplementary_findings(
    project_root: Path, lockfile: Path, cfg: VetConfig, violations: list[Violation]
) -> list[str]:
    """Fold JS-lifecycle (if applicable) and osv-scanner violations into
    `violations` in place; return the combined skipped-note list."""
    skipped: list[str] = []
    if lockfile.name in ("package-lock.json", "pnpm-lock.yaml"):
        lc_violations, lc_skipped = _lifecycle_violations(project_root, cfg)
        violations.extend(lc_violations)
        skipped.extend(lc_skipped)

    osv_violations, osv_skipped = _osv_violations(lockfile, cfg)
    violations.extend(osv_violations)
    skipped.extend(osv_skipped)
    return skipped


def _resolve_lockfiles_and_deps(
    root: Path,
) -> Result[
    tuple[tuple[tuple[Path, tuple[Dependency, ...]], ...], Path, VetConfig, Path],
    VetError,
]:
    """Locate EVERY supported lockfile under `root` (T-0400 audit finding
    #2 -- a polyglot repo's second lockfile must not go unscanned), parse
    each one's dependencies, and resolve the project root + `[vet]` config
    + cache path `scan_tree` needs (shared across every lockfile found)."""
    lockfiles = _find_all_lockfiles(root)
    if not lockfiles:
        _log.warning(
            "vet: no supported lockfile (uv.lock, package-lock.json, "
            "pnpm-lock.yaml, Cargo.lock) under %s",
            root,
        )
        return Err(VetError.LockfileUnsupported)

    parsed_lockfiles: list[tuple[Path, tuple[Dependency, ...]]] = []
    for lockfile in lockfiles:
        parsed = _parse_lockfile(lockfile)
        if parsed.is_err:
            return Err(parsed.danger_err)
        deps = parsed.danger_ok
        _log.info("vet: scanning %d dependency(ies) from %s", len(deps), lockfile)
        parsed_lockfiles.append((lockfile, deps))

    # T-0221: `root` may itself be a lockfile path (_find_all_lockfiles
    # returns it directly, as a 1-tuple). Project-relative lookups (config,
    # cache) need the containing directory, never the lockfile path itself.
    project_root = root if root.is_dir() else lockfiles[0].parent

    cfg = _load_vet_config(project_root)
    cache_path = project_root / _CACHE_REL
    if not cfg.present:
        _log.info("vet: no [vet] section; advisory-only mode")
    return Ok((tuple(parsed_lockfiles), project_root, cfg, cache_path))


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="scan_tree 84.0% branch cover, debt T-0160"
# frob:tests tests/test_vet.py::TestScanTreeLockArg.test_scan_tree_lockfile_arg
# frob:tests tests/test_vet.py::TestScanTreeLockArg.test_scan_tree_unsupp_err
def scan_tree(
    root: Path,
    *,
    fetch: bool = True,
    timeout: float | None = None,
    jobs: int = 1,
) -> Result[VetReport, VetError]:
    """Full-lockfile vet pass: allow conformance, quarantine, typosquat,
    JS lifecycle scripts, and the optional osv-scanner adapter. `timeout`
    (T-0208) bounds each package's scan in seconds; on expiry that package
    gets an honest VET-TIMEOUT verdict, never a silent skip. `jobs` > 1 runs
    packages concurrently -- see `_scan_dependencies`'s docstring for the
    shared-cache risk this discloses before you raise it above 1.

    T-0400: scans EVERY supported lockfile found under `root` (uv.lock,
    package-lock.json, pnpm-lock.yaml, Cargo.lock), not just the first one a
    fixed-order search hits -- a polyglot repo with both a `uv.lock` and a
    `package-lock.json` used to have its entire npm dependency set silently
    unscanned. Verdicts/violations/skipped-notes from every lockfile are
    merged into one report."""
    resolved = _resolve_lockfiles_and_deps(root)
    if resolved.is_err:
        return Err(resolved.danger_err)
    parsed_lockfiles, project_root, cfg, cache_path = resolved.danger_ok

    violations: list[Violation] = []
    verdicts: list[PackageVerdict] = []
    skipped: list[str] = []
    for lockfile, deps in parsed_lockfiles:
        lf_violations, lf_verdicts = _scan_dependencies(
            deps,
            project_root,
            lockfile,
            cfg,
            cache_path,
            fetch,
            timeout=timeout,
            jobs=jobs,
        )
        violations.extend(lf_violations)
        verdicts.extend(lf_verdicts)
        skipped.extend(
            _collect_supplementary_findings(project_root, lockfile, cfg, violations)
        )

    report = VetReport(
        verdicts=tuple(verdicts),
        violations=tuple(violations),
        enforce=cfg.enforce,
        advisory_only=not cfg.present,
        skipped=tuple(skipped),
    )
    _log.info(
        "vet: scan complete: %d lockfile(s), %d verdict(s), %d violation(s), "
        "enforce=%s",
        len(parsed_lockfiles),
        len(verdicts),
        len(violations),
        cfg.enforce,
    )
    return Ok(report)


__all__ = ["scan_tree"]
