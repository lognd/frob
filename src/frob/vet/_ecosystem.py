"""Cheap per-ecosystem rules (docs/vet.md "Python, Rust, C/C++: same care,
ecosystem-shaped" + "JavaScript/TypeScript: first-priority ecosystem").

Each function takes a located local source directory (see `_source.py`) and
returns the violations it can produce from that. Every rule here is a local
file-shape check -- no network, no registry metadata -- which is why they are
"cheap" (0.2.x candidates that need registry/wheel-availability data, such as
VET-PY001's "when a wheel exists" clause and VET-JS002's full dependency-
confusion resolution, are noted inline and left for a follow-up ticket
rather than half-implemented against data this scan doesn't have).
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.vet._models import Dependency

_log = get_logger(__name__)


def python_rules(
    dep: Dependency, source_dir: Path, lockfile_name: str
) -> list[Violation]:
    """VET-PY001 (executable setup.py present) and VET-PY002 (.pth files) --
    VET-PY003 (pickle/marshal payloads) folds in here too.

    Cut: VET-PY001's "when a wheel exists" qualifier and VET-PY004
    (index-priority confusion) need registry metadata this local-cache-only
    scan does not have; documented, not implemented.
    """
    violations: list[Violation] = []

    setup_py = source_dir / "setup.py"
    if setup_py.is_file():
        try:
            text = setup_py.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log.warning("vet: could not read %s: %s", setup_py, exc)
            text = ""
        if "cmdclass" in text:
            violations.append(
                Violation(
                    rule="VET-PY001",
                    severity=Severity.ERROR,
                    file=lockfile_name,
                    line=0,
                    message=(
                        f"{dep.name}@{dep.version}: setup.py declares cmdclass "
                        f"(install-time code execution)"
                    ),
                )
            )

    pth_files = list(source_dir.glob("*.pth"))
    if pth_files:
        violations.append(
            Violation(
                rule="VET-PY002",
                severity=Severity.ERROR,
                file=lockfile_name,
                line=0,
                message=(
                    f"{dep.name}@{dep.version}: ships {len(pth_files)} .pth file(s) "
                    f"(interpreter-startup code execution)"
                ),
            )
        )

    pickle_files = [
        p
        for p in source_dir.rglob("*")
        if p.suffix in (".pkl", ".pickle") and p.is_file()
    ]
    if pickle_files:
        violations.append(
            Violation(
                rule="VET-PY003",
                severity=Severity.WARN,
                file=lockfile_name,
                line=0,
                message=(
                    f"{dep.name}@{dep.version}: ships {len(pickle_files)} pickle "
                    f"payload(s) in package data (serialized-code load == eval)"
                ),
            )
        )
    return violations


def rust_rules(
    dep: Dependency, source_dir: Path, lockfile_name: str
) -> list[Violation]:
    """VET-RS001 (build.rs capability-scanned as a normal package) and
    VET-RS002 (proc-macro crate presence).

    Cut: VET-RS003 ([patch]/git substitutions) needs Cargo.lock `source`
    field parsing this MVP's lockfile parser doesn't capture; documented,
    not implemented.
    """
    from frob.vet._capability import scan_file_capabilities

    violations: list[Violation] = []

    build_rs = source_dir / "build.rs"
    if build_rs.is_file():
        capabilities = scan_file_capabilities(build_rs)
        if capabilities:
            violations.append(
                Violation(
                    rule="VET-RS001",
                    severity=Severity.ERROR,
                    file=lockfile_name,
                    line=0,
                    message=(
                        f"{dep.name}@{dep.version}: build.rs exercises "
                        f"{', '.join(sorted(capabilities))} at cargo-build time"
                    ),
                )
            )

    cargo_toml = source_dir / "Cargo.toml"
    if cargo_toml.is_file():
        try:
            text = cargo_toml.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log.warning("vet: could not read %s: %s", cargo_toml, exc)
            text = ""
        if "proc-macro" in text and "true" in text:
            violations.append(
                Violation(
                    rule="VET-RS002",
                    severity=Severity.ERROR,
                    file=lockfile_name,
                    line=0,
                    message=(
                        f"{dep.name}@{dep.version}: proc-macro crate (executes "
                        f"in the compiler; requires [vet.allow] declaration)"
                    ),
                )
            )
    return violations


def npm_non_registry_rule(dep: Dependency, lockfile_name: str) -> Violation | None:
    """VET-JS004: git/http/file dependency sources are declarable-only."""
    if not dep.resolved:
        return None
    non_registry_prefixes = ("git+", "git://", "http://", "https://github.com", "file:")
    is_non_registry = dep.resolved.startswith(non_registry_prefixes)
    if is_non_registry and "registry.npmjs.org" not in dep.resolved:
        return Violation(
            rule="VET-JS004",
            severity=Severity.WARN,
            file=lockfile_name,
            line=0,
            message=(
                f"{dep.name}@{dep.version}: resolves to a non-registry source "
                f"({dep.resolved}); declarable-only, review the pin"
            ),
        )
    return None


__all__ = ["npm_non_registry_rule", "python_rules", "rust_rules"]
