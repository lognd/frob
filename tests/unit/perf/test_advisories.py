"""T-0712: `frob.perf._advisories`'s three slow-operation advisory shapes
(external-call-dominates-loop, nested-loop fan-in, heavy-tail variance),
built purely off a `HitStream`/`SectionIndex` (no live profiling)."""

from __future__ import annotations

from frob.perf._advisories import (
    external_call_advisories,
    heavy_tail_advisories,
    nested_loop_fanin_advisories,
)
from frob.perf._hotgraph import EdgeHit, HitStream, Section, SectionHit
from frob.stats._sketch import DEFAULT_ALPHA, add_value, new_sketch


def _loop_section(qualname: str = "pkg.mod.hot_loop", section_id: str = "loop-1"):
    return Section(
        id=section_id,
        kind="loop",
        qualname=qualname,
        file="pkg/mod.py",
        start_line=4,
        end_line=8,
    )


class TestExternalCallAdvisories:
    def test_dominant_external_edge_fires(self) -> None:
        loop = _loop_section()
        index = {"pkg/mod.py": [loop]}
        stream = HitStream(
            section_hits=(SectionHit(section_id=loop.id, weight=10.0),),
            edge_hits=(
                EdgeHit(
                    caller_section_id=loop.id,
                    callee="requests.get",
                    is_external=True,
                    weight=8.0,
                ),
            ),
        )
        violations = external_call_advisories(stream, index)
        assert len(violations) == 1
        assert violations[0].rule == "PERF-ADV-EXT"
        assert "requests.get" in violations[0].message

    def test_minor_external_edge_does_not_fire(self) -> None:
        loop = _loop_section()
        index = {"pkg/mod.py": [loop]}
        stream = HitStream(
            section_hits=(SectionHit(section_id=loop.id, weight=10.0),),
            edge_hits=(
                EdgeHit(
                    caller_section_id=loop.id,
                    callee="requests.get",
                    is_external=True,
                    weight=1.0,
                ),
            ),
        )
        assert external_call_advisories(stream, index) == []


class TestNestedLoopFaninAdvisories:
    def test_hot_loop_with_multiple_callers_fires(self) -> None:
        inner = _loop_section(qualname="pkg.mod.inner", section_id="loop-inner")
        caller_a = _loop_section(qualname="pkg.mod.caller_a", section_id="loop-a")
        caller_b = _loop_section(qualname="pkg.mod.caller_b", section_id="loop-b")
        index = {"pkg/mod.py": [inner, caller_a, caller_b]}
        stream = HitStream(
            section_hits=(
                SectionHit(section_id=inner.id, weight=9.0),
                SectionHit(section_id=caller_a.id, weight=0.5),
                SectionHit(section_id=caller_b.id, weight=0.5),
            ),
            edge_hits=(
                EdgeHit(
                    caller_section_id=caller_a.id,
                    callee=inner.qualname,
                    is_external=False,
                    weight=4.5,
                ),
                EdgeHit(
                    caller_section_id=caller_b.id,
                    callee=inner.qualname,
                    is_external=False,
                    weight=4.5,
                ),
            ),
        )
        violations = nested_loop_fanin_advisories(stream, index)
        assert len(violations) == 1
        assert violations[0].rule == "PERF-ADV-FANIN"
        assert "pkg.mod.inner" in violations[0].message

    def test_single_caller_loop_does_not_fire(self) -> None:
        inner = _loop_section(qualname="pkg.mod.inner", section_id="loop-inner")
        caller_a = _loop_section(qualname="pkg.mod.caller_a", section_id="loop-a")
        index = {"pkg/mod.py": [inner, caller_a]}
        stream = HitStream(
            section_hits=(SectionHit(section_id=inner.id, weight=9.0),),
            edge_hits=(
                EdgeHit(
                    caller_section_id=caller_a.id,
                    callee=inner.qualname,
                    is_external=False,
                    weight=9.0,
                ),
            ),
        )
        assert nested_loop_fanin_advisories(stream, index) == []


def _sketch(values: list[float]):
    sketch = new_sketch(alpha=DEFAULT_ALPHA)
    for value in values:
        sketch = add_value(sketch, value)
    return sketch


class TestHeavyTailAdvisories:
    def test_heavy_tail_ratio_fires(self) -> None:
        # Bimodal: mostly cheap, occasionally 10x -- p90 >> p50.
        values = [1.0] * 80 + [15.0] * 20
        sketches = {"k1": ("pkg.mod.fn", "pkg/mod.py", 3, _sketch(values))}
        violations = heavy_tail_advisories(sketches)
        assert len(violations) == 1
        assert violations[0].rule == "PERF-ADV-VARIANCE"
        assert "pkg.mod.fn" in violations[0].message

    def test_uniform_distribution_does_not_fire(self) -> None:
        values = [10.0] * 100
        sketches = {"k1": ("pkg.mod.fn", "pkg/mod.py", 3, _sketch(values))}
        assert heavy_tail_advisories(sketches) == []
