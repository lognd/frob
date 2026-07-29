"""`frob.perf._advisories` -- hot-graph slow-operation advisories (T-0712,
EPIC T-0709, suggestion tier per T-0332's noise discipline: WARN-only,
never gated to error, always waivable).

Three shapes, all read straight off a resolved `HitStream` (T-0710) --
no re-profiling, no new IO:

1. **External-call-dominates-loop**: a call edge out of a loop section
   whose callee is external (unmodeled -- stdlib/third-party) and whose
   weight share of that loop's own total weight crosses
   `_EXTERNAL_DOMINANCE_THRESHOLD` -> batch/cache/hoist suggestion.
2. **Nested-loop hot upstream of a fan-in**: a loop section nested inside
   another loop (approximated here as "loop kind, qualname contains a
   dot" is NOT reliable -- instead this uses `Section.kind == "loop"`
   PLUS more than one caller-section edge feeding into it, i.e. the
   section is a fan-in target for 2+ distinct callers) whose own weight
   share of the file's total crosses the same dominance threshold ->
   complexity-suspect advisory.
3. **Heavy-tail variance**: a section whose stored sketch has `p90 >>
   p50` (ratio beyond `_HEAVY_TAIL_RATIO`) -> variance advisory naming
   likely bimodal/outlier-driven behavior.

Every advisory is a `Violation` at `Severity.WARN` (this project has no
separate "suggestion" severity -- WARN is the suggestion tier, matching
PERF001-004's own posture) so it renders through the same gate-finding
machinery as every other PERF rule without inventing a parallel reporting
path.
"""
# frob:waive INV006 reason="T-0712: this module's 'only' usage ('WARN-only') is \
# source-level design-rationale prose describing already-implemented internal behavior \
# (verifiable by reading the Violation(severity=Severity.WARN, ...) calls below), not \
# a separate cross-module contract needing its own tracked invariant; same \
# calibration-batch disposition as the T-0585/T-0711 INV006 pool"

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.perf._hotgraph import HitStream, Section, SectionIndex
from frob.stats._sketch import QuantileSketch, quantile

_log = get_logger(__name__)

__all__ = [
    "external_call_advisories",
    "heavy_tail_advisories",
    "nested_loop_fanin_advisories",
]

#: An external call (or a hot nested loop) eating this fraction or more of
#: its enclosing section's total resolved weight is "dominating" it.
_DOMINANCE_THRESHOLD = 0.5

#: p90/p50 ratio beyond which a section's latency is "heavy-tailed" enough
#: to name explicitly rather than silently averaged away.
_HEAVY_TAIL_RATIO = 3.0


def _all_sections(index: SectionIndex) -> dict[str, Section]:
    """`{Section.id: Section}` across every file in `index` -- the lookup
    every advisory below needs to go from a hit's bare id back to the
    section it names."""
    return {section.id: section for sections in index.values() for section in sections}


# frob:doc docs/modules/perf.md#slow-operation-advisories-t-0712
# frob:tests tests/unit/perf/test_advisories.py::TestExternalCallAdvisories.test_dominant_external_edge_fires  # noqa: E501
# frob:tests tests/unit/perf/test_advisories.py::TestExternalCallAdvisories.test_minor_external_edge_does_not_fire  # noqa: E501
# frob:ticket T-0972
def external_call_advisories(stream: HitStream, index: SectionIndex) -> list[Violation]:
    """One `PERF-ADV-EXT` advisory per loop section whose external call
    edge(s) sum to at least `_DOMINANCE_THRESHOLD` of that loop's own
    total resolved weight -- "this loop's time is mostly one external
    call" (T-0712's "batch/cache/move-out-of-loop" wording)."""
    sections = _all_sections(index)
    loop_total: dict[str, float] = {}
    for hit in stream.section_hits:
        loop_total[hit.section_id] = loop_total.get(hit.section_id, 0.0) + hit.weight

    external_by_caller: dict[str, list[tuple[str, float]]] = {}
    for edge in stream.edge_hits:
        if not edge.is_external:
            continue
        external_by_caller.setdefault(edge.caller_section_id, []).append(
            (edge.callee, edge.weight)
        )

    violations: list[Violation] = []
    for caller_id, edges in external_by_caller.items():
        section = sections.get(caller_id)
        if section is None or section.kind != "loop":
            continue
        total = loop_total.get(caller_id, 0.0)
        if total <= 0.0:
            continue
        external_weight = sum(weight for _, weight in edges)
        share = external_weight / total
        if share < _DOMINANCE_THRESHOLD:
            continue
        callee_names = ", ".join(sorted({callee for callee, _ in edges}))
        violations.append(
            Violation(
                rule="PERF-ADV-EXT",
                severity=Severity.WARN,
                file=section.file,
                line=section.start_line,
                message=(
                    f"loop {section.qualname!r} spends {share * 100:.0f}% of its "
                    f"sampled time in external call(s) {callee_names} -- consider "
                    "batching, caching, or hoisting the call out of the loop"
                ),
            )
        )
    return violations


# frob:ticket T-0976
def _section_and_file_weight_totals(
    stream: HitStream, sections: dict
) -> tuple[dict[str, float], dict[str, float]]:
    """`(section_id -> total weight, file -> total weight)` from `stream`'s
    `section_hits` -- `nested_loop_fanin_advisories`'s weight-aggregation
    half, split from its fan-in/dominance check."""
    section_total: dict[str, float] = {}
    for hit in stream.section_hits:
        section_total[hit.section_id] = (
            section_total.get(hit.section_id, 0.0) + hit.weight
        )
    file_total: dict[str, float] = {}
    for section_id, weight in section_total.items():
        section = sections.get(section_id)
        if section is None:
            continue
        file_total[section.file] = file_total.get(section.file, 0.0) + weight
    return section_total, file_total


# frob:ticket T-0976
def _loop_callers_by_callee(stream: HitStream, sections: dict) -> dict[str, set[str]]:
    """`loop-section-id -> {distinct caller section ids}` from `stream`'s
    non-external `edge_hits` -- `nested_loop_fanin_advisories`'s fan-in
    computation half, split from its weight-aggregation half."""
    callers_by_callee: dict[str, set[str]] = {}
    for edge in stream.edge_hits:
        if edge.is_external:
            continue
        callee_section = next(
            (
                s
                for s in sections.values()
                if s.qualname == edge.callee and s.kind == "loop"
            ),
            None,
        )
        if callee_section is None:
            continue
        callers_by_callee.setdefault(callee_section.id, set()).add(
            edge.caller_section_id
        )
    return callers_by_callee


# frob:doc docs/modules/perf.md#slow-operation-advisories-t-0712
# frob:tests tests/unit/perf/test_advisories.py::TestNestedLoopFaninAdvisories.test_hot_loop_with_multiple_callers_fires  # noqa: E501
# frob:tests tests/unit/perf/test_advisories.py::TestNestedLoopFaninAdvisories.test_single_caller_loop_does_not_fire  # noqa: E501
def nested_loop_fanin_advisories(
    stream: HitStream, index: SectionIndex
) -> list[Violation]:
    """One `PERF-ADV-FANIN` advisory per hot loop section reached from 2+
    DISTINCT caller sections (a fan-in: this loop's own body runs on
    behalf of multiple call sites, so its cost multiplies with every new
    caller) whose own weight share of its file's total resolved weight
    crosses `_DOMINANCE_THRESHOLD` -- "hot AND a shared dependency" is the
    complexity-suspect shape this names."""
    sections = _all_sections(index)
    section_total, file_total = _section_and_file_weight_totals(stream, sections)
    callers_by_callee = _loop_callers_by_callee(stream, sections)

    violations: list[Violation] = []
    for section_id, callers in callers_by_callee.items():
        if len(callers) < 2:
            continue
        section = sections.get(section_id)
        if section is None:
            continue
        total = file_total.get(section.file, 0.0)
        weight = section_total.get(section_id, 0.0)
        if total <= 0.0 or weight / total < _DOMINANCE_THRESHOLD:
            continue
        violations.append(
            Violation(
                rule="PERF-ADV-FANIN",
                severity=Severity.WARN,
                file=section.file,
                line=section.start_line,
                message=(
                    f"loop {section.qualname!r} is hot ({weight / total * 100:.0f}% "
                    f"of its file's sampled time) and called from {len(callers)} "
                    "distinct sites -- complexity suspect, check for a shared "
                    "abstraction that could amortize the cost"
                ),
            )
        )
    return violations


# frob:doc docs/modules/perf.md#slow-operation-advisories-t-0712
# frob:tests tests/unit/perf/test_advisories.py::TestHeavyTailAdvisories.test_heavy_tail_ratio_fires  # noqa: E501
# frob:tests tests/unit/perf/test_advisories.py::TestHeavyTailAdvisories.test_uniform_distribution_does_not_fire  # noqa: E501
def heavy_tail_advisories(
    sketches: dict[str, tuple[str, str, int, QuantileSketch]],
) -> list[Violation]:
    """One `PERF-ADV-VARIANCE` advisory per `(label, file, line, sketch)`
    entry in `sketches` (keyed by section_key, `frob.perf._sketch_store`'s
    persisted rows -- this advisory reads history, not one run, since a
    single run's own sketch is exactly the shape T-0711's stored value
    already is) whose `p90 / p50` ratio exceeds `_HEAVY_TAIL_RATIO` --
    "this section's tail is much worse than its typical case," naming
    likely variance-driving modes (concurrency contention, cold-cache
    misses, GC pauses) for the caller to go look for."""
    violations: list[Violation] = []
    for label, file, line, sketch in sketches.values():
        p50 = quantile(sketch, 0.5)
        p90 = quantile(sketch, 0.9)
        if p50 <= 0.0:
            continue
        ratio = p90 / p50
        if ratio < _HEAVY_TAIL_RATIO:
            continue
        violations.append(
            Violation(
                rule="PERF-ADV-VARIANCE",
                severity=Severity.WARN,
                file=file,
                line=line,
                message=(
                    f"{label!r} has a heavy tail: p90 is {ratio:.1f}x p50 -- "
                    "likely bimodal (cache miss, contention, or a cold-start "
                    "path); consider isolating the slow mode"
                ),
            )
        )
    return violations
