"""Project-tree-wide supply-chain structural checks (T-1088).

Unlike `_ecosystem.py` (per-DEPENDENCY-source cheap rules run against a
located package's local copy), the four detectors here run once per
`scan_tree` call against the SCANNED PROJECT'S OWN tracked files -- its
manifests, CI workflows, and tracked binary blobs are purely structural
properties of text/tree-shape frob already has on disk, no fetch, no
registry metadata, same "statically-detectable" class docs/design/
registry/supply-chain.yaml tags them with.

T-2469: the four manifest-reading detectors (`_pyproject_unpinned_
violations`/`_package_json_unpinned_violations`/`_cargo_toml_unpinned_
violations`/`_python_install_artifact_violations`/`_unpinned_ci_action_
violations`) used to decide from `re.search`/`re.match` over each
manifest's raw TEXT and build a symref-less `Violation` -- T-2466's
LEXCHECK001 widening (`DETECTOR_PACKAGE_ROOTS` past `src/frob/gates/**`
alone) correctly caught this as the SAME "parse, don't grep" defect
class this repo already enforces elsewhere. Every one of these manifest
formats already has a real parser available (`tomllib`/`json` in the
stdlib, `packaging.requirements.Requirement` for a PEP 508 dependency
string, `ast` for setup.py's own Python source, `configparser` for
setup.cfg's declarative-config INI shape, `yaml` -- already a project
dependency -- for a GitHub Actions workflow document), so the root fix
is switching each detector to its real parser rather than adding a
`symref=` allowlist entry: a regex over an already-structurally-parsed
VALUE (e.g. splitting `"lodash": "*"`'s value into a bare string) is
not the lexical-decision shape LEXCHECK001 exists to catch (nothing is
decided FROM the regex any more, `json`/`tomllib` already decided the
shape), and this file no longer imports `re` at all.
"""

from __future__ import annotations

import ast
import configparser
import json
import tomllib
from pathlib import Path

import yaml
from packaging.requirements import InvalidRequirement, Requirement

from frob.excludes import iter_files
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

# Version specs that are NOT an exact pin: caret/tilde ranges, wildcards,
# comparison operators, and the bare npm/cargo "*" catch-all.
_UNPINNED_MARKERS = ("^", "~", "*", ">", "<", "x", "X")


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
    """VET007 half: parse `pyproject.toml`'s `dependencies = [...]` array
    (bare top-level, or PEP 621's `[project]` table -- both shapes are
    checked) via `tomllib`, then each PEP 508 requirement string via
    `packaging.requirements.Requirement`, for specs with no exact pin."""
    violations: list[Violation] = []
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        return violations
    try:
        data = tomllib.loads(_read_text_or_empty(pyproject))
    except tomllib.TOMLDecodeError as exc:
        _log.warning("vet: %s is not valid TOML: %s", pyproject, exc)
        return violations
    deps = data.get("dependencies") or data.get("project", {}).get("dependencies") or []
    if not isinstance(deps, list):
        return violations
    for entry in deps:
        if not isinstance(entry, str):
            continue
        try:
            req = Requirement(entry)
        except InvalidRequirement:
            continue
        if _is_unpinned_spec(str(req.specifier)):
            violations.append(
                Violation(
                    rule="VET007",
                    severity=Severity.WARN,
                    file=str(pyproject),
                    line=0,
                    message=(
                        f"{req.name}: unpinned dependency spec {entry!r} "
                        f"in pyproject.toml"
                    ),
                )
            )
    return violations


def _package_json_unpinned_violations(project_root: Path) -> list[Violation]:
    """VET007 half: parse `package.json` (real JSON) for a
    dependencies/devDependencies entry with no exact pin."""
    violations: list[Violation] = []
    package_json = project_root / "package.json"
    if not package_json.is_file():
        return violations
    try:
        data = json.loads(_read_text_or_empty(package_json))
    except json.JSONDecodeError as exc:
        _log.warning("vet: %s is not valid JSON: %s", package_json, exc)
        return violations
    if not isinstance(data, dict):
        return violations
    for section in ("dependencies", "devDependencies"):
        deps = data.get(section)
        if not isinstance(deps, dict):
            continue
        for name, spec in deps.items():
            if not isinstance(spec, str):
                continue
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
    """VET007 half: parse `Cargo.toml`'s `[dependencies]` table (real
    TOML) for a spec (bare version string, or an inline table's own
    `version=`) with no exact pin."""
    violations: list[Violation] = []
    cargo_toml = project_root / "Cargo.toml"
    if not cargo_toml.is_file():
        return violations
    try:
        data = tomllib.loads(_read_text_or_empty(cargo_toml))
    except tomllib.TOMLDecodeError as exc:
        _log.warning("vet: %s is not valid TOML: %s", cargo_toml, exc)
        return violations
    deps = data.get("dependencies", {})
    if not isinstance(deps, dict):
        return violations
    for name, value in deps.items():
        if isinstance(value, str):
            spec = value
        elif isinstance(value, dict):
            spec = value.get("version", "")
            if not isinstance(spec, str):
                continue
        else:
            continue
        if _is_unpinned_spec(spec):
            violations.append(
                Violation(
                    rule="VET007",
                    severity=Severity.WARN,
                    file=str(cargo_toml),
                    line=0,
                    message=(
                        f"{name}: unpinned dependency spec {spec!r} in Cargo.toml"
                    ),
                )
            )
    return violations


# frob:enforces SC-ATTACK-UNPINNED-DEPENDENCIES
# frob:enforces CHK-GATE-VET007
# frob:tests \
# tests/test_vet.py::TestSupplyChainUnpinnedDependencies.test_pyproject_caret_range_fla\
# gged
def _unpinned_dependency_violations(project_root: Path) -> list[Violation]:
    """VET007: a manifest (pyproject.toml/package.json/Cargo.toml) dependency
    spec with no exact pin -- a purely structural property of the manifest
    text, independent of any lockfile resolution."""
    return [
        *_pyproject_unpinned_violations(project_root),
        *_package_json_unpinned_violations(project_root),
        *_cargo_toml_unpinned_violations(project_root),
    ]


def _setup_py_data_files_dests(text: str) -> list[str]:
    """Every destination string literal from a `setup(...)`/`setuptools.
    setup(...)` call's `data_files=` keyword argument, via a real `ast`
    parse of `text` (T-2469) -- no text regex over Python source. A
    `data_files` entry is `(dest, [files])`; only the first (destination)
    element of each 2-tuple/list is collected. A syntax error (or any
    shape this walk cannot resolve to a literal string) yields nothing
    rather than raising -- same fail-open posture the previous regex-
    based scan had for unmatched text."""
    dests: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return dests
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "setup":
            continue
        for kw in node.keywords:
            if kw.arg != "data_files" or not isinstance(kw.value, ast.List):
                continue
            for entry in kw.value.elts:
                dest_node = None
                if isinstance(entry, (ast.Tuple, ast.List)) and entry.elts:
                    dest_node = entry.elts[0]
                if isinstance(dest_node, ast.Constant) and isinstance(
                    dest_node.value, str
                ):
                    dests.append(dest_node.value)
    return dests


def _setup_cfg_data_files_dests(text: str) -> list[str]:
    """Every destination key under setuptools' declarative `[options.
    data_files]` INI section (T-2469), via a real `configparser` parse of
    `text` -- no text regex. A malformed/unparseable `setup.cfg` yields
    nothing rather than raising."""
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text)
    except configparser.Error as exc:
        _log.warning("vet: setup.cfg is not valid INI: %s", exc)
        return []
    if not parser.has_section("options.data_files"):
        return []
    return list(parser["options.data_files"])


def _is_escaping_data_files_dest(dest: str) -> bool:
    """Whether `dest` is absolute or escapes the package via a leading
    `../` traversal -- the same two shapes the previous regex-based scan
    flagged, expressed as plain string prefix checks (no regex needed:
    the value is already an exact string, extracted by a real parser)."""
    return dest.startswith("/") or dest.startswith("../")


# frob:enforces SC-DETECTION-PYTHON-INSTALL-ARTIFACTS
# frob:enforces CHK-GATE-VET008
# frob:tests \
# tests/test_vet.py::TestSupplyChainInstallArtifacts.test_setup_py_absolute_data_files_\
# flagged
def _python_install_artifact_violations(project_root: Path) -> list[Violation]:
    """VET008: setup.py/setup.cfg `data_files` writing to an absolute path or
    escaping the package via `../` traversal -- an installed artifact landing
    somewhere unexpected on the target filesystem."""
    violations: list[Violation] = []

    py_path = project_root / "setup.py"
    if py_path.is_file():
        text = _read_text_or_empty(py_path)
        if "data_files" in text:
            for dest in _setup_py_data_files_dests(text):
                if _is_escaping_data_files_dest(dest):
                    violations.append(
                        Violation(
                            rule="VET008",
                            severity=Severity.ERROR,
                            file=str(py_path),
                            line=0,
                            message=(
                                f"setup.py: data_files destination {dest!r} "
                                f"is absolute or escapes the package via "
                                f"'../' traversal (installed artifact lands "
                                f"outside the package)"
                            ),
                        )
                    )

    cfg_path = project_root / "setup.cfg"
    if cfg_path.is_file():
        text = _read_text_or_empty(cfg_path)
        if "data_files" in text:
            for dest in _setup_cfg_data_files_dests(text):
                if _is_escaping_data_files_dest(dest):
                    violations.append(
                        Violation(
                            rule="VET008",
                            severity=Severity.ERROR,
                            file=str(cfg_path),
                            line=0,
                            message=(
                                f"setup.cfg: data_files destination {dest!r} "
                                f"is absolute or escapes the package via "
                                f"'../' traversal (installed artifact lands "
                                f"outside the package)"
                            ),
                        )
                    )

    return violations


def _iter_workflow_uses_values(node: object) -> list[str]:
    """Every `uses:` string value anywhere in a parsed GitHub Actions
    workflow document (T-2469) -- a real recursive walk of the `yaml.
    safe_load`-parsed structure, covering a job step's `uses`, a
    composite action's own `runs.steps[].uses`, or any other nesting
    shape, not just the `jobs.*.steps[]` case a line-oriented regex would
    have to special-case. No text regex over the YAML source."""
    values: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                values.append(value)
            else:
                values.extend(_iter_workflow_uses_values(value))
    elif isinstance(node, list):
        for item in node:
            values.extend(_iter_workflow_uses_values(item))
    return values


_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _is_full_commit_sha(ref: str) -> bool:
    """Whether `ref` is a full 40-hex-character commit SHA (T-2469) --
    plain string checks, no regex."""
    return len(ref) == 40 and all(c in _HEX_DIGITS for c in ref)


# frob:enforces SC-DETECTION-UNPINNED-CI-ACTION
# frob:enforces CHK-GATE-VET009
# frob:tests \
# tests/test_vet.py::TestSupplyChainCiActionPin.test_workflow_branch_ref_flagged
def _unpinned_ci_action_violations(project_root: Path) -> list[Violation]:
    """VET009: a GitHub Actions `uses: owner/action@ref` where `ref` is a
    mutable branch/tag rather than a full 40-hex-char commit SHA -- a
    structural property of tracked `.github/workflows/*.yaml` text,
    decided from a real `yaml.safe_load` parse (T-2469), not a line
    regex."""
    violations: list[Violation] = []
    workflows_dir = project_root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return violations
    for path in sorted(workflows_dir.glob("*.y*ml")):
        text = _read_text_or_empty(path)
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            _log.warning("vet: %s is not valid YAML: %s", path, exc)
            continue
        for uses in _iter_workflow_uses_values(doc):
            if "@" not in uses:
                continue
            action, _, ref = uses.rpartition("@")
            if action.startswith("./"):
                continue  # local composite action, not a supply-chain edge
            if _is_full_commit_sha(ref):
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
# frob:tests \
# tests/test_vet.py::TestSupplyChainOpaqueBinaryArtifact.test_tracked_so_without_recipe\
# _flagged
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
# frob:tests \
# tests/test_vet.py::TestSupplyChainUnpinnedDependencies.test_pyproject_caret_range_fla\
# gged
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
