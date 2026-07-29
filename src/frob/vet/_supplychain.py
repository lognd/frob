"""Project-tree-wide supply-chain structural checks (T-1088).

Unlike `_ecosystem.py` (per-DEPENDENCY-source cheap rules run against a
located package's local copy), the four detectors here run once per
`scan_tree` call against the SCANNED PROJECT'S OWN tracked files -- its
manifests, CI workflows, and tracked binary blobs are purely structural
properties of text/tree-shape frob already has on disk, no fetch, no
registry metadata, same "statically-detectable" class docs/design/
registry/supply-chain.yaml tags them with.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

# Version specs that are NOT an exact pin: caret/tilde ranges, wildcards,
# comparison operators, and the bare npm/cargo "*" catch-all.
_UNPINNED_MARKERS = ("^", "~", "*", ">", "<", "x", "X")

_PYPROJECT_DEP_RE = re.compile(r'"([A-Za-z0-9_.-]+)\s*([^"]*)"')
_PACKAGE_JSON_DEP_RE = re.compile(r'"([A-Za-z0-9_.@/-]+)"\s*:\s*"([^"]+)"')
_CARGO_DEP_RE = re.compile(
    r'^\s*([A-Za-z0-9_-]+)\s*=\s*"([^"]+)"', re.MULTILINE
)


def _read_text_or_empty(path: Path) -> str:
    """`path`'s UTF-8 text (replacement errors) or `""` on an OS read failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("vet: could not read %s: %s", path, exc)
        return ""


def _is_unpinned_spec(spec: str) -> bool:
    """A version spec with no exact pin: empty, or containing a range/
    wildcard marker instead of a single `==`/`=`-style exact version."""
    spec = spec.strip()
    if not spec:
        return True
    if spec.startswith("==") or spec.startswith("="):
        return False
    return any(marker in spec for marker in _UNPINNED_MARKERS) or spec == ""


def _pyproject_unpinned_violations(project_root: Path) -> list[Violation]:
    """VET007 half: scan `pyproject.toml`'s `dependencies = [...]` block for
    specs with no exact pin."""
    violations: list[Violation] = []
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        return violations
    text = _read_text_or_empty(pyproject)
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies") and "=" in stripped:
            in_deps = True
            continue
        if in_deps and stripped.startswith("]"):
            in_deps = False
            continue
        if not in_deps or stripped.startswith("#"):
            continue
        match = _PYPROJECT_DEP_RE.search(stripped)
        if match is None:
            continue
        name, rest = match.group(1), match.group(2)
        if _is_unpinned_spec(rest):
            violations.append(
                Violation(
                    rule="VET007",
                    severity=Severity.WARN,
                    file=str(pyproject),
                    line=0,
                    message=(
                        f"{name}: unpinned dependency spec {stripped!r} "
                        f"in pyproject.toml"
                    ),
                )
            )
    return violations


def _package_json_unpinned_violations(project_root: Path) -> list[Violation]:
    """VET007 half: scan `package.json`'s dependencies/devDependencies for
    specs with no exact pin."""
    violations: list[Violation] = []
    package_json = project_root / "package.json"
    if not package_json.is_file():
        return violations
    text = _read_text_or_empty(package_json)
    for section in ("dependencies", "devDependencies"):
        block_match = re.search(rf'"{section}"\s*:\s*\{{([^}}]*)\}}', text, re.DOTALL)
        if block_match is None:
            continue
        for name, spec in _PACKAGE_JSON_DEP_RE.findall(block_match.group(1)):
            if spec.startswith("git+") or spec.startswith("file:"):
                continue  # SC-DETECTION-NPM-NON-REGISTRY-SOURCE's territory
            if _is_unpinned_spec(spec):
                violations.append(
                    Violation(
                        rule="VET007",
                        severity=Severity.WARN,
                        file=str(package_json),
                        line=0,
                        message=(
                            f"{name}: unpinned dependency spec "
                            f"{spec!r} in package.json ({section})"
                        ),
                    )
                )
    return violations


def _cargo_toml_unpinned_violations(project_root: Path) -> list[Violation]:
    """VET007 half: scan `Cargo.toml`'s `[dependencies]` table for specs
    with no exact pin."""
    violations: list[Violation] = []
    cargo_toml = project_root / "Cargo.toml"
    if not cargo_toml.is_file():
        return violations
    text = _read_text_or_empty(cargo_toml)
    dep_section = re.search(r"\[dependencies\](.*?)(?:\n\[|\Z)", text, re.DOTALL)
    if dep_section is None:
        return violations
    for name, spec in _CARGO_DEP_RE.findall(dep_section.group(1)):
        if _is_unpinned_spec(spec):
            violations.append(
                Violation(
                    rule="VET007",
                    severity=Severity.WARN,
                    file=str(cargo_toml),
                    line=0,
                    message=(
                        f"{name}: unpinned dependency spec "
                        f"{spec!r} in Cargo.toml"
                    ),
                )
            )
    return violations


# frob:enforces SC-ATTACK-UNPINNED-DEPENDENCIES
# frob:enforces CHK-GATE-VET007
# frob:tests tests/test_vet.py::TestSupplyChainUnpinnedDependencies.test_pyproject_caret_range_flagged
def _unpinned_dependency_violations(project_root: Path) -> list[Violation]:
    """VET007: a manifest (pyproject.toml/package.json/Cargo.toml) dependency
    spec with no exact pin -- a purely structural property of the manifest
    text, independent of any lockfile resolution."""
    return [
        *_pyproject_unpinned_violations(project_root),
        *_package_json_unpinned_violations(project_root),
        *_cargo_toml_unpinned_violations(project_root),
    ]


# frob:enforces SC-DETECTION-PYTHON-INSTALL-ARTIFACTS
# frob:enforces CHK-GATE-VET008
# frob:tests tests/test_vet.py::TestSupplyChainInstallArtifacts.test_setup_py_absolute_data_files_flagged
def _python_install_artifact_violations(project_root: Path) -> list[Violation]:
    """VET008: setup.py/setup.cfg `data_files` writing to an absolute path or
    escaping the package via `../` traversal -- an installed artifact landing
    somewhere unexpected on the target filesystem."""
    violations: list[Violation] = []
    for name in ("setup.py", "setup.cfg"):
        path = project_root / name
        if not path.is_file():
            continue
        text = _read_text_or_empty(path)
        if "data_files" not in text:
            continue
        data_files_match = re.search(r"data_files\s*=\s*(\[.*?\])", text, re.DOTALL)
        candidate_text = data_files_match.group(1) if data_files_match else text
        for dest in re.findall(r"""['"]((?:/|\.\./)[^'"]*)['"]""", candidate_text):
            violations.append(
                Violation(
                    rule="VET008",
                    severity=Severity.ERROR,
                    file=str(path),
                    line=0,
                    message=(
                        f"{name}: data_files destination {dest!r} is "
                        f"absolute or escapes the package via '../' "
                        f"traversal (installed artifact lands outside "
                        f"the package)"
                    ),
                )
            )
    return violations


_SHA_REF_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)", re.MULTILINE
)


# frob:enforces SC-DETECTION-UNPINNED-CI-ACTION
# frob:enforces CHK-GATE-VET009
# frob:tests tests/test_vet.py::TestSupplyChainCiActionPin.test_workflow_branch_ref_flagged
def _unpinned_ci_action_violations(project_root: Path) -> list[Violation]:
    """VET009: a GitHub Actions `uses: owner/action@ref` where `ref` is a
    mutable branch/tag rather than a full 40-hex-char commit SHA -- a
    structural property of tracked `.github/workflows/*.yaml` text."""
    violations: list[Violation] = []
    workflows_dir = project_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return violations
    for path in sorted(workflows_dir.glob("*.y*ml")):
        text = _read_text_or_empty(path)
        for action, ref in _USES_RE.findall(text):
            if action.startswith("./"):
                continue  # local composite action, not a supply-chain edge
            if _SHA_REF_RE.match(ref):
                continue
            violations.append(
                Violation(
                    rule="VET009",
                    severity=Severity.ERROR,
                    file=str(path),
                    line=0,
                    message=(
                        f"{action}@{ref}: CI action pinned to a mutable "
                        f"ref, not a full commit SHA"
                    ),
                )
            )
    return violations


_BINARY_ARTIFACT_SUFFIXES = (".whl", ".so", ".node", ".wasm", ".dylib", ".dll", ".a")
_BUILD_RECIPE_NAMES = (
    "Cargo.toml",
    "CMakeLists.txt",
    "setup.py",
    "pyproject.toml",
    "Makefile",
    "package.json",
    "build.rs",
)


def _has_nearby_build_recipe(path: Path, project_root: Path) -> bool:
    """A build recipe file in `path`'s own directory or any ancestor up to
    `project_root` -- the presence a committed binary needs to look like an
    intentional build artifact rather than an opaque smuggled blob."""
    directory = path.parent
    while True:
        if any((directory / name).is_file() for name in _BUILD_RECIPE_NAMES):
            return True
        if directory == project_root or directory == directory.parent:
            return False
        directory = directory.parent


# frob:enforces SC-DETECTION-OPAQUE-BINARY-ARTIFACT
# frob:enforces CHK-GATE-VET010
# frob:tests tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact.test_tracked_so_without_recipe_flagged
def _opaque_binary_artifact_violations(project_root: Path) -> list[Violation]:
    """VET010: a tracked binary blob (.whl/.so/.node/.wasm and similar)
    committed directly into source control with no accompanying build
    recipe nearby -- a structural property of the tracked file tree."""
    violations: list[Violation] = []
    for path in iter_files(project_root):
        if path.suffix not in _BINARY_ARTIFACT_SUFFIXES:
            continue
        if _has_nearby_build_recipe(path, project_root):
            continue
        violations.append(
            Violation(
                rule="VET010",
                severity=Severity.WARN,
                file=str(path),
                line=0,
                message=(
                    f"{path.name}: tracked binary artifact with no build "
                    f"recipe (Cargo.toml/CMakeLists.txt/setup.py/Makefile) "
                    f"nearby -- opaque provenance"
                ),
            )
        )
    return violations


# frob:doc docs/modules/vet.md#public-api
# frob:tests tests/test_vet.py::TestSupplyChainUnpinnedDependencies.test_pyproject_caret_range_flagged
def supply_chain_tree_violations(project_root: Path) -> list[Violation]:
    """VET007-VET010: the four project-tree-wide, once-per-scan supply-chain
    structural checks folded into `scan_tree` (docs/modules/vet.md
    "Mechanics")."""
    violations: list[Violation] = []
    violations.extend(_unpinned_dependency_violations(project_root))
    violations.extend(_python_install_artifact_violations(project_root))
    violations.extend(_unpinned_ci_action_violations(project_root))
    violations.extend(_opaque_binary_artifact_violations(project_root))
    return violations


__all__ = ["supply_chain_tree_violations"]
