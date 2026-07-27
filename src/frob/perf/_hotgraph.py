"""Hot-graph collector contract: language-neutral hit-stream + normalized-
model section resolver (T-0710, EPIC T-0709's first child).

CONTRACT MANDATE (user, 2026-07-22): the hit-stream this module defines is
LANGUAGE-NEUTRAL BY CONSTRUCTION -- a `SampledStack` is nothing but
`(file, line, weight)` frames; the resolver maps those onto section ids
using only `frob.arch._normalized.NormalizedModule` line spans (function
bodies, and the loop/branch bodies nested inside them), never touching
`frob.lang`/tree-sitter or any python-specific runtime state. The python
sampler in `frob.perf._sampler` is merely the FIRST producer of this
stream -- sibling ticket T-0748 feeds native/V8/JVM profiles into the same
`SampledStack`/`resolve_stream` contract via per-language collector
adapters (mirroring `frob.arch._normalized.LanguageAdapter`), with zero
changes needed here.

NO-FAIL-SILENT: a frame that resolves to no section is never dropped --
it is attributed to the `UNATTRIBUTED_SECTION_ID` sentinel section, so
total sampled weight is always conserved and visible (`HitStream.
unattributed_weight`) rather than silently vanishing from the hot-graph.

Section spans are DERIVED, not authoritative: `NormalizedFunction` carries
a real `(line, body_line_count)` span, but `NormalizedLoop`/
`NormalizedBranch` carry only a single anchor line (T-0609 did not need
more for its detectors) in a FLATTENED sibling list with no nesting info.
DEGRADE-TO-CORRECT (T-0710 review round 2): a block's true body span is
unknowable from anchor lines alone once a function has more than one
loop/branch (is the next anchor a sibling after this block, or nested
inside it?) -- guessing wrong here is silent MIS-attribution, worse than
`UNATTRIBUTED_SECTION_ID`, since it names the wrong section with total
confidence. So a block only gets an extended span (to the function's end)
when it is PROVABLY the function's only block; the instant 2+ blocks
compete, every block in that function degrades to a single-line span (its
own anchor line only) and everything else in the function resolves to the
enclosing FUNCTION section instead -- coarser, but never wrong. See
`_block_sections`' docstring for the full mechanism and
`docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709` for the
documented tradeoff.
"""

# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/perf/_hotgraph.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from pydantic import BaseModel

from frob.arch._normalized import (
    NormalizedBranch,
    NormalizedClass,
    NormalizedFunction,
    NormalizedLoop,
    NormalizedModule,
)
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "UNATTRIBUTED_SECTION_ID",
    "EdgeHit",
    "HitStream",
    "LanguageDecileRow",
    "SampledFrame",
    "SampledStack",
    "Section",
    "SectionHit",
    "SectionIndex",
    "build_section_index",
    "language_deciles",
    "resolve_stream",
]

#: File-extension -> a human-readable language label for `language_deciles`'
#: per-language grouping -- deliberately just a display label (never a
#: parse decision, unlike `frob.perf._collectors`' adapter-selection
#: table), so an extension `frob.arch` has no adapter for still gets a
#: readable bucket name instead of vanishing from the CLI's output.
_DECILE_LANGUAGE_LABELS: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".kt": "kotlin",
    ".kts": "kotlin",
}

#: Label for a section hit whose file carries no known extension mapping,
#: or `UNATTRIBUTED_SECTION_ID` itself -- always a visible bucket, never a
#: silently dropped fraction of the stream's total weight.
_OTHER_LANGUAGE_LABEL = "other"

#: Sentinel section id a sample attributes to when its `(file, line)` matches
#: no known section span -- NEVER dropped (see module docstring's NO-FAIL-
#: SILENT contract), always a visible, explicit bucket in a `HitStream`.
# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
UNATTRIBUTED_SECTION_ID = "unattributed"


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class SampledFrame(BaseModel):
    """One stack frame in a single stack sample: source file (repo-relative
    or as reported by the collector) and 1-based line number -- the
    language-neutral unit every per-language collector adapter (python
    today, native/V8/JVM per T-0748) produces. Weight lives on the
    enclosing `SampledStack`, not per-frame: every frame of one sample
    shares that sample's single weight, so it is not duplicated here."""

    model_config = {}

    file: str
    line: int


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class SampledStack(BaseModel):
    """One full sampled call stack, innermost (leaf) frame first, all
    sharing this sample's `weight`. The leaf frame attributes self-time to
    a section; the leaf's caller (`frames[1]`, when present) plus the leaf
    attribute a call edge (caller section -> callee), the shared unit both
    per-section and per-edge hit streams are built from."""

    model_config = {}

    frames: tuple[SampledFrame, ...]
    weight: float = 1.0


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class SectionHit(BaseModel):
    """One resolved sample's attribution to a section id, with its weight.
    `section_id` is `UNATTRIBUTED_SECTION_ID` (never dropped -- see the
    module docstring's NO-FAIL-SILENT contract) when the sample's leaf
    frame matched no known section span."""

    model_config = {}

    section_id: str
    weight: float


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class EdgeHit(BaseModel):
    """One resolved call edge: a caller section id calling `callee` (a bare
    function/method name, or `qualname` for a resolved internal callee),
    classified `is_external` when the callee's frame falls outside every
    section this repo's normalized model knows about (a stdlib/third-party
    call) -- the "external call dominating a loop body" signal T-0712's
    advisories key off of."""

    model_config = {}

    caller_section_id: str
    callee: str
    is_external: bool
    weight: float


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class HitStream(BaseModel):
    """The resolver's full output for one batch of `SampledStack`s: the
    per-section and per-edge hit streams T-0711's sketch store ingests, plus
    `unattributed_weight` (samples matching no section, surfaced -- never
    silently dropped) so a caller can always account for 100 percent of
    sampled weight."""

    model_config = {}

    section_hits: tuple[SectionHit, ...] = ()
    edge_hits: tuple[EdgeHit, ...] = ()

    @property
    # frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
    # frob:tests tests/unit/perf/test_hotgraph.py::TestResolveStream.test_unresolvable_leaf_is_unattributed_never_dropped  # noqa: E501
    def unattributed_weight(self) -> float:
        """Total weight attributed to `UNATTRIBUTED_SECTION_ID` -- the
        NO-FAIL-SILENT accounting this stream always exposes."""
        return sum(
            hit.weight
            for hit in self.section_hits
            if hit.section_id == UNATTRIBUTED_SECTION_ID
        )


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class Section(BaseModel):
    """One resolvable code unit -- a function/method body, or a loop/branch
    body nested inside one -- with the `[start_line, end_line]` (inclusive,
    1-based) span the resolver matches a sample's `(file, line)` against.
    `id` is a stable sha256-derived id over `(file, qualname, kind,
    start_line)`: stable across repeated runs of the SAME tree, so repeated
    profiling sessions of an unchanged codebase accumulate onto the same
    section id; T-0711's sketch store is responsible for the line-drift-
    tolerant symbol-digest keying its own ticket calls out, layered on top
    of this id, not a replacement for it."""

    model_config = {}

    id: str
    kind: str  # "function" | "loop" | "branch"
    qualname: str
    file: str
    start_line: int
    end_line: int


#: file -> its `Section`s, sorted by `start_line` ascending, for lookup.
SectionIndex = dict[str, list[Section]]


def _section_id(file: str, qualname: str, kind: str, start_line: int) -> str:
    """Sha256 hex id (16 hex chars) over `(file, qualname, kind,
    start_line)` -- stable across repeated runs of an unchanged tree."""
    joined = "\x00".join((file, qualname, kind, str(start_line)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _function_end_line(func: NormalizedFunction) -> int:
    """Approximate last line of `func`'s body: its own line plus the
    body's recorded line count (0 when a language adapter found no body,
    e.g. an abstract/protocol stub -- the function's own line is then both
    its start and end)."""
    if func.body_line_count <= 0:
        return func.line
    return func.line + func.body_line_count - 1


def _block_sections(
    file: str,
    func_qualname: str,
    func_end_line: int,
    branches: list[NormalizedBranch],
    loops: list[NormalizedLoop],
    nested_starts: list[int],
) -> list[Section]:
    """Loop/branch `Section`s nested directly inside one function --
    DEGRADE-TO-CORRECT (T-0710 review round 2, replacing the round-1
    next-sibling-boundary approximation this review REJECTED for real
    mis-attribution): `NormalizedLoop`/`NormalizedBranch` are FLATTENED
    sibling lists with no nesting information, so a block's true body
    span (does it end before the next anchor, or does the next anchor sit
    NESTED inside this block's own body?) is fundamentally unknowable from
    anchor lines alone the moment a function has more than one block.
    Guessing "next anchor's line minus one" for that case silently
    mis-attributes: a branch NESTED inside a loop was previously given a
    span reaching all the way to the function's end (nothing else claimed
    those lines), so a sample taken in the LOOP's body AFTER the branch
    resolved to the WRONG branch section instead of the loop -- wrong and
    silent, exactly the hot-graph poison this contract promises never to
    produce (see the module docstring's NO-FAIL-SILENT contract, which
    this closes a hole in).

    The sound fix: a block only gets an EXTENDED span (its anchor line to
    `func_end_line`, bounded by any nested-function start) when it is
    PROVABLY the function's only block -- one loop or one branch, nothing
    else competing for the remaining lines, so there is no sibling/nested
    ambiguity to get wrong. The instant a function has 2+ loops/branches,
    EVERY block in it degrades to a single-line span (`start_line ==
    end_line`, its own anchor line only) -- a sample landing on a block's
    own header line still resolves to that exact block (still useful,
    still precise), but any other line in the ambiguous function falls
    through to the enclosing FUNCTION section instead of a guessed
    sibling -- coarser, but NEVER wrong. See `docs/modules/perf.md#hot-
    graph-collector-t-0710-epic-t-0709` for the documented tradeoff and
    `tests/unit/perf/test_hotgraph.py::TestResolveStream.
    test_loop_body_after_nested_branch_never_attributes_to_branch` for the
    regression this fixes."""
    blocks: list[tuple[int, str]] = [(b.line, "branch") for b in branches]
    blocks += [(loop.line, "loop") for loop in loops]
    unambiguous = len(blocks) == 1
    boundary_lines = sorted({*nested_starts, func_end_line + 1})

    sections: list[Section] = []
    for line, kind in sorted(blocks):
        if unambiguous:
            later = [b for b in boundary_lines if b > line]
            end_line = (min(later) - 1) if later else func_end_line
            end_line = max(end_line, line)
        else:
            end_line = line
        qualname = f"{func_qualname}::{kind}@{line}"
        sections.append(
            Section(
                id=_section_id(file, qualname, kind, line),
                kind=kind,
                qualname=qualname,
                file=file,
                start_line=line,
                end_line=end_line,
            )
        )
    return sections


def _function_sections(
    file: str, qualname_prefix: str, func: NormalizedFunction
) -> list[Section]:
    """`Section`s for one function/method: itself, its directly-nested
    loops/branches, and (recursively) any nested function definitions."""
    qualname = f"{qualname_prefix}.{func.name}" if qualname_prefix else func.name
    end_line = _function_end_line(func)
    sections = [
        Section(
            id=_section_id(file, qualname, "function", func.line),
            kind="function",
            qualname=qualname,
            file=file,
            start_line=func.line,
            end_line=end_line,
        )
    ]
    nested_starts = [nested.line for nested in func.nested_functions]
    sections += _block_sections(
        file, qualname, end_line, func.branches, func.loops, nested_starts
    )
    for nested in func.nested_functions:
        sections += _function_sections(file, qualname, nested)
    return sections


def _class_sections(file: str, cls: NormalizedClass) -> list[Section]:
    """`Section`s for every method of one class, qualname-prefixed by the
    class name (`Class.method`, matching `frob.graph`'s qualname style)."""
    sections: list[Section] = []
    for method in cls.methods:
        sections += _function_sections(file, cls.name, method)
    return sections


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_hotgraph.py::TestResolveStream.test_leaf_in_loop_body_attributes_to_loop_section  # noqa: E501
# frob:ticket T-0972
def build_section_index(modules: list[NormalizedModule]) -> SectionIndex:
    """Build a `SectionIndex` (file -> sorted `Section`s) from one or more
    `NormalizedModule`s -- the language-agnostic prerequisite `resolve_
    stream` matches sampled frames against. Works identically for a
    python, TypeScript, rust, kotlin, or cpp module: everything here reads
    only shared `NormalizedModule`/`NormalizedFunction`/`NormalizedLoop`/
    `NormalizedBranch` fields, never a language-specific tree."""
    index: SectionIndex = {}
    for module in modules:
        sections: list[Section] = []
        for func in module.functions:
            sections += _function_sections(module.path, "", func)
        for cls in module.classes:
            sections += _class_sections(module.path, cls)
        # frob:waive PERF004 reason="sections is this loop's own per-module distinct list, not a shared re-sort"  # noqa: E501
        sections.sort(key=lambda s: s.start_line)
        index[module.path] = sections
        _log.debug(
            "build_section_index: %s -> %d section(s)", module.path, len(sections)
        )
    return index


def _resolve_frame(index: SectionIndex, frame: SampledFrame) -> Section | None:
    """The innermost (smallest-span) `Section` in `index` whose file+span
    contains `frame.line`, or `None` when no section matches (the caller
    attributes this to `UNATTRIBUTED_SECTION_ID`, never drops it)."""
    candidates = [
        section
        for section in index.get(frame.file, ())
        if section.start_line <= frame.line <= section.end_line
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda s: s.end_line - s.start_line)


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_hotgraph.py::TestResolveStream.test_leaf_in_loop_body_attributes_to_loop_section  # noqa: E501
# frob:tests tests/unit/perf/test_hotgraph.py::TestResolveStream.test_call_edge_classified_external_when_callee_unmodeled  # noqa: E501
# frob:tests tests/unit/perf/test_hotgraph.py::TestResolveStream.test_unresolvable_leaf_is_unattributed_never_dropped  # noqa: E501
def resolve_stream(index: SectionIndex, stacks: list[SampledStack]) -> HitStream:
    """Resolve `stacks` (from any collector adapter -- python today,
    native/V8/JVM per T-0748) into a `HitStream` against `index`.

    Per-section hits come from each stack's leaf (innermost) frame.
    Per-edge hits come from the leaf calling its caller (`frames[1]`, when
    present): `is_external` when the caller frame resolves to no section
    in `index` (a stdlib/third-party frame this repo's normalized model
    never modeled). A leaf resolving to no section is NEVER dropped -- it
    is still emitted as a `SectionHit(UNATTRIBUTED_SECTION_ID, weight)`,
    per the module docstring's NO-FAIL-SILENT contract.
    """
    section_hits: list[SectionHit] = []
    edge_hits: list[EdgeHit] = []
    for stack in stacks:
        if not stack.frames:
            continue
        leaf = stack.frames[0]
        leaf_section = _resolve_frame(index, leaf)
        leaf_id = (
            leaf_section.id if leaf_section is not None else UNATTRIBUTED_SECTION_ID
        )
        section_hits.append(SectionHit(section_id=leaf_id, weight=stack.weight))
        if leaf_section is None:
            _log.debug(
                "resolve_stream: unattributed frame file=%s line=%s weight=%s",
                leaf.file,
                leaf.line,
                stack.weight,
            )
        if len(stack.frames) > 1:
            caller = stack.frames[1]
            caller_section = _resolve_frame(index, caller)
            if caller_section is not None:
                callee = (
                    leaf_section.qualname
                    if leaf_section is not None
                    else f"external:{leaf.file}:{leaf.line}"
                )
                edge_hits.append(
                    EdgeHit(
                        caller_section_id=caller_section.id,
                        callee=callee,
                        is_external=leaf_section is None,
                        weight=stack.weight,
                    )
                )
    return HitStream(section_hits=tuple(section_hits), edge_hits=tuple(edge_hits))


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
class LanguageDecileRow(BaseModel):
    """One decile bucket (`decile` 1..10, 1 = the hottest 10 percent by
    weight) of one language's resolved section hits -- `frob perf
    collect`'s rendering unit (T-0765). `section_count` is how many
    distinct sections fall in this bucket, `weight` their summed hit
    weight; `language` is `UNATTRIBUTED_SECTION_ID`'s own bucket
    (`"unattributed"`) for samples that matched no section, or
    `"other"` for a resolved section whose file carries an extension
    `language_deciles` has no display label for -- both real, visible
    buckets, never merged away or dropped (NO-FAIL-SILENT)."""

    model_config = {}

    language: str
    decile: int
    weight: float
    section_count: int


def _decile_language(section_id: str, file_by_section: dict[str, str]) -> str:
    """Display language for `section_id`: `"unattributed"` for the
    sentinel, `language_deciles`' extension label for a real section, or
    `_OTHER_LANGUAGE_LABEL` when the section's file has no known
    extension mapping."""
    if section_id == UNATTRIBUTED_SECTION_ID:
        return UNATTRIBUTED_SECTION_ID
    file = file_by_section.get(section_id, "")
    suffix = PurePosixPath(file).suffix
    return _DECILE_LANGUAGE_LABELS.get(suffix, _OTHER_LANGUAGE_LABEL)


# frob:doc docs/modules/perf.md#hot-graph-collector-t-0710-epic-t-0709
# frob:tests tests/unit/perf/test_collectors.py::TestLanguageDeciles.test_resolve_stream_output_feeds_language_deciles_end_to_end  # noqa: E501
# frob:ticket T-0972
def language_deciles(stream: HitStream, index: SectionIndex) -> list[LanguageDecileRow]:
    """Bucket `stream`'s per-section hit weight into 10 rank-ordered
    deciles PER LANGUAGE (decile 1 = a language's hottest-ranked 10
    percent of its OWN sections, never mixed across languages) -- the
    `frob perf collect` rendering `resolve_stream`'s language-neutral
    output feeds directly (T-0765). A language with fewer than 10
    distinct sections still gets up to 10 rows (one row per section,
    unpadded) rather than a divide-by-zero or a fabricated empty row.
    `UNATTRIBUTED_SECTION_ID`'s own weight is exposed as a single-row
    `"unattributed"` bucket (decile 1), matching this module's NO-FAIL-
    SILENT accounting -- never silently folded into another language's
    total."""
    file_by_section = {
        section.id: section.file for sections in index.values() for section in sections
    }
    totals: dict[str, float] = {}
    for hit in stream.section_hits:
        totals[hit.section_id] = totals.get(hit.section_id, 0.0) + hit.weight

    by_language: dict[str, list[tuple[str, float]]] = {}
    for section_id, weight in totals.items():
        language = _decile_language(section_id, file_by_section)
        by_language.setdefault(language, []).append((section_id, weight))

    rows: list[LanguageDecileRow] = []
    for language, entries in sorted(by_language.items()):
        # frob:waive PERF004 reason="entries is this loop's own per-language distinct list, not a shared re-sort"  # noqa: E501
        ranked = sorted(entries, key=lambda pair: pair[1], reverse=True)
        n = len(ranked)
        bucket_size = max(1, -(-n // 10))  # ceil(n / 10), at least 1
        for decile in range(1, 11):
            start = (decile - 1) * bucket_size
            if start >= n:
                break
            bucket = ranked[start : start + bucket_size]
            if not bucket:
                continue
            rows.append(
                LanguageDecileRow(
                    language=language,
                    decile=decile,
                    weight=sum(w for _, w in bucket),
                    section_count=len(bucket),
                )
            )
    return rows
