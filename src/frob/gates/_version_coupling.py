"""VERSION001: `frob`'s own version, its `frob-core` extra pin, and its
`strata-core` extra pin, plus `frob-core/pyproject.toml`'s and
`strata-core/pyproject.toml`'s own `version` fields, must all be the exact
SAME string, and the two extra pins must be exact (`==`), never `>=`/`~=`/
unpinned (T-3011).

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


def _extra_pin(root_doc: dict, dep_name: str) -> str | None:
    """The raw dependency-specifier string frob's own `pyproject.toml`
    pins `dep_name` to inside `[project.optional-dependencies].native`, or
    `None` if that extra or entry is missing entirely."""
    extras = root_doc.get("project", {}).get("optional-dependencies", {})
    native = extras.get("native", [])
    for spec in native:
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
def _version001_violation(message: str) -> Violation:
    """The VERSION001 `Violation` for one detected skew/shape problem."""
    _log.warning("VERSION001: %s", message)
    return Violation(
        rule="VERSION001",
        severity=Severity.ERROR,
        file=_ROOT_PYPROJECT,
        line=0,
        symref="pyproject.toml::optional-dependencies.native",
        message=f"VERSION001: {message}",
    )


def _crate_violations(
    root: Path, root_doc: dict, frob_version: str, dep_name: str, crate_pyproject: str
) -> list[Violation]:
    """VERSION001 checks for ONE crate (`dep_name`): its exact-pin entry in
    frob's own `native` extra, and its own `pyproject.toml`'s `version`
    field, both against `frob_version` -- split out of `version_coupling_
    gate` to keep that function under ARCH001's line threshold, one call
    per crate."""
    violations: list[Violation] = []
    pin = _extra_pin(root_doc, dep_name)
    if pin is None:
        violations.append(
            _version001_violation(
                f"[project.optional-dependencies].native has no exact pin "
                f"for {dep_name} (expected '{dep_name}=={frob_version}')"
            )
        )
        return violations
    if not pin.startswith(f"{dep_name}=="):
        violations.append(
            _version001_violation(
                f"{pin!r} is not an exact (==) pin -- a loose pin on an "
                f"ABI-coupled native extension produces bug reports nobody "
                f"can reproduce; expected '{dep_name}=={frob_version}'"
            )
        )
        return violations
    pinned_version = pin.split("==", 1)[1]
    if pinned_version != frob_version:
        violations.append(
            _version001_violation(
                f"{dep_name} is pinned to {pinned_version!r} in the native "
                f"extra but frob itself is {frob_version!r} -- all three "
                f"are cut together"
            )
        )

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


# frob:doc docs/guides/release.md#version-coupling-t-3011
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_matched_versions_clean  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_skewed_core_version_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_loose_pin_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_missing_extra_fires  # noqa: E501
# frob:tests tests/unit/gates/test_version_coupling.py::TestVersionCouplingGate.test_mismatched_extra_pin_fires  # noqa: E501
def version_coupling_gate(root: Path) -> tuple[Violation, ...]:
    """VERSION001: frob's own version, its `frob[native]` extra's exact
    pins on `frob-core`/`strata-core`, and those two crates' own
    `pyproject.toml` `version` fields must all match exactly, and the
    extra's pins must be exact-equality (`==`) specifiers, never a range.
    Module docstring for the full incident reasoning; never raises --
    every failure mode (missing file, unreadable TOML, missing extra,
    missing entry, loose pin, mismatched version) is a named Violation,
    not an exception."""
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
