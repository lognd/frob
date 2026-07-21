"""Invariant loading (docs/modules/gates.md's Invariants section).

An invariant is a tracked statement (`invariants/INV-###.md`, YAML
frontmatter over markdown prose) whose truth must have standing evidence --
a collected test node id or a loaded policy rule id. Loading is pure
schema validation over the frontmatter block; INV001/INV002 (evidence and
code-anchor closure) live in `frob.gates` proper since they must join
against `CollectedTests` and the `GraphSnapshot`.
"""

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
# frob:ticket T-0462
# The exclusivity vocabulary INV003 (frob.gates.__init__) treats as a
# normative claim that needs a bound invariant: "only X", "sole"/"solely",
# "exclusively", "nothing else", "never...except", and "at most/exactly
# one" all assert a closed set or a single permitted case -- exactly the
# kind of claim that silently rots when the code it describes grows a
# second case and nothing catches it. Word-boundary patterns so "lonely"
# doesn't false-positive on "only", and `never...except` allows an
# unbounded span between the two words since real prose interleaves
# qualifiers ("never reads the file, except under --force").
EXCLUSIVITY_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bonly\b"),
    re.compile(r"\bsole(?:ly)?\b"),
    re.compile(r"\bexclusively\b"),
    re.compile(r"\bnothing else\b"),
    re.compile(r"\bnever\b.{0,120}?\bexcept\b", re.DOTALL),
    re.compile(r"\bat (?:most|exactly) one\b"),
)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0462
# frob:tests tests/test_gates.py::TestInv003Gate.test_exclusivity_claim_without_marker_warns kind="unit"  # noqa: E501
def find_exclusivity_claims(text: str) -> tuple[str, ...]:
    """Every distinct exclusivity phrase (`EXCLUSIVITY_CLAIM_PATTERNS`)
    matched anywhere in `text`, for INV003's normative-claim scan."""
    return tuple(
        pattern.pattern
        for pattern in EXCLUSIVITY_CLAIM_PATTERNS
        if pattern.search(text) is not None
    )


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
# The base normative-claim vocabulary INV004 (frob.gates.__init__) uses to
# decide whether a doc section "describes behavior" at all: must/must
# not/never/always/shall/guarantees/ensures/requires. Distinct from
# EXCLUSIVITY_CLAIM_PATTERNS above (which flags a specific closed-set
# claim needing ITS OWN bound invariant, INV003) -- this is the broader,
# coarser signal INV004 uses for the inverse check: a section using ANY
# of this normative language but binding NO invariant at all is a likely
# under-specified region, not a specific unproven claim.
NORMATIVE_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmust\b"),
    re.compile(r"\bmust not\b"),
    re.compile(r"\bnever\b"),
    re.compile(r"\balways\b"),
    re.compile(r"\bshall\b"),
    re.compile(r"\bguarantees?\b"),
    re.compile(r"\bensures?\b"),
    re.compile(r"\brequires?\b"),
    *EXCLUSIVITY_CLAIM_PATTERNS,
)


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0452
# frob:tests tests/test_gates.py::TestInv004Gate.test_section_with_normative_language_and_no_invariant_is_advisory kind="unit"  # noqa: E501
def find_normative_claims(text: str) -> tuple[str, ...]:
    """Every distinct normative phrase (`NORMATIVE_CLAIM_PATTERNS`) matched
    anywhere in `text`, for INV004's section-density scan."""
    return tuple(
        pattern.pattern
        for pattern in NORMATIVE_CLAIM_PATTERNS
        if pattern.search(text) is not None
    )


# frob:doc docs/modules/gates.md#invariants
class _Criticality(StrEnum):
    """How severe a broken invariant would be."""

    HIGH = "high"
    MEDIUM = "medium"


_CRITICALITY_VALUES = frozenset(c.value for c in _Criticality)


# frob:doc docs/modules/gates.md#invariants
class Invariant(BaseModel):
    """One tracked invariant: id, statement, criticality, and its evidence list."""

    model_config = ConfigDict(frozen=True)

    id: str
    statement: str
    criticality: _Criticality
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


def _validate_invariant_shape(
    invariant: Invariant, path: Path
) -> Result[None, InvariantError]:
    """Post-construction checks `Invariant`'s own pydantic validation doesn't
    cover: id format, non-empty statement."""
    if _ID_RE.match(invariant.id) is None:
        _log.warning("load_invariants: %s has bad id %r", path, invariant.id)
        return Err(InvariantError.Malformed)
    if not invariant.statement:
        _log.warning("load_invariants: %s has empty statement", path)
        return Err(InvariantError.Malformed)
    return Ok(None)


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
            criticality=_Criticality(raw_criticality),
            evidence=tuple(str(item) for item in evidence),
            path=str(path.relative_to(root).as_posix()),
        )
    except ValidationError as exc:
        _log.warning("load_invariants: %s failed validation: %s", path, exc)
        return Err(InvariantError.Malformed)

    shape = _validate_invariant_shape(invariant, path)
    if shape.is_err:
        return Err(shape.danger_err)
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


__all__ = [
    "EXCLUSIVITY_CLAIM_PATTERNS",
    "NORMATIVE_CLAIM_PATTERNS",
    "Invariant",
    "InvariantError",
    "_Criticality",
    "find_exclusivity_claims",
    "find_normative_claims",
    "load_invariants",
]
