"""Invariant loading (docs/modules/gates.md's Invariants section).

An invariant is a tracked statement (`invariants/INV-###.md`, YAML
frontmatter over markdown prose) whose truth must have standing evidence --
a collected test node id or a loaded policy rule id. Loading is pure
schema validation over the frontmatter block; INV001/INV002 (evidence and
code-anchor closure) live in `frob.gates` proper since they must join
against `CollectedTests` and the `GraphSnapshot`.
"""

# frob:waive TEST005 reason="module line coverage 78.3%, debt T-0160"

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

_log = get_logger(__name__)

_ID_RE = re.compile(r"^INV-\d{3}$")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


# frob:doc docs/modules/gates.md#invariants
class Criticality(StrEnum):
    """How severe a broken invariant would be."""

    HIGH = "high"
    MEDIUM = "medium"


_CRITICALITY_VALUES = frozenset(c.value for c in Criticality)


# frob:doc docs/modules/gates.md#invariants
class Invariant(BaseModel):
    """One tracked invariant: id, statement, criticality, and its evidence list."""

    model_config = ConfigDict(frozen=True)

    id: str
    statement: str
    criticality: Criticality
    evidence: tuple[str, ...] = ()
    path: str = ""


# frob:doc docs/modules/gates.md#invariants
class InvariantError(ErrorSet):
    """Failure values `load_invariants` can return."""

    Malformed = "Invariant file failed schema validation"
    DuplicateId = "Two invariant files share an id"


def _invariants_dir(root: Path) -> Path:
    """The `invariants/` directory under `root`."""
    return root / "invariants"


def _frontmatter_dict(path: Path) -> Result[dict, InvariantError]:
    """Read `path` and parse its YAML frontmatter block into a mapping."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("load_invariants: could not read %s: %s", path, exc)
        return Err(InvariantError.Malformed)

    match = _FRONTMATTER_RE.match(text)
    if match is None:
        _log.warning("load_invariants: %s has no YAML frontmatter block", path)
        return Err(InvariantError.Malformed)

    try:
        raw = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        _log.warning("load_invariants: %s frontmatter is bad YAML: %s", path, exc)
        return Err(InvariantError.Malformed)

    if not isinstance(raw, dict):
        _log.warning("load_invariants: %s frontmatter is not a mapping", path)
        return Err(InvariantError.Malformed)
    return Ok(raw)


def _build_invariant(
    raw: dict, path: Path, root: Path
) -> Result[Invariant, InvariantError]:
    """Validate a parsed frontmatter mapping into an `Invariant`."""
    evidence = raw.get("evidence") or []
    if not isinstance(evidence, list):
        _log.warning("load_invariants: %s evidence is not a list", path)
        return Err(InvariantError.Malformed)

    raw_criticality = str(raw.get("criticality", ""))
    if raw_criticality not in _CRITICALITY_VALUES:
        _log.warning(
            "load_invariants: %s has bad criticality %r", path, raw_criticality
        )
        return Err(InvariantError.Malformed)

    try:
        invariant = Invariant(
            id=str(raw.get("id", "")),
            statement=str(raw.get("statement", "")),
            criticality=Criticality(raw_criticality),
            evidence=tuple(str(item) for item in evidence),
            path=str(path.relative_to(root).as_posix()),
        )
    except ValidationError as exc:
        _log.warning("load_invariants: %s failed validation: %s", path, exc)
        return Err(InvariantError.Malformed)

    if _ID_RE.match(invariant.id) is None:
        _log.warning("load_invariants: %s has bad id %r", path, invariant.id)
        return Err(InvariantError.Malformed)
    if not invariant.statement:
        _log.warning("load_invariants: %s has empty statement", path)
        return Err(InvariantError.Malformed)
    return Ok(invariant)


def _parse_one(path: Path, root: Path) -> Result[Invariant, InvariantError]:
    """Parse one `invariants/INV-###.md` file's YAML frontmatter."""
    raw = _frontmatter_dict(path)
    if raw.is_err:
        return Err(raw.danger_err)
    return _build_invariant(raw.danger_ok, path, root)


# frob:doc docs/modules/gates.md#public-api
def load_invariants(root: Path) -> Result[tuple[Invariant, ...], InvariantError]:
    """Parse every `invariants/INV-###.md` under `root`; a missing dir is `Ok(())`."""
    directory = _invariants_dir(root)
    if not directory.is_dir():
        _log.info("load_invariants: no invariants/ under %s", root)
        return Ok(())

    invariants: dict[str, Invariant] = {}
    inv_paths = sorted(directory.glob("*.md"))
    for path in inv_paths:
        parsed = _parse_one(path, root)
        if parsed.is_err:
            return Err(parsed.danger_err)
        invariant = parsed.danger_ok
        if invariant.id in invariants:
            _log.error("load_invariants: duplicate id %s (%s)", invariant.id, path)
            return Err(InvariantError.DuplicateId)
        invariants[invariant.id] = invariant

    _log.info(
        "load_invariants: loaded %d invariant(s) from %s", len(invariants), directory
    )
    return Ok(tuple(invariants.values()))


__all__ = ["Criticality", "Invariant", "InvariantError", "load_invariants"]
