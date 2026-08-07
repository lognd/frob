"""Closed-world import accounting (T-0158 addendum 2 remainder, T-0180):
resolves every top-level import a vetted package's source makes to one of
three buckets -- (a) a `DANGEROUS_OPERATIONS` registry library, (b) a
VETTED library (the same capability-scan engine run over the imported
package's own installed source, cached per package+version by reusing the
`frob.vet._cache.py` sqlite pattern), or (c) a LOUD "unknown, unvetted,
uninspected" resolution -- so the audit accounting line ("N registry ops,
M vetted libraries, K explicit no-capability entries, J unknown") is a
checkable fact instead of a sampled guess. T-0158's own sys-audit line only
proves the (kind x language) DANGEROUS_OPERATIONS matrix is exhaustive;
this module proves the separate, narrower claim that a given package's
import graph is FULLY accounted for.

Python only: the import-graph walk uses `ast.parse` (never a substring
guess -- an import is a syntactic fact, not a needle hit). An npm/cargo
import-graph walk is a documented, real gap (docs/modules/vet.md "Honest
limits"), the same posture as `NO_CAPABILITY_MODULES` being a curated
subset of the stdlib rather than an exhaustive one: extending either is
always safe, never silently claimed done ahead of being built.
"""

from __future__ import annotations

import ast
import hashlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _installed_version
from pathlib import Path

from frob.excludes import iter_files
from frob.logging import get_logger
from frob.vet import _cache, _capability, _source
from frob.vet._capability_registry import DANGEROUS_OPERATIONS, NO_CAPABILITY_MODULES
from frob.vet._models import ClosedWorldAccounting, ImportResolution, PackageVerdict

_log = get_logger(__name__)

#: file-count ceiling for both the import-graph walk and the vetted-library
#: content hash -- same safety-valve posture as `_capability.py`'s
#: `max_files`/`_scan.py`'s `_artifact_hash` (a huge vendored tree must
#: never make this unusable).
_MAX_FILES = 300

#: PyPI import-name divergences from the `DANGEROUS_OPERATIONS.library`
#: field this registry cannot derive mechanically (the distribution name
#: on PyPI and the top-level import name are simply different strings for
#: these two libraries) -- an explicit, documented override, not a guess.
_LIBRARY_TO_IMPORT_OVERRIDES: dict[str, str] = {
    "python-dotenv": "dotenv",
    "Pillow": "PIL",
}


def _registry_import_roots(language: str) -> frozenset[str]:
    """Every import-root name a `DANGEROUS_OPERATIONS` entry for `language`
    is reachable through -- the `library` field verbatim, plus the
    documented PyPI distribution-name/import-name override table."""
    roots: set[str] = set()
    for op in DANGEROUS_OPERATIONS:
        if op.language != language:
            continue
        for candidate in op.library.split("/"):
            roots.add(_LIBRARY_TO_IMPORT_OVERRIDES.get(candidate, candidate))
    return frozenset(roots)


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0180
def walk_python_imports(
    source_dir: Path, *, max_files: int = _MAX_FILES
) -> frozenset[str]:
    """Every top-level module name absolutely imported (`import x[.y]`,
    `from x[.y] import z`) across `source_dir`'s `.py` files, via
    `ast.parse` -- never a substring guess. Relative imports
    (`from . import foo`, `from .sub import bar`) are excluded by
    construction: they name a module inside the SAME package, not a
    closed-world dependency this accounting needs to resolve."""
    roots: set[str] = set()
    scanned = 0
    # frob:ticket T-0471
    for path in sorted(iter_files(source_dir, suffix=".py")):
        if scanned >= max_files:
            _log.warning(
                "vet: closed-world import walk truncated at %d file(s) under %s",
                max_files,
                source_dir,
            )
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError) as exc:
            _log.debug("vet: closed-world: skipping unparseable %s: %s", path, exc)
            continue
        scanned += 1
        _collect_import_roots(tree, roots)
    _log.debug(
        "vet: closed-world: walked %d file(s) under %s, %d import root(s)",
        scanned,
        source_dir,
        len(roots),
    )
    return frozenset(roots)


def _collect_import_roots(tree: ast.Module, roots: set[str]) -> None:
    """Add every absolute (non-relative) top-level import root in `tree` to `roots`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import: same package, not a closed-world target
            if node.module:
                roots.add(node.module.split(".")[0])


def _scan_capabilities_best_effort(
    source_dir: Path, import_name: str
) -> frozenset[str]:
    """`_scan_directory_capabilities`'s capability set, degraded to empty on
    a `RecursionError` from a pathologically deep parse tree (a known
    `_capability.py::_comment_byte_spans` recursive-walk limit on some
    real third-party sources) -- vetted-library resolution must stay
    best-effort like every other closed-world lookup here, never crash
    the whole accounting pass over one deeply nested dependency file."""
    try:
        capabilities, _decode_to_exec = _capability._scan_directory_capabilities(
            source_dir
        )
        return capabilities
    except RecursionError:
        _log.warning(
            "vet: closed-world: capability scan of %s (%s) hit a recursion "
            "limit; treating as empty capabilities rather than crashing",
            import_name,
            source_dir,
        )
        return frozenset()
    except Exception:
        # "Best-effort like every other closed-world lookup here, never
        # crash the whole accounting pass" (this function's own
        # docstring) covers any other scan surprise too, not just
        # `RecursionError` (EXHAUST001, T-1371).
        _log.warning(
            "vet: closed-world: capability scan of %s (%s) failed "
            "unexpectedly; treating as empty capabilities rather than "
            "crashing",
            import_name,
            source_dir,
        )
        return frozenset()


def _best_effort_version(import_name: str) -> str:
    """The installed distribution version for `import_name`, or `"unknown"`
    when it cannot be resolved (never raises -- this is best-effort
    metadata for a cache key, not a hard dependency)."""
    try:
        return _installed_version(import_name)
    except PackageNotFoundError:
        return "unknown"
    except Exception:
        # "Never raises -- this is best-effort metadata for a cache key"
        # (this function's own docstring) covers any other metadata-
        # lookup surprise too, not just `PackageNotFoundError`
        # (EXHAUST001, T-1371).
        return "unknown"


def _source_hash(source_dir: Path, *, max_files: int = _MAX_FILES) -> str:
    """sha256 over sorted (relpath, content) pairs -- same content-address
    scheme `_scan.py::_artifact_hash` uses for the primary verdict cache,
    reused here (not reimplemented) so a vetted library's cache key stays
    identical in shape to every other verdict this repo stores."""
    digest = hashlib.sha256()
    # frob:ticket T-0471
    files = sorted(iter_files(source_dir))[:max_files]
    for path in files:
        try:
            digest.update(path.relative_to(source_dir).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
        except OSError as exc:
            _log.debug(
                "vet: closed-world: skipping unreadable %s during hashing: %s",
                path,
                exc,
            )
    return digest.hexdigest()


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0180
def resolve_import(
    import_name: str,
    *,
    root: Path,
    cache_path: Path,
    language: str = "python",
    ecosystem: str = "pypi",
) -> ImportResolution:
    """Classify one imported module name: `"registry"` if it matches a
    `DANGEROUS_OPERATIONS` library for `language`, `"no-capability"` if it
    is a curated `NO_CAPABILITY_MODULES` stdlib entry, `"vetted"` if it is
    already cached OR its source is locatable under `root` (scanned by the
    same capability engine and cached on the spot), else the loud
    `"unknown"` fallthrough. Checked in that order: a registry match is the
    most specific classification available, so it is never shadowed by the
    coarser no-capability/vetted buckets."""
    registry_roots = _registry_import_roots(language)
    if import_name in registry_roots:
        return ImportResolution(
            import_name=import_name,
            resolution="registry",
            detail=f"matches a DANGEROUS_OPERATIONS {language} library",
        )
    if language == "python" and import_name in NO_CAPABILITY_MODULES:
        return ImportResolution(
            import_name=import_name,
            resolution="no-capability",
            detail="curated stdlib module, no effectful surface",
        )
    cached = _cache._latest_verdict(cache_path, ecosystem, import_name)
    if cached is not None:
        return ImportResolution(
            import_name=import_name,
            resolution="vetted",
            detail=(
                f"cached verdict @ {cached.version}, "
                f"capabilities={sorted(cached.capabilities)}"
            ),
        )
    source_dir = _source._locate_source(root, ecosystem, import_name, "unknown")
    if source_dir is not None:
        capabilities = _scan_capabilities_best_effort(source_dir, import_name)
        resolved_version = _best_effort_version(import_name)
        artifact_hash = _source_hash(source_dir)
        verdict = PackageVerdict(
            name=import_name,
            version=resolved_version,
            ecosystem=ecosystem,
            artifact_hash=artifact_hash,
            capabilities=capabilities,
        )
        _cache._store_verdict(cache_path, verdict)
        _log.info(
            "vet: closed-world: scanned+cached %s/%s@%s, capabilities=%s",
            ecosystem,
            import_name,
            resolved_version,
            sorted(capabilities),
        )
        return ImportResolution(
            import_name=import_name,
            resolution="vetted",
            detail=(
                f"scanned+cached @ {resolved_version}, "
                f"capabilities={sorted(capabilities)}"
            ),
        )
    _log.warning(
        "vet: closed-world: %s is UNKNOWN, UNVETTED, UNINSPECTED "
        "(not a registry library, not curated stdlib, source not locatable)",
        import_name,
    )
    return ImportResolution(
        import_name=import_name,
        resolution="unknown",
        detail="not a registry library, not curated stdlib, source not locatable",
    )


# frob:doc docs/modules/vet.md#public-api
# frob:ticket T-0180
def closed_world_accounting(
    root: Path,
    ecosystem: str,
    name: str,
    version: str,
    *,
    cache_path: Path,
) -> ClosedWorldAccounting:
    """The full closed-world import accounting for `name@version` (T-0158
    addendum 2 remainder): locates the package's source under `root`,
    walks its Python imports, and resolves each one via `resolve_import`.
    `source_available=False` (empty `resolutions`) when the source cannot
    be located locally -- an honest "could not check", per docs/modules/
    vet.md "Honest limits", never silently read as zero unknowns."""
    source_dir = _source._locate_source(root, ecosystem, name, version)
    if source_dir is None:
        _log.info(
            "vet: closed-world: no local source for %s/%s@%s; accounting skipped",
            ecosystem,
            name,
            version,
        )
        return ClosedWorldAccounting(
            ecosystem=ecosystem, name=name, version=version, source_available=False
        )
    imports = walk_python_imports(source_dir)
    resolutions = tuple(
        resolve_import(
            import_name, root=root, cache_path=cache_path, ecosystem=ecosystem
        )
        for import_name in sorted(imports)
    )
    accounting = ClosedWorldAccounting(
        ecosystem=ecosystem,
        name=name,
        version=version,
        resolutions=resolutions,
        source_available=True,
    )
    _log.info("vet: closed-world: %s", accounting.accounting_line())
    return accounting


__all__ = [
    "ClosedWorldAccounting",
    "ImportResolution",
    "closed_world_accounting",
    "resolve_import",
    "walk_python_imports",
]
