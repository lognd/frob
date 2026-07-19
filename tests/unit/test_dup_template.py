"""Unit tests for `frob.dup._template.build_group_template` (docs/modules/dup.md's
"Reverse-templating report" section, T-0195).

Litmus shapes per the ticket: one-leaf divergence -> one hole with both
concrete sides visible; identical bodies -> zero holes; a >2-member group
folds to one shared skeleton with per-member bindings that share hole ids.
Skips (rather than fails) when `frob_core` is not installed -- same posture
as tests/test_dup_smart.py, since `anti_unify` needs the native extension.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import _core as dup_core
from frob.dup._models import ClonePair, CloneRegion
from frob.dup._template import build_group_template

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)


def _write(root: Path, name: str, literal: int) -> CloneRegion:
    """Write a one-function file `name` returning `x + literal`; region for the whole def."""
    (root / name).write_text(f"def f(x):\n    return x + {literal}\n")
    return CloneRegion(ref=f"{name}::f", span=(1, 2))


class TestBuildGroupTemplate:
    def test_one_leaf_divergence_yields_one_hole_with_both_sides(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        left = _write(tmp_path, "a.py", 1)
        right = _write(tmp_path, "b.py", 2)
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        assert template.holes == (0,)
        assert "$hole_0" in template.skeleton_text
        assert len(template.bindings) == 2
        sides = {group[0].source_text for group in template.bindings}
        assert sides == {"1", "2"}
        assert "hole_0" in template.suggested_signature

    def test_identical_bodies_yield_zero_holes(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        left = _write(tmp_path, "a.py", 1)
        right = _write(tmp_path, "c.py", 1)
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        assert template.holes == ()
        assert "$hole_" not in template.skeleton_text
        assert all(group == () for group in template.bindings)

    def test_three_member_group_folds_to_one_shared_skeleton(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        a = _write(tmp_path, "a.py", 1)
        b = _write(tmp_path, "b.py", 2)
        d = _write(tmp_path, "d.py", 3)
        pairs = (
            ClonePair(left=a, right=b, similarity=1.0, rung="test"),
            ClonePair(left=a, right=d, similarity=1.0, rung="test"),
            ClonePair(left=b, right=d, similarity=1.0, rung="test"),
        )

        template = build_group_template(tmp_path, pairs)

        assert template is not None
        assert template.holes == (0,)
        assert len(template.bindings) == 3
        literals = {group[0].source_text for group in template.bindings}
        assert literals == {"1", "2", "3"}
        # every member's binding names the same hole id -- the fold kept
        # numbering stable across all three members, not just a pair.
        assert all(group[0].hole == 0 for group in template.bindings)

    def test_single_member_returns_none(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        # A "group" with only one distinct region (both pair sides identical
        # ref/span, a degenerate input no real pipeline produces) has
        # nothing to generalize over.
        left = _write(tmp_path, "a.py", 1)
        pair = ClonePair(left=left, right=left, similarity=1.0, rung="test")

        assert build_group_template(tmp_path, (pair,)) is None

    def test_unrecoverable_subtree_returns_none_not_raises(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        left = CloneRegion(ref="missing.py::f", span=(1, 2))
        right = _write(tmp_path, "b.py", 2)
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        assert build_group_template(tmp_path, (pair,)) is None
