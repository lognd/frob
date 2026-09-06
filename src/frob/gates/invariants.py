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
from frob.yamlio import fast_yaml_loader

_log = get_logger(__name__)

# T-4019: widened from the original `^INV-\d{3}$` to match the id grammar
# the `frob:invariant` code-comment directive already accepts with NO
# format restriction of its own (`frob.graph.dsl`'s target parsing takes
# any bare token) -- a real, working example already lives in this repo:
# `# frob:invariant INV-RENDER-SOLE-STDOUT` (src/frob/gates/_render_lint.py).
# The old three-digit-only pattern rejected that shape outright, so a
# consumer's descriptive id (`INV-ADMIN-DATA-001`) failed this loader's
# validation while the very directive meant to anchor it accepted the
# same string -- one concept, two disagreeing spellings. This is the ONE
# shared definition now: "INV-" followed by one or more dash-separated
# all-caps/digit segments, covering both the original convention
# (INV-045) and a descriptive id (INV-ADMIN-DATA-001,
# INV-RENDER-SOLE-STDOUT) -- never silently permissive (lowercase, empty
# segments, and bare "INV-" still fail loudly, matching a directive's own
# de-facto shape: real ids are always dash-separated shouting-case
# tokens).
_ID_RE = re.compile(r"^INV-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
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
# frob:ticket T-0509
# T-0509 calibration: the bare-vocabulary scan (T-0462) fired on ~765
# warnings across docs/ -- mostly headings, table cells, code samples, and
# link text carrying the trigger word with no actual claim attached (e.g.
# a `## Schema` heading, or a `| only |` table cell). Two changes narrow
# this to a genuinely reviewable pool without dropping real claims:
# (1) `_strip_markdown_noise` removes fenced/inline code, link targets,
# and table rows before scanning -- code and tabular data are not prose
# assertions; (2) `_is_claim_shaped` requires a claim-verb
# (`_CLAIM_VERB_RE`) in the SAME sentence as the trigger word -- a
# subject-less fragment (a bare heading, a dangling noun phrase) cannot
# assert anything, so it is not a claim regardless of vocabulary.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n\s*\n")
_CLAIM_VERB_RE = re.compile(
    r"\b(?:is|are|was|were|must|never|always|can|could|cannot|can't|does|"
    r"do|did|has|have|had|will|would|should|shall|supports?|returns?|"
    r"produces?|writes?|reads?|calls?|creates?|deletes?|emits?|enforces?|"
    r"guarantees?|requires?|allows?|permits?|checks?|raises?|throws?|"
    r"fires?|holds?|stays?|remains?|runs?|treats?|resolves?|binds?)\b",
    re.IGNORECASE,
)


def _strip_markdown_noise(text: str) -> str:
    """Drop fenced/inline code, link targets, and table rows from `text`
    before claim-shape scanning (T-0509) -- these carry trigger vocabulary
    that is never a prose assertion (a code sample, a URL, a table cell)."""
    text = _FENCED_CODE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("|")]
    return "\n".join(lines)


def _is_claim_shaped(sentence: str) -> bool:
    """T-0509: a genuine normative/exclusivity claim needs a claim-verb
    (`_CLAIM_VERB_RE`) in the SAME sentence as the trigger word -- a
    heading, a bare noun phrase, or a table fragment has no verb and
    asserts nothing, regardless of which trigger word it contains."""
    return _CLAIM_VERB_RE.search(sentence) is not None


def _claim_shaped_sentences(text: str) -> tuple[str, ...]:
    """`text`, noise-stripped (`_strip_markdown_noise`) and split into
    sentences, filtered to only the claim-shaped ones (`_is_claim_shaped`)
    -- the shared preprocessing both `find_exclusivity_claims` and
    `find_normative_claims` scan over."""
    clean = _strip_markdown_noise(text)
    return tuple(s for s in _SENTENCE_SPLIT_RE.split(clean) if _is_claim_shaped(s))


# frob:doc docs/modules/gates.md#invariants
# frob:ticket T-0462
# frob:tests tests/gates_suite/test_invariant.py::TestInv003Gate.test_exclusivity_claim_without_marker_warns kind="unit"  # noqa: E501
def find_exclusivity_claims(text: str) -> tuple[str, ...]:
    """Every distinct exclusivity phrase (`EXCLUSIVITY_CLAIM_PATTERNS`)
    matched in a claim-shaped sentence of `text` (T-0509: noise-stripped,
    verb-bearing), for INV003's normative-claim scan."""
    sentences = _claim_shaped_sentences(text)
    return tuple(
        pattern.pattern
        for pattern in EXCLUSIVITY_CLAIM_PATTERNS
        if any(pattern.search(s) is not None for s in sentences)
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
# frob:tests tests/gates_suite/test_invariant.py::TestInv004Gate.test_section_with_normative_language_and_no_invariant_is_advisory kind="unit"  # noqa: E501
def find_normative_claims(text: str) -> tuple[str, ...]:
    """Every distinct normative phrase (`NORMATIVE_CLAIM_PATTERNS`) matched
    in a claim-shaped sentence of `text` (T-0509: noise-stripped,
    verb-bearing), for INV004's section-density scan."""
    sentences = _claim_shaped_sentences(text)
    return tuple(
        pattern.pattern
        for pattern in NORMATIVE_CLAIM_PATTERNS
        if any(pattern.search(s) is not None for s in sentences)
    )


# frob:doc docs/modules/gates.md#invariants
# frob:waive COV007 reason="docs/modules/gates.md's Invariants section individually \
# frob:describes this private enum by name (T-0529) -- a deliberate architecture doc, \
# not accidental drift onto a private helper"
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
    """Per-file failure values `load_invariants` can attach to one
    `InvariantLoadError` (T-4019: no longer the whole load's own Err --
    see that class's docstring)."""

    Malformed = "Invariant file failed schema validation"
    DuplicateId = "Two invariant files share an id"


# frob:doc docs/modules/gates.md#invariants
# frob:tests \
# tests/gates_suite/test_invariant.py::TestInvariantLoad.test_malformed_bad_id \
# kind="unit"
class InvariantLoadError(BaseModel):
    """One `invariants/*.md` file that failed to load: its path (relative
    to root) and why (T-4019). `load_invariants` emits one of these PER
    bad file instead of aborting -- a malformed file must be loud (it
    always produces one of these, never silently dropped) and local (it
    never keeps any OTHER file from loading), the fix for the "one bad
    file turns off every gate" defect."""

    model_config = ConfigDict(frozen=True)

    path: str
    error: InvariantError


# frob:doc docs/modules/gates.md#invariants
# frob:tests \
# tests/gates_suite/test_invariant.py::TestInvariantLoad.test_one_malformed_file_does_n\
# ot_block_others kind="unit"
class LoadedInvariants(BaseModel):
    """`load_invariants`'s result (T-4019): every invariant that parsed
    cleanly, plus one `InvariantLoadError` for every file that didn't.
    Scanning `invariants/` for files it exists to read can't meaningfully
    fail as a whole (a missing directory is simply zero files) -- the
    only failure unit that exists is a single file, so `load_invariants`
    returns this directly rather than wrapping it in `Result`: there is
    no longer a whole-load failure case left to represent."""

    model_config = ConfigDict(frozen=True)

    invariants: tuple[Invariant, ...] = ()
    errors: tuple[InvariantLoadError, ...] = ()


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
        raw = yaml.load(match.group(1), Loader=fast_yaml_loader()) or {}
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


# frob:waive AFFECT001 reason="T-4019: docs/modules/gates.md's Invariants section was \
# already rewritten in this same change for load_invariants' new LoadedInvariants \
# return shape; the frob ack write that clears the DRIFT001 digest stamp needs \
# frob.lock, which is under a concurrent T-3799 (unrelated Windows PATHEXT work) scope \
# lease this ticket cannot take -- content is current, only the ack bookkeeping is \
# blocked, same T-2466 precedent frob/tickets/_evidence.py already carries for this \
# exact lease-contention shape"
# frob:waive DRIFT001 reason="same T-3799 frob.lock lease conflict as the AFFECT001 \
# waiver immediately above -- docs/modules/gates.md is already re-verified accurate \
# for this change, the ack write alone is blocked"
# frob:doc docs/modules/gates.md#public-api
def load_invariants(root: Path) -> LoadedInvariants:
    """Parse every `invariants/*.md` under `root`; a missing dir loads zero
    invariants and zero errors.

    T-4019: ONE malformed file used to abort the ENTIRE load
    (`Err(InvariantError...)` on the first bad file, `frob.gates`'
    `_load_required_state` then treating that as a hard failure that
    turned off every OTHER gate too) and, further up the stack, that hard
    failure rendered as `exit_code=0` "gates skipped ... pass" -- the
    largest-blast-radius silent zero this repo has measured. Scoped now:
    every file is parsed independently, a bad one becomes its own
    `InvariantLoadError` (naming its path) in `errors`, and every OTHER
    file's invariant still loads into `invariants` normally. A duplicate
    id is likewise scoped to the SECOND file that declares it -- the
    first file's invariant is kept, the duplicate becomes an
    `InvariantLoadError` naming the losing path, and every unrelated file
    is unaffected either way."""
    directory = _invariants_dir(root)
    if not directory.is_dir():
        _log.info("load_invariants: no invariants/ under %s", root)
        return LoadedInvariants()

    invariants: dict[str, Invariant] = {}
    errors: list[InvariantLoadError] = []
    inv_paths = sorted(directory.glob("*.md"))
    for path in inv_paths:
        rel_path = str(path.relative_to(root).as_posix())
        parsed = _parse_one(path, root)
        if parsed.is_err:
            errors.append(InvariantLoadError(path=rel_path, error=parsed.danger_err))
            continue
        invariant = parsed.danger_ok
        if invariant.id in invariants:
            _log.error("load_invariants: duplicate id %s (%s)", invariant.id, path)
            errors.append(
                InvariantLoadError(path=rel_path, error=InvariantError.DuplicateId)
            )
            continue
        invariants[invariant.id] = invariant

    if errors:
        _log.error(
            "load_invariants: %d of %d file(s) under %s failed to load: %s",
            len(errors),
            len(inv_paths),
            directory,
            ", ".join(e.path for e in errors),
        )
    _log.info(
        "load_invariants: loaded %d invariant(s) from %s", len(invariants), directory
    )
    return LoadedInvariants(invariants=tuple(invariants.values()), errors=tuple(errors))


__all__ = [
    "EXCLUSIVITY_CLAIM_PATTERNS",
    "NORMATIVE_CLAIM_PATTERNS",
    "Invariant",
    "InvariantError",
    "InvariantLoadError",
    "LoadedInvariants",
    "_Criticality",
    "find_exclusivity_claims",
    "find_normative_claims",
    "load_invariants",
]
