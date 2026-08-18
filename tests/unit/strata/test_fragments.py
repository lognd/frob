"""Unit tests for the T-2502 fragment mechanism: `module`/`part of`/`extend`
grammar (`strata-core/src/parse`) and its merge-time closure in
`frob.strata._multifile.resolve_fragments`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from frob.strata._ast import MayGrantDecl, NodeDecl
from frob.strata._multifile import SealedGrantSet, elaborate_merged, resolve_fragments
from frob.strata._parse import parse_module


def _test_module(text: str):
    parsed = parse_module(text)
    assert parsed.is_ok, parsed.danger_err
    return parsed.danger_ok


ROOT = (
    "module frob\n"
    'node testsuite : trusted { clearance Internal; may "exec" via "a.py"; }\n'
)


class TestParseFragmentGrammar:
    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_part_of_parses
    def test_part_of_parses(self) -> None:
        """`part of NAME` sets `part_of` and leaves `name` empty -- a
        fragment declares no module of its own."""
        m = _test_module(
            'part of frob\nextend node testsuite { may "exec" via "b.py"; }\n'
        )
        assert m.part_of == "frob"
        assert m.name == ""
        assert len(m.extends) == 1
        assert m.extends[0].id == "testsuite"
        assert m.extends[0].may_grants[0].atom == "exec"
        assert m.extends[0].may_grants[0].via == ("b.py",)

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_root_has_no_pa\
    # rt_of
    def test_root_has_no_part_of(self) -> None:
        """A plain `module NAME` file (the pre-T-2502 shape) still parses
        with `part_of=None`, `extends=()` -- no behavior change for the
        single-file case."""
        m = _test_module(ROOT)
        assert m.part_of is None
        assert m.extends == ()

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_fragment_canno\
    # t_declare_module
    def test_fragment_cannot_declare_module(self) -> None:
        """A file cannot say both `part of` and `module` -- refused at
        parse time (structural, not a loader-level check)."""
        r = parse_module("part of frob\nmodule frob\n")
        assert r.is_err

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_fragment_canno\
    # t_declare_new_node
    def test_fragment_cannot_declare_new_node(self) -> None:
        """A fragment introducing a fresh top-level `node` is refused at
        parse time -- fragments extend, they do not stand alone."""
        r = parse_module("part of frob\nnode zzz : trusted { clearance Internal; }\n")
        assert r.is_err

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_extend_cannot_\
    # set_clearance
    def test_extend_cannot_set_clearance(self) -> None:
        """An `extend node` block cannot spell `clearance` (or any other
        node field) -- the grammar only has vocabulary for `may ... via
        ...`, structurally preventing a fragment from weakening/replacing
        anything but a via-list."""
        r = parse_module("part of frob\nextend node testsuite { clearance Public; }\n")
        assert r.is_err

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestParseFragmentGrammar.test_extend_grant_r\
    # equires_via
    def test_extend_grant_requires_via(self) -> None:
        """A via-less `may "ATOM";` inside `extend node` is refused -- an
        unscoped grant is a fresh whole-node bless, not a widening of
        anything, so a fragment may never write one."""
        r = parse_module('part of frob\nextend node testsuite { may "exec"; }\n')
        assert r.is_err


class TestResolveFragments:
    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_widens_existing_gr\
    # ant
    def test_widens_existing_grant(self) -> None:
        """POSITIVE CONTROL: a fragment extending a declared node's
        EXISTING grant loads and takes effect -- the root's via-list is
        widened by set-union, order-preserving."""
        root = _test_module(ROOT)
        frag = _test_module(
            'part of frob\nextend node testsuite { may "exec" via "b.py", "c.py"; }\n'
        )
        resolved = resolve_fragments((("root.strata", root), ("frag.strata", frag)))
        assert resolved.is_ok
        ((_, resolved_root), _) = resolved.danger_ok
        node = next(n for n in resolved_root.nodes if n.id == "testsuite")
        grant = next(g for g in node.may_grants if g.atom == "exec")
        assert grant.via == ("a.py", "b.py", "c.py")

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_extend_takes_effec\
    # t_through_elaborate_merged
    def test_extend_takes_effect_through_elaborate_merged(self) -> None:
        """POSITIVE CONTROL, end to end: the widened grant survives the
        full `elaborate_merged` pipeline used by the real loader."""
        root = _test_module(ROOT)
        frag = _test_module(
            'part of frob\nextend node testsuite { may "exec" via "b.py"; }\n'
        )
        result = elaborate_merged((("root.strata", root), ("frag.strata", frag)))
        assert result.is_ok
        node = next(n for n in result.danger_ok.nodes if n.id == "testsuite")
        grant = next(g for g in node.may_grants if g.atom == "exec")
        assert grant.via == ("a.py", "b.py")

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_no_root_is_error
    def test_no_root_is_error(self) -> None:
        """NEGATIVE CONTROL: every loaded file is a fragment, no root --
        refused."""
        frag = _test_module(
            'part of frob\nextend node testsuite { may "exec" via "b.py"; }\n'
        )
        resolved = resolve_fragments((("frag.strata", frag),))
        assert resolved.is_err

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_two_roots_is_error
    def test_two_roots_is_error(self) -> None:
        """NEGATIVE CONTROL: two files declare `module frob` and a
        fragment targets that name -- the closure boundary is ambiguous
        for the fragment, refused naming both root files. (Two files
        sharing a module name with NO fragment targeting it is the
        pre-existing T-1196 multi-module merge, untouched by T-2502 --
        see test_unrelated_multi_module_merge_is_unaffected.)"""
        root_a = _test_module(ROOT)
        root_b = _test_module(
            "module frob\nnode other : trusted { clearance Internal; }\n"
        )
        frag = _test_module(
            'part of frob\nextend node other { may "exec" via "b.py"; }\n'
        )
        resolved = resolve_fragments(
            (("a.strata", root_a), ("b.strata", root_b), ("f.strata", frag))
        )
        assert resolved.is_err
        paths = {e.path for e in resolved.danger_err}
        assert paths == {"a.strata", "b.strata"}

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_unrelated_multi_mo\
    # dule_merge_is_unaffected
    def test_unrelated_multi_module_merge_is_unaffected(self) -> None:
        """T-1196's pre-existing multi-file merge (several independently
        named `module` files, no fragments at all) passes through
        `resolve_fragments` completely untouched -- T-2502 does not
        mandate modularity or retroactively require a single root name
        for a design that never uses `part of`."""
        a = _test_module("module a\nnode client : foreign { clearance Public; }\n")
        b = _test_module("module b\nnode api : authenticated { clearance Internal; }\n")
        resolved = resolve_fragments((("a.strata", a), ("b.strata", b)))
        assert resolved.is_ok
        assert resolved.danger_ok == (("a.strata", a), ("b.strata", b))

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_root_name_\
    # is_error
    def test_unknown_root_name_is_error(self) -> None:
        """NEGATIVE CONTROL: a fragment names a root that was never
        loaded -- refused as a distinct case from an unknown node."""
        root = _test_module(ROOT)
        frag = _test_module(
            'part of not_frob\nextend node testsuite { may "exec" via "b.py"; }\n'
        )
        resolved = resolve_fragments((("root.strata", root), ("frag.strata", frag)))
        assert resolved.is_err
        assert "nonexistent root" in resolved.danger_err[0].message

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_node_is_er\
    # ror
    def test_unknown_node_is_error(self) -> None:
        """NEGATIVE CONTROL: `extend node` targets an id the root never
        declared -- refused as a distinct case from an unknown atom."""
        root = _test_module(ROOT)
        frag = _test_module(
            'part of frob\nextend node ghost { may "exec" via "b.py"; }\n'
        )
        resolved = resolve_fragments((("root.strata", root), ("frag.strata", frag)))
        assert resolved.is_err
        assert "never declared" in resolved.danger_err[0].message

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_unknown_atom_is_er\
    # ror
    def test_unknown_atom_is_error(self) -> None:
        """NEGATIVE CONTROL, the hard constraint: a fragment cannot grant
        a capability the root never granted to that node in the first
        place -- refused, distinct message from the unknown-node case."""
        root = _test_module(ROOT)
        frag = _test_module(
            'part of frob\nextend node testsuite { may "net.out" via "b.py"; }\n'
        )
        resolved = resolve_fragments((("root.strata", root), ("frag.strata", frag)))
        assert resolved.is_err
        assert (
            "cannot grant a capability the root refused"
            in resolved.danger_err[0].message
        )

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestResolveFragments.test_single_file_design\
    # _passes_through_unchanged
    def test_single_file_design_passes_through_unchanged(self) -> None:
        """MUST-STILL-PASS control: a single root file with no fragments
        (the current `design/frob.strata` shape) passes through
        `resolve_fragments` with zero changes -- backward compatible."""
        root = _test_module(ROOT)
        resolved = resolve_fragments((("root.strata", root),))
        assert resolved.is_ok
        assert resolved.danger_ok == (("root.strata", root),)


_SEALED_GRANT_FRESH_INSERT_PROBE = '''
from frob.strata._ast import MayGrantDecl
from frob.strata._multifile import SealedGrantSet


def attempt_insert_fresh_atom(sealed: SealedGrantSet) -> None:
    """T-2530 positive control: `SealedGrantSet.grants` is typed as
    `Mapping[str, MayGrantDecl]` (never `dict`), so this assignment must
    be REJECTED by the type checker before the code could ever run --
    inserting a fresh atom is not an expressible operation on this type,
    not merely one this test happens not to exercise."""
    sealed.grants["net.out"] = MayGrantDecl(
        atom="net.out", via=(), exclusive=False, of=()
    )
'''


class TestSealedGrantSet:
    """T-2530: the fragment merge (`_multifile._widen_node_grants` and its
    callers) used to pass a plain `dict[str, MayGrantDecl]` around and
    mutate it directly -- correct only because every call site happened
    to union into an existing key, a property nothing enforced. These
    tests assert the STRONGER contract `SealedGrantSet` replaces it
    with: inserting a fresh atom is impossible, not merely untested, in
    both the type checker and at runtime."""

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_declared_at\
    # om_still_works
    def test_widen_on_declared_atom_still_works(self) -> None:
        """POSITIVE CONTROL (direction 1, unchanged from T-2502): widening
        an ALREADY-DECLARED atom's `via` list still works through the
        sealed type -- the mechanism must keep working, not just refuse
        harder."""
        node = NodeDecl(
            id="a",
            trust="trusted",
            clearance="Internal",
            may_grants=(_may_grant("exec", ("a.py",)),),
        )
        sealed = SealedGrantSet.from_root_node(node)
        assert sealed.widen("exec", ("b.py",)) is True
        assert sealed.grants["exec"].via == ("a.py", "b.py")

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_widen_on_undeclared_\
    # atom_refuses_closed
    def test_widen_on_undeclared_atom_refuses_closed(self) -> None:
        """POSITIVE CONTROL (direction 2, unchanged from T-2502): an atom
        the root never granted still refuses closed -- `widen` returns
        `False` and changes nothing, rather than inserting."""
        node = NodeDecl(id="a", trust="trusted", clearance="Internal", may_grants=())
        sealed = SealedGrantSet.from_root_node(node)
        assert sealed.widen("net.out", ("b.py",)) is False
        assert "net.out" not in sealed.grants

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_fresh_insert_raises_\
    # at_runtime
    def test_fresh_insert_raises_at_runtime(self) -> None:
        """NEW POSITIVE CONTROL this ticket adds: an attempt IN CODE to
        assign a fresh key through the public `grants` view raises
        `TypeError` immediately (`MappingProxyType` has no `__setitem__`
        at all) -- this is real construction-time/runtime enforcement,
        not a convention a careless edit could silently drop."""
        node = NodeDecl(id="a", trust="trusted", clearance="Internal", may_grants=())
        sealed = SealedGrantSet.from_root_node(node)
        with pytest.raises(TypeError):
            sealed.grants["net.out"] = _may_grant("net.out", ())  # ty: ignore[invalid-assignment]

    # frob:tests \
    # tests/unit/strata/test_fragments.py::TestSealedGrantSet.test_fresh_insert_fails_s\
    # tatic_type_check
    def test_fresh_insert_fails_static_type_check(self, tmp_path: Path) -> None:
        """NEW POSITIVE CONTROL this ticket adds, the STATIC half: the
        exact same fresh-insert attempt, written as ordinary source and
        run through this repo's own `ty check`, is rejected as
        `invalid-assignment` BEFORE the code would ever execute --
        `Mapping[str, MayGrantDecl]` has no `__setitem__` in its
        interface, so the type checker itself proves the operation is
        inexpressible, matching `TestSnapshotParameterDroppedStatically\
        Enforced` (tests/test_gates_fix_engine.py)'s precedent for a
        "cannot be typed, not merely avoided by convention" claim."""
        if shutil.which("ty") is None:
            pytest.skip("ty binary not available")

        probe = tmp_path / "sealed_grant_fresh_insert_probe.py"
        probe.write_text(_SEALED_GRANT_FRESH_INSERT_PROBE, encoding="utf-8")

        result = subprocess.run(
            ["ty", "check", str(probe)],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr

        assert result.returncode != 0, output
        assert "invalid-assignment" in output, output
        assert "__setitem__" in output, output


def _may_grant(atom: str, via: tuple[str, ...]) -> MayGrantDecl:
    return MayGrantDecl(atom=atom, via=via, exclusive=False, of=())
