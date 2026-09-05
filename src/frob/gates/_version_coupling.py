"""VERSION001: `frob`'s own version, EVERY pin naming `frob-core`/
`strata-core` anywhere in root `pyproject.toml` (`[project].dependencies`,
every extra under `[project.optional-dependencies]`, and any
`[dependency-groups]` table -- not just the `native` extra), plus
`frob-core/pyproject.toml`'s and `strata-core/pyproject.toml`'s own
`version` fields, must all be the exact SAME string, and every such pin
must be exact (`==`), never `>=`/`~=`/unpinned (T-3011, widened T-3903).

T-3903: this gate originally read the `native` extra BY NAME. T-3845 added
a second pin site -- `frob-core`/`strata-core` also landed in `[project].
dependencies` -- and the by-name gate did not see it: a version bump could
have shipped frob 0.531.0 hard-depending on frob-core==0.530.0, a package
that cannot resolve, with every gate green. Enumerating pin sites by name
is exactly the mistake that produced the gap, so this gate now enumerates
by TABLE SHAPE (any list of dependency-specifier strings reachable from
`[project].dependencies`, `[project.optional-dependencies].*`, or
`[dependency-groups].*`) and matches entries by PACKAGE NAME
(`frob-core`/`strata-core`) wherever they appear, so the next new pin site
is covered automatically instead of needing another hardcoded line.

Root cause this closes: three separately published artifacts (`frob`,
`frob-core`, `strata-core`) is three chances to skew, and this repo already
has the problem in miniature -- T-2884 had to add a git-SHA check to a
daemon BECAUSE VERSION STRINGS ALONE WERE NOT SUFFICIENT to detect skew
between two things that are supposed to move together. A native PyO3/abi3
extension is even less forgiving than that daemon case: a Python-side
change that assumes a new Rust-side field/behavior, installed against an
OLDER (or newer, mismatched) compiled `frob_core`/`strata_core`, does not
raise ImportError -- it silently returns wrong answers or drops fields the
Rust side has no code path for. A loose pin (`>=0.5`) would let pip resolve
ANY compatible-by-number-only version at install time, defeating the
lockstep-cut discipline entirely. `==` on all three, all matching frob's
own version, cut together at every release, is the only shape a gate can
mechanically enforce rather than merely recommend -- see
`docs/guides/release.md#version-coupling-t-3011` for the full reasoning
(including why an sdist-fallback alternative was rejected).

Read-only, filesystem-based (three `pyproject.toml` files under `root`),
matching every other gate module's `root: Path -> tuple[Violation, ...]`
shape -- no native extension import required, so this gate itself works
identically whether or not `frob_core`/`strata_core` are installed.
"""

# frob:ticket T-3011

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: The three files VERSION001 reads. (root-relative, POSIX-style)
_ROOT_PYPROJECT = "pyproject.toml"
_FROB_CORE_PYPROJECT = "frob-core/pyproject.toml"
_STRATA_CORE_PYPROJECT = "strata-core/pyproject.toml"


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load: `None` on any read/parse failure rather than
    raising, so one missing/malformed file reports as a named violation
    instead of aborting the whole gate (EXHAUST001/EXHAUST002 posture,
    matching every other filesystem-reading gate in this package)."""
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.debug("version_coupling_gate: could not read %s: %s", path, exc)
        return None


def _pin_sites(root_doc: dict) -> list[tuple[str, list]]:
    """Every list of PEP 508 dependency-specifier strings reachable from
    root `pyproject.toml` that could carry a pin naming a sibling crate:
    `[project].dependencies`, each extra under `[project.optional-
    dependencies]`, and each group under `[dependency-groups]` (T-3903) --
    enumerated by TABLE SHAPE, so a newly added pin site (another extra, a
    new dependency group, `[project].dependencies` itself) is covered the
    moment it exists, with no per-site name to remember to add."""
    sites: list[tuple[str, list]] = []
    project = root_doc.get("project", {})
    dependencies = project.get("dependencies")
    if isinstance(dependencies, list):
        sites.append(("project.dependencies", dependencies))
    extras = project.get("optional-dependencies", {})
    if isinstance(extras, dict):
        for extra_name, specs in extras.items():
            if isinstance(specs, list):
                sites.append((f"optional-dependencies.{extra_name}", specs))
    groups = root_doc.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_name, specs in groups.items():
            if isinstance(specs, list):
                sites.append((f"dependency-groups.{group_name}", specs))
    return sites


def _pin_in_specs(specs: list, dep_name: str) -> str | None:
    """The raw dependency-specifier string inside `specs` (one pin site's
    list) that names `dep_name`, or `None` if `dep_name` does not appear
    there at all -- matches by PACKAGE NAME, not by which site it is
    (T-3903), so the same rule catches an exact pin, a loose pin, or a
    bare unpinned entry wherever it is written."""
    for spec in specs:
        if not isinstance(spec, str):
            continue
        if spec == dep_name or spec.startswith(f"{dep_name}=="):
            return spec
        if spec.startswith(dep_name) and spec[len(dep_name) : len(dep_name) + 1] in (
            ">",
            "<",
            "~",
            "!",
        ):
            return spec
    return None


# frob:enforces CHK-GATE-VERSION001
def _version001_violation(message: str, site: str = "project") -> Violation:
    """The VERSION001 `Violation` for one detected skew/shape problem at
    `site` (a `pyproject.toml`-relative table path, e.g. `project.
    dependencies` or `optional-dependencies.native` -- T-3903 widened this
    from a single hardcoded site to whichever site the problem was found
    in)."""
    _log.warning("VERSION001: %s", message)
    return Violation(
        rule="VERSION001",
        severity=Severity.ERROR,
        file=_ROOT_PYPROJECT,
        line=0,
        symref=f"pyproject.toml::{site}",
        message=f"VERSION001: {message}",
    )


def _crate_pin_violations(
    root_doc: dict, frob_version: str, dep_name: str
) -> tuple[list[Violation], bool]:
    """VERSION001's pin-shape checks for ONE crate (`dep_name`) across
    EVERY pin site in root `pyproject.toml` (T-3903) -- not just the
    `native` extra. Returns `(violations, found_any)`; `found_any` is
    `False` only if `dep_name` appears in none of `_pin_sites` at all, so
    the caller can tell "no pin anywhere" (skip the crate-version check,
    there is nothing to have cut together) apart from "every pin found was
    fine"."""
    violations: list[Violation] = []
    found_any = False
    for site, specs in _pin_sites(root_doc):
        pin = _pin_in_specs(specs, dep_name)
        if pin is None:
            continue
        found_any = True
        if not pin.startswith(f"{dep_name}=="):
            violations.append(
                _version001_violation(
                    f"{pin!r} in [{site}] is not an exact (==) pin -- a "
                    f"loose pin on an ABI-coupled native extension produces "
                    f"bug reports nobody can reproduce; expected "
                    f"'{dep_name}=={frob_version}'",
                    site,
                )
            )
            continue
        pinned_version = pin.split("==", 1)[1]
        if pinned_version != frob_version:
            violations.append(
                _version001_violation(
                    f"{dep_name} is pinned to {pinned_version!r} in "
                    f"[{site}] but frob itself is {frob_version!r} -- "
                    f"every pin naming a sibling crate is cut together",
                    site,
                )
            )
    return violations, found_any


def _crate_violations(
    root: Path, root_doc: dict, frob_version: str, dep_name: str, crate_pyproject: str
) -> list[Violation]:
    """VERSION001 checks for ONE crate (`dep_name`): every exact-pin entry
    naming it anywhere in root `pyproject.toml` (T-3903, not just the
    `native` extra), and its own `pyproject.toml`'s `version` field,
    against `frob_version` -- split out of `version_coupling_gate` to keep
    that function under ARCH001's line threshold, one call per crate."""
    violations, found_any = _crate_pin_violations(root_doc, frob_version, dep_name)
    if not found_any:
        violations.append(
            _version001_violation(
                f"no exact pin for {dep_name} found anywhere in "
                f"{_ROOT_PYPROJECT} (checked [project].dependencies, every "
                f"[project.optional-dependencies] extra, and every "
                f"[dependency-groups] group; expected "
                f"'{dep_name}=={frob_version}' in at least one)"
            )
        )
        return violations

    crate_doc = _read_toml(root / crate_pyproject)
    if crate_doc is None:
        violations.append(
            _version001_violation(f"could not read/parse {crate_pyproject}")
        )
        return violations
    crate_version = crate_doc.get("project", {}).get("version")
    if crate_version != frob_version:
        violations.append(
            _version001_violation(
                f"{crate_pyproject} declares version {crate_version!r} but "
                f"frob itself is {frob_version!r} -- all three are cut "
                f"together"
            )
        )
    return violations


# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/guides/release.md#version-coupling-t-3011, whose own SCOPE002/ AFFECT001 \
# doc-closure (that large shared file's OTHER anchors describe \
# scripts/artifact_smoke.py, scripts/verify_release_ci_status.py, and \
# src/frob/doctor.py -- each pulling in ITS OWN further doc/test closure) is out of \
# proportion to pull into T-3903's narrow pin-matching-fix scope; same doc-anchor \
# scope-closure tension src/frob/gates/_rule_id_ scan.py's \
# SCANNED_BASES/RETIRED_RULE_IDS waivers already document (T-1010/T-1937) -- this \
# function's own docstring (widened by T-3903) is the authoritative description; a \
# follow-up can widen scope deliberately to add a frob:doc anchor back"
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_matched_versions_clean  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_skewed_core_version_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_loose_pin_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_missing_extra_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_mismatched_extra_pin_fires  # noqa: E501
# frob:tests \
# tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_skewed_defaul\
# t_dependency_pin_fires
# frob:tests \
# tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_loose_default\
# _dependency_pin_fires
# frob:tests \
# tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_pin_in_new_ex\
# tra_fires
def version_coupling_gate(root: Path) -> tuple[Violation, ...]:
    """VERSION001: frob's own version, EVERY pin naming `frob-core`/
    `strata-core` anywhere in root `pyproject.toml` (T-3903: `[project].
    dependencies`, every `[project.optional-dependencies]` extra, and any
    `[dependency-groups]` group -- not just the `native` extra), and those
    two crates' own `pyproject.toml` `version` fields must all match
    exactly, and every such pin must be exact-equality (`==`), never a
    range. Module docstring for the full incident reasoning; never raises
    -- every failure mode (missing file, unreadable TOML, no pin found
    anywhere, loose pin, mismatched version) is a named Violation, not an
    exception."""
    root = Path(root)

    root_doc = _read_toml(root / _ROOT_PYPROJECT)
    if root_doc is None:
        return (_version001_violation(f"could not read/parse {_ROOT_PYPROJECT}"),)
    frob_version = root_doc.get("project", {}).get("version")
    if not frob_version:
        return (_version001_violation(f"{_ROOT_PYPROJECT} has no [project].version"),)

    violations: list[Violation] = []
    for dep_name, crate_pyproject in (
        ("frob-core", _FROB_CORE_PYPROJECT),
        ("strata-core", _STRATA_CORE_PYPROJECT),
    ):
        violations.extend(
            _crate_violations(root, root_doc, frob_version, dep_name, crate_pyproject)
        )

    _log.info(
        "version_coupling_gate: frob=%s, %d violation(s)",
        frob_version,
        len(violations),
    )
    return tuple(violations)


__all__ = ["version_coupling_gate"]
