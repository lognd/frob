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
from frob.dup._models import CloneBinding, ClonePair, CloneRegion
from frob.dup._template import _hole_param_name, build_group_template

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

    def test_literal_rendering_preserves_source_text_not_a_skeleton(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        left = _write(tmp_path, "a.py", 1)
        right = _write(tmp_path, "b.py", 2)
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        # literal source characters survive verbatim (e.g. "return", "x +"),
        # not a `label(child, ...)` structural approximation.
        assert "return x + $hole_0" in template.skeleton_text

    def test_suggested_signature_falls_back_when_not_a_plain_identifier(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
        left = _write(tmp_path, "a.py", 1)
        right = _write(tmp_path, "b.py", 2)
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        # both sides are numeric literals, never a valid parameter name.
        assert "hole_0" in template.suggested_signature

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


class TestTypeHoleClassification:
    """T-0287: holes whose divergence sits in a type-annotation position
    (python's `type` wrapper node) in EVERY group member propose a shared
    type variable instead of a bare value hole."""

    # frob:waive DUP001 reason="parallel test methods within test_dup_template.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def _write_typed(self, root: Path, name: str, type_name: str) -> CloneRegion:
        """A one-function file annotating both its parameter and return
        type as `type_name` (kept equal on purpose: this isolates the
        TYPE-position divergence from any value-position divergence)."""
        (root / name).write_text(
            f"def f(x: {type_name}) -> {type_name}:\n    return x\n"
        )
        return CloneRegion(ref=f"{name}::f", span=(1, 2))

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_matching_type_annotations_propose_one_shared_type_var(self, tmp_path):
        left = self._write_typed(tmp_path, "a.py", "int")
        right = self._write_typed(tmp_path, "b.py", "str")
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        # two divergences (param annotation, return annotation), both
        # type-shaped and co-varying identically (int/str on both) -- one
        # shared type var, not two independent ones.
        assert template.type_params == ("T0",)
        assert template.skeleton_text.count("T0") == 2
        assert "$hole_" not in template.skeleton_text
        for group in template.bindings:
            assert len(group) == 2
            assert all(b.type_var == "T0" for b in group)
        assert 'T0 = TypeVar("T0")' in template.suggested_signature
        # a pure type-hole template extracts no value parameters.
        assert "def _extracted(): ..." in template.suggested_signature

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_value_divergence_alongside_type_divergence_stays_separate(self, tmp_path):
        (tmp_path / "a.py").write_text("def f(x: int) -> int:\n    return x + 1\n")
        (tmp_path / "b.py").write_text("def f(x: str) -> str:\n    return x + 2\n")
        left = CloneRegion(ref="a.py::f", span=(1, 2))
        right = CloneRegion(ref="b.py::f", span=(1, 2))
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        assert template.type_params == ("T0",)
        # the `1`/`2` literal divergence is a plain value hole, untouched
        # by the type classification -- it still renders as $hole_N and
        # still contributes a suggested-signature parameter.
        assert "$hole_" in template.skeleton_text
        assert "hole_" in template.suggested_signature.split("\n")[-1]
        type_bindings = [
            b for group in template.bindings for b in group if b.type_var is not None
        ]
        value_bindings = [
            b for group in template.bindings for b in group if b.type_var is None
        ]
        assert len(type_bindings) == 4  # 2 members x 2 type positions
        assert len(value_bindings) == 2  # 2 members x 1 value hole

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_type_position_in_one_member_only_stays_a_value_hole(self, tmp_path):
        # Consistency guard: the divergence sits in a type-annotation
        # position for ONE member but the SAME hole id's other member
        # binds a plain value position (a synthetic shape no real
        # anti-unify fold produces from typed/untyped python -- built
        # directly to exercise the guard) -- never emit a bogus generic
        # when the sides do not agree on being type-shaped.
        from frob.dup._template import _classify_type_vars

        # hole 0 bound at a type-position node in member 0 (index 1, whose
        # parent index 0 is a "type" node) but a bare identifier at the
        # top level (index 0, no parent) in member 1.
        trees: list[
            tuple[
                tuple[str, ...],
                tuple[int, ...],
                tuple[tuple[int, int], ...],
                tuple[str | None, ...],
            ]
        ] = [
            (("type", "int"), (-1, 0), ((0, 10), (1, 4)), (None, None)),
            (("x",), (-1,), ((0, 1),), (None,)),
        ]
        hole_node_idx = {0: [1, 0]}
        hole_source_texts = {0: ["int", "x"]}

        assert _classify_type_vars(hole_node_idx, hole_source_texts, trees) == {}


class TestHoleParamName:
    """`_hole_param_name` is pure Python (no `frob_core` dependency) -- covered
    directly rather than only indirectly through a full `anti_unify` fold.
    """

    # frob:waive DUP001 reason="parallel test methods within test_dup_template.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_reuses_shared_plain_identifier(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::_hole_param_name kind="unit"
        region = CloneRegion(ref="a.py::f", span=(1, 2))
        bindings = (
            (CloneBinding(hole=0, region=region, source_text="count"),),
            (CloneBinding(hole=0, region=region, source_text="count"),),
        )

        assert _hole_param_name(0, bindings) == "count"

    # frob:waive DUP001 reason="parallel test methods within test_dup_template.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_falls_back_when_members_disagree(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::_hole_param_name kind="unit"
        region = CloneRegion(ref="a.py::f", span=(1, 2))
        bindings = (
            (CloneBinding(hole=0, region=region, source_text="count"),),
            (CloneBinding(hole=0, region=region, source_text="other"),),
        )

        assert _hole_param_name(0, bindings) == "hole_0"

    # frob:waive DUP001 reason="parallel test methods within test_dup_template.py (3 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def test_falls_back_when_shared_text_is_not_a_plain_identifier(self, tmp_path):
        # frob:tests src/frob/dup/_template.py::_hole_param_name kind="unit"
        region = CloneRegion(ref="a.py::f", span=(1, 2))
        bindings = (
            (CloneBinding(hole=0, region=region, source_text="a.b"),),
            (CloneBinding(hole=0, region=region, source_text="a.b"),),
        )

        assert _hole_param_name(0, bindings) == "hole_0"


class TestTypeHoleClassificationRust:
    """T-0495: rust has no `type`/`type_annotation` WRAPPER node
    (`_TYPE_WRAPPER_LABELS`) -- its `parameter` node places the type as a
    direct sibling distinguished only by tree-sitter FIELD NAME ("type"
    vs "pattern"), which `frob.lang.TreeNode.field` (T-0495) now carries.
    Non-vacuous per the ticket: a real rust clone pair with CONSISTENT
    type annotations proposes a shared type variable; one whose only real
    divergence is a plain VALUE position does not (proving the field-name
    rule doesn't over-fire)."""

    def _write_typed(self, root: Path, name: str, type_name: str) -> CloneRegion:
        """A one-function rust file annotating both its parameter and
        return type as `type_name` (kept equal on purpose, mirroring
        `TestTypeHoleClassification._write_typed`'s python shape)."""
        (root / name).write_text(f"fn f(x: {type_name}) -> {type_name} {{\n    x\n}}\n")
        return CloneRegion(ref=f"{name}::f", span=(1, 3))

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_matching_type_annotations_propose_one_shared_type_var(self, tmp_path):
        left = self._write_typed(tmp_path, "a.rs", "i32")
        right = self._write_typed(tmp_path, "b.rs", "u64")
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        # param annotation + return annotation, both type-shaped and
        # co-varying identically (i32/u64 on both) -- one shared type
        # var, not two independent ones, and no wrapper node involved
        # (rust's `parameter`/`function_item` field name IS the signal).
        assert template.type_params == ("T0",)
        assert template.skeleton_text.count("T0") == 2
        assert "$hole_" not in template.skeleton_text
        for group in template.bindings:
            assert len(group) == 2
            assert all(b.type_var == "T0" for b in group)

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_value_only_divergence_is_never_misclassified_as_a_type_hole(
        self, tmp_path
    ):
        # Negative counterpart, real files: both members share the IDENTICAL
        # type annotation ("i32" on both sides, both param and return), so
        # anti-unify never opens a hole at either type-field position at
        # all -- the only divergence is the body expression (a plain
        # `identifier`, no field name), a value position. Proves the new
        # field-name-based rule (`_TYPE_FIELD_NAMES`) does not spuriously
        # fire outside a true type position -- if it over-matched (e.g. any
        # node under a `parameter`/`function_item`, not just the "type"
        # field), this body-expression hole would be wrongly promoted to a
        # type variable.
        left = self._write_typed(tmp_path, "a.rs", "i32")
        (tmp_path / "c.rs").write_text("fn f(x: i32) -> i32 {\n    y\n}\n")
        right = CloneRegion(ref="c.rs::f", span=(1, 3))
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        assert all(b.type_var is None for group in template.bindings for b in group)
        assert template.type_params == ()


class TestTypeHoleClassificationC:
    """T-0495: c shares rust's field-name-only convention for a
    `parameter_declaration`'s type (field "type", no wrapper node), but
    unlike rust reuses the SAME field name ("type") for its
    `function_definition`'s return type too (no separate "return_type"
    field). One litmus fixture proving c's shape is real, matching the
    "c/cpp if feasible" acceptance note -- cpp inherits the identical
    grammar shape for this construct and is not independently fixtured."""

    # frob:waive DUP001 reason="parallel test methods within test_dup_template.py (2 sites) \
    # sharing an arrange-act scaffold typical of exhaustive per-case \
    # coverage; extracting would obscure per-case intent"
    def _write_typed(self, root: Path, name: str, type_name: str) -> CloneRegion:
        """A one-function c file annotating both its parameter and return
        type as `type_name` (kept equal on purpose, mirroring the rust
        fixture's shape)."""
        (root / name).write_text(
            f"{type_name} f({type_name} x) {{\n    return x;\n}}\n"
        )
        return CloneRegion(ref=f"{name}::f", span=(1, 3))

    # frob:tests src/frob/dup/_template.py::build_group_template kind="unit"
    def test_matching_type_annotations_propose_one_shared_type_var(self, tmp_path):
        left = self._write_typed(tmp_path, "a.c", "int")
        right = self._write_typed(tmp_path, "b.c", "long")
        pair = ClonePair(left=left, right=right, similarity=1.0, rung="test")

        template = build_group_template(tmp_path, (pair,))

        assert template is not None
        # param type + return type, both classified via the SAME "type"
        # field name (c has no separate return_type field, unlike rust) --
        # one shared type var, not two independent ones.
        assert template.type_params == ("T0",)
        assert template.skeleton_text.count("T0") == 2
        assert "$hole_" not in template.skeleton_text
