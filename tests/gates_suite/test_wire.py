import subprocess
from pathlib import Path

from frob.gates import (
    Severity,
)
from frob.gitio import Diff, Hunk, working_diff
from frob.tickets import TicketQueue, TicketState
from tests.conftest import (
    _first_rule,
    _git_init,
    _snapshot,
    _ticket,
    _write,
)


class TestDeadSymbolGate:
    """T-0422: an unreferenced private symbol (written but never wired) is
    the symbol-level analog of REF001's anti-orphan file gate.

    frob:ticket T-0422
    """

    # frob:ticket T-0422
    def test_unwired_private_function_is_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _never_called() -> None:\n    pass\n\n\ndef foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert any(
            v.rule == "DEAD001" and "_never_called" in v.message for v in violations
        )
        assert all(v.severity == Severity.WARN for v in violations)

    # frob:ticket T-0422
    def test_called_private_helper_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _helper() -> int:\n"
            "    return 1\n"
            "\n\n"
            "def foo() -> int:\n"
            "    return _helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_helper" in v.message for v in violations)

    # frob:ticket T-1881
    def test_call_site_in_constant_folded_dead_branch_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1881: the `_store_mode` shape from T-1552's v1-ledger
        unwiring measurement -- a producer function collapsed to
        unconditionally `return "v2"`, with the guarded `else` arm's call
        site still textually present. `_helper`'s only call site sits in
        that now-unreachable arm, so DEAD001 must still flag it even
        though a bare token scan would see `_helper(` in the source."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _mode() -> str:\n"
            '    return "v2"\n\n\n'
            "def _helper() -> None:\n"
            "    pass\n\n\n"
            "def dispatch() -> str:\n"
            '    if _mode() == "v2":\n'
            '        return "v2-path"\n'
            "    else:\n"
            "        _helper()\n"
            '        return "v1-path"\n',
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert any(v.rule == "DEAD001" and "_helper" in v.message for v in violations)

    # frob:ticket T-1881
    def test_call_site_in_constant_folded_local_var_dead_branch_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1881 acceptance [1]: the fold also covers a comparison one
        LOCAL VARIABLE hop away from the constant-return call
        (`mode = _mode(); if mode != "v2": ...`), not only a direct
        `_mode() == "v2"` call-site comparison."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _mode() -> str:\n"
            '    return "v2"\n\n\n'
            "def _helper() -> None:\n"
            "    pass\n\n\n"
            "def dispatch() -> None:\n"
            "    mode = _mode()\n"
            '    if mode != "v2":\n'
            "        _helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert any(v.rule == "DEAD001" and "_helper" in v.message for v in violations)

    # frob:ticket T-1881
    def test_call_site_in_live_branch_is_not_flagged_by_constant_fold(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1881 false-positive guard: the constant-fold override must
        never mark a symbol dead when it also has a call site OUTSIDE any
        folded-dead branch -- here `_helper` is called unconditionally,
        so it must stay unflagged even though `_mode` is a constant-
        return function elsewhere in the same file."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _mode() -> str:\n"
            '    return "v2"\n\n\n'
            "def _helper() -> None:\n"
            "    pass\n\n\n"
            "def dispatch() -> str:\n"
            "    _helper()\n"
            '    if _mode() == "v2":\n'
            '        return "v2-path"\n'
            '    return "v1-path"\n',
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_helper" in v.message for v in violations)

    # frob:ticket T-1881
    def test_dead_caller_two_hops_deep_still_misses_confirming_open_defect(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1881 acceptance [2]: DISCLOSED, NOT FIXED here. When a
        symbol's only caller is itself dead PURELY via the ordinary
        SYNTACTIC route (its own dispatch-table entry was deleted
        outright -- no constant-fold involved at all) and the target
        symbol is a SECOND hop further out (`_leaf` is called only by
        `_mid`, and `_mid`'s own only reference was a now-deleted
        dispatch-table entry), DEAD001 flags the one-hop-dead `_mid` but
        still misses the two-hop-dead `_leaf` -- confirming the real
        repo's `_require_merge_driver_args`/`_archived_ids_for_merge_
        driver` finding is a genuine, separate defect from this ticket's
        constant-folding fix, not incidentally closed by it. This test
        is evidence FOR the acceptance criterion's claim (the gap still
        exists), not evidence the gap is fixed."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _leaf() -> None:\n"
            "    pass\n\n\n"
            "def _mid() -> None:\n"
            "    _leaf()\n\n\n"
            "def _live() -> None:\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        flagged = {(v.symref or "").rsplit("::", 1)[-1] for v in violations}
        # `_mid` (one-hop, its own zero-caller status is directly
        # syntactic) IS caught -- this part already worked pre-T-1881.
        assert "_mid" in flagged
        # `_leaf` (two hops from the nearest live root) is STILL missed
        # -- the open defect acceptance [2] describes, confirmed, not
        # resolved, by this fix.
        assert "_leaf" not in flagged

    # frob:ticket T-1652
    def test_waiver_directly_above_symbol_suppresses_it(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1651: DEAD001's Violation now carries `symref`, so a
        `frob:waive DEAD001 reason="..."` placed directly above the
        flagged symbol (the exact pattern the gate's own message
        recommends) actually matches via `_match_waiver`'s symbol-exact
        path -- previously every such waiver silently failed to bind
        because the Violation left `symref` unset (None), forcing every
        DEAD001 waiver onto the file-scoped fallback instead."""
        from frob.gates import _apply_waivers
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive DEAD001 reason="reached only via getattr dispatch"\n'
            "def _never_called() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        kept, waived = _apply_waivers(violations, snap)
        assert not any("_never_called" in v.message for v in kept)
        assert any("_never_called" in v.message for v in waived)

    # frob:ticket T-1652
    def test_pydantic_field_validator_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1651: a `@field_validator`/`@model_validator`-decorated private
        method is dispatched by pydantic's own decorator registry, never by
        a call token this gate's `build_reference_graph` scan can see --
        `_is_pydantic_validator` rescues it the same way WIRE001's
        autouse-pytest-fixture rescue covers that gate's own analogous
        dynamic-dispatch shape."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "from pydantic import BaseModel, field_validator\n\n\n"
            "class Foo(BaseModel):\n"
            "    model_config = {}\n"
            "    x: str\n\n"
            '    @field_validator("x")\n'
            "    @classmethod\n"
            "    def _check_x(cls, v: str) -> str:\n"
            "        return v\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_check_x" in v.message for v in violations)

    # frob:ticket T-1652
    def test_autouse_pytest_fixture_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1651: an `@pytest.fixture(autouse=True)` fixture is invoked
        implicitly by pytest's own injection machinery for every test in
        its module, never by a name/call token this gate's reference-graph
        scan can see -- `_is_autouse_pytest_fixture` (moved here from
        WIRE001's own T-1510 rescue) exempts it. DEAD001 previously lacked
        this exemption entirely."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "import pytest\n\n\n"
            "@pytest.fixture(autouse=True)\n"
            "def _reset_env() -> None:\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_reset_env" in v.message for v in violations)

    # frob:ticket T-0422
    def test_dunder_method_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    def __init__(self) -> None:\n        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("__init__" in v.message for v in violations)

    # frob:ticket T-0422
    def test_test_function_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "class Foo:\n    def _test_never_called_directly(self) -> None:\n        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_test_never_called_directly" in v.message for v in violations)

    # frob:ticket T-0422
    def test_tests_edge_target_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _never_called() -> None:\n"
            '    # frob:tests tests/test_a.py::test_never_called kind="unit"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_never_called" in v.message for v in violations)

    # frob:ticket T-1959
    def test_call_site_inside_with_block_dead_branch_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-1959 class-1 miss (`_render_ledger`, T-1881 evidence): the real
        repo's `write_all`/`write_archive` mode-dispatch sits INSIDE a
        `with ledger_lock(root):` block, not at the function's own top
        level -- `_walk_dead_ranges` (T-1881) only ever recurses into an
        `if` statement's branches, never into a `with`/`async with` body,
        so a constant-folded dispatch nested one `with` deep was
        completely invisible to the fold pass (verified empirically
        against `bdb39bde3`: the real `write_all` dispatch's dead branch
        was silently unscanned, not merely unfolded). `_helper`'s only
        call site sits in the dead branch of a `with`-nested dispatch, so
        this must still flag it."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _mode() -> str:\n"
            '    return "v2"\n\n\n'
            "def _helper() -> None:\n"
            "    pass\n\n\n"
            "class _Lock:\n"
            "    def __enter__(self) -> None:\n"
            "        return None\n\n"
            "    def __exit__(self, *exc: object) -> None:\n"
            "        return None\n\n\n"
            "def dispatch() -> str:\n"
            "    with _Lock():\n"
            '        if _mode() == "v2":\n'
            '            return "v2-path"\n'
            "        _helper()\n"
            '        return "v1-path"\n',
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert any(v.rule == "DEAD001" and "_helper" in v.message for v in violations)

    # frob:ticket T-1959
    def test_call_site_inside_with_block_live_branch_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """False-positive guard for the T-1959 `with`-recursion fix: a
        call site inside a `with` block's LIVE branch (the fold resolves
        `True`, not `False`) must stay unflagged -- recursing into a
        `with` body must not accidentally treat everything inside it as
        dead."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _mode() -> str:\n"
            '    return "v2"\n\n\n'
            "def _helper() -> None:\n"
            "    pass\n\n\n"
            "class _Lock:\n"
            "    def __enter__(self) -> None:\n"
            "        return None\n\n"
            "    def __exit__(self, *exc: object) -> None:\n"
            "        return None\n\n\n"
            "def dispatch() -> str:\n"
            "    with _Lock():\n"
            '        if _mode() == "v2":\n'
            "            _helper()\n"
            '            return "v2-path"\n'
            '        return "v1-path"\n',
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        assert not any("_helper" in v.message for v in violations)

    # frob:ticket T-2205
    def test_dead_symbol_gate_verifies_imports_across_a_same_named_collision(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_dead_symbols.py::dead_symbol_gate kind="unit"
        """T-2205: `dead_symbol_gate`'s own `build_reference_graph` call
        now passes `verify_imports=True` (T-2188 added the flag,
        T-2195/T-2211 fixed the primitive it depends on -- this ticket
        wires it into the one consumer named in its own title). Before
        this wiring, TWO unrelated sibling files each defining a private
        `_target` with the SAME short name, where only ONE of them is
        genuinely called and NEITHER imports the other, collapsed to a
        single ambiguous edge (the T-2156 bare-short-name-collision
        defect `build_call_graph`'s own docstring documents) -- masking
        the genuinely dead `_target` in `b.py` as called, purely because
        a same-named symbol happens to be called somewhere else in the
        same package directory. `verify_imports=True` requires a real
        import edge for a cross-file candidate, so only `a.py`'s own
        `_target` (called from within `a.py` itself, no import needed)
        resolves -- `b.py`'s `_target`, never imported by anyone, must
        now read as genuinely dead."""
        from frob.gates._dead_symbols import dead_symbol_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _target() -> None:\n"
            "    pass\n\n\n"
            "def user() -> None:\n"
            "    _target()\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "def _target() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = dead_symbol_gate(tmp_path, snap)
        flagged_paths = {
            v.file for v in violations if v.rule == "DEAD001" and "_target" in v.message
        }
        assert flagged_paths == {"src/b.py"}


# frob:ticket T-1428
# frob:ticket T-1502
# frob:ticket T-1746
class TestWireGate:
    """T-1428: refuse a ticket's own diff when it adds a function with no
    non-test caller, a gate rule id absent from `_KNOWN_GATE_RULES`, or a
    CLI flag `dest` absent from `_config_external.py` -- the repeat
    "landed, passed every gate, did nothing" defect (T-1384/T-1399/
    T-1391/T-1421/T-1422)."""

    # frob:ticket T-1428
    def test_new_public_function_with_no_caller_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Reconstructs T-1421's shape: a new guard function, unit-tested
        # directly, wired into nothing outside its own test.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_own_obligations_clean() -> None:\n"
            "    assert own_obligations_clean()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "own_obligations_clean" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "own_obligations_clean" in v.message
        assert v.severity == Severity.ERROR

    # frob:ticket T-1558
    def test_shared_test_fixture_called_from_a_sibling_test_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """A helper DEFINED under `tests/` that is only ever called from a
        DIFFERENT test file (never from production code) is genuinely
        wired -- WIRE001's reachability scan must count a cross-test-file
        caller, not just skip every test path the way it treats production
        symbols (the live T-1558 class:
        `tests/_cache_transparency.py::git_init`, called only from
        `tests/test_cache_transparency.py`)."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "tests/_shared_helper.py",
            "def git_init(root) -> None:\n    return None\n",
        )
        _write(
            tmp_path,
            "tests/test_uses_helper.py",
            "from tests._shared_helper import git_init\n\n"
            "def test_it(tmp_path) -> None:\n    git_init(tmp_path)\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "git_init" in r.symref)
        diff = Diff(
            base="x", hunks=(Hunk(file="tests/_shared_helper.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(v.rule == "WIRE001" for v in violations)

    # frob:ticket T-1746
    def test_test_helper_called_from_a_real_test_in_the_same_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """T-1746: a helper called directly from a genuine `test_*`
        function in its OWN defining file now counts as reached -- the
        same-file test-fixture-reuse false positive this ticket exists
        for (T-1727's motivating case: a shared fixture two test classes
        in one file both call from real `test_*` methods). Superseded the
        pre-T-1746 assertion that same-file usage never counts."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "tests/test_only_self.py",
            "def _make_thing() -> bool:\n    return True\n\n"
            "def test_it() -> None:\n    assert _make_thing()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_make_thing" in r.symref)
        diff = Diff(
            base="x", hunks=(Hunk(file="tests/test_only_self.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is None

    # frob:ticket T-1746
    def test_test_helper_called_only_from_a_non_test_helper_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """T-1746's narrower allowance does NOT swallow the genuinely-
        unwired case: a helper called only from ANOTHER non-`test_*`
        helper in the same file (never from a real test function, never
        from a different file, never from production code) still trips
        WIRE001 -- T-1746 only recognizes a call sitting inside an actual
        `test_*` function/method, not same-file text in general."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "tests/test_only_self.py",
            "def _make_thing() -> bool:\n    return True\n\n"
            "def _other_helper() -> bool:\n    return _make_thing()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_make_thing" in r.symref)
        diff = Diff(
            base="x", hunks=(Hunk(file="tests/test_only_self.py", span=record.span),)
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None

    # frob:ticket T-1428
    def test_new_function_called_from_non_test_code_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "from a import own_obligations_clean\n\n\n"
            "def caller() -> bool:\n"
            "    return own_obligations_clean()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "own_obligations_clean" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "own_obligations_clean" in v.message
            for v in violations
        )

    # frob:ticket T-1502
    def test_new_function_passed_bare_to_a_wrapper_marker_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1502: `memoize_per_run(_target)` (or `wraps`/`lru_cache`/
        # `cache`) passes the wrapped symbol BY REFERENCE, never as a
        # `name(`-shaped call token -- WIRE001 must not treat this as
        # unreached (frob.graph.callgraph._WRAPPER_MARKER_NAMES).
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _target() -> bool:\n"
            "    return True\n\n\n"
            "cached = memoize_per_run(_target)\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_target() -> None:\n    assert _target()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_target" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_target" in v.message for v in violations
        )

    # frob:ticket T-1807
    def test_new_function_reached_via_module_qualified_dict_table_value_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1807: `"frob_map": _tools.frob_map,` (the exact style every
        # row of src/frob/serve/_socketd.py::_TOOL_DISPATCH uses) is a
        # dict-table wiring shape same as a bare `"key": _target,` value
        # -- WIRE001 must not flag it just because a module-qualifier
        # sits between the colon and the short name.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def frob_map() -> bool:\n"
            "    return True\n\n\n"
            '_TOOL_DISPATCH = {"frob_map": _tools.frob_map}\n',
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_dispatch() -> None:\n    assert _TOOL_DISPATCH\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "frob_map" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "frob_map" in v.message for v in violations
        )

    # frob:ticket T-1502
    def test_new_function_named_like_a_wrapper_argument_but_never_passed_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Negative case: the wrapper-marker allowance must not blanket-
        # exempt every symbol in a file that happens to mention
        # `memoize_per_run` -- a genuinely unwired sibling still fires.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _target() -> bool:\n"
            "    return True\n\n\n"
            "def _unwired() -> bool:\n"
            "    return False\n\n\n"
            "cached = memoize_per_run(_target)\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_unwired() -> None:\n    assert not _unwired()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_unwired" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(v.rule == "WIRE001" and "_unwired" in v.message for v in violations)

    # frob:ticket T-1527
    def test_new_errorset_class_referenced_by_bare_member_access_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1527: a typani ErrorSet subclass is never referenced call-
        # shaped (MyError(...)) -- callers spell it MyError.Member (bare
        # attribute access, no parens); WIRE001 must not treat that as
        # unreached (src/frob/testing/_coverage_refresh.py's
        # CoverageRefreshError instance).
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "class MyError:\n    Broken = 'x'\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "from a import MyError\n\n\n"
            "def make_result():\n"
            "    return MyError.Broken\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_myerror() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "MyError" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "MyError" in v.message for v in violations
        )

    # frob:ticket T-1527
    def test_new_class_never_referenced_by_member_access_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Negative case: the member-access allowance must not blanket-
        # exempt every new class -- one genuinely never referenced (by
        # call OR attribute access) anywhere still fires.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "class UnreferencedThing:\n    Marker = 'x'\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_unreferenced() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r for r in snap.symbols.values() if "UnreferencedThing" in r.symref
        )
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "UnreferencedThing" in v.message for v in violations
        )

    # frob:ticket T-1532
    def test_new_function_passed_bare_to_process_job_constructor_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1532: a gate function registered into the process job table as
        # a bare positional argument (`_ProcessJob(cache_gate, (...))`) is
        # genuinely wired but never text-adjacent to its own `(` -- the
        # job-table analog of T-1502's wrapper-marker shape.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _target_gate() -> bool:\n"
            "    return True\n\n\n"
            "JOBS = {'x': _ProcessJob(_target_gate, (root,))}\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_target_gate() -> None:\n    assert _target_gate()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_target_gate" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "_target_gate" in v.message for v in violations
        )

    # frob:ticket T-1532
    def test_new_function_never_passed_to_a_job_constructor_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Negative case: the job-table allowance must not blanket-exempt
        # every symbol in a file that happens to mention _ProcessJob -- a
        # genuinely unwired sibling still fires.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _target_gate() -> bool:\n"
            "    return True\n\n\n"
            "def _unwired_gate() -> bool:\n"
            "    return False\n\n\n"
            "JOBS = {'x': _ProcessJob(_target_gate, (root,))}\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_unwired_gate() -> None:\n    assert not _unwired_gate()\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_unwired_gate" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(
            v.rule == "WIRE001" and "_unwired_gate" in v.message for v in violations
        )

    # frob:ticket T-1431
    def test_relocated_symbol_via_file_split_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1431: a LARGE001 file split moves a symbol verbatim into a new
        # file. The diff-scoped hunk proxy sees it as "new" in the new
        # file, but it existed (same body, same name, called only from its
        # own test) at the merge-base under the OLD path -- WIRE001 must
        # not fire.
        from frob.gates._wire import wire_gate

        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_own_obligations_clean() -> None:\n"
            "    assert own_obligations_clean()\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add own_obligations_clean"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        # The "split": delete src/a.py, add the identical symbol under
        # src/pkg/_a.py instead.
        (tmp_path / "src" / "a.py").unlink()
        _write(
            tmp_path,
            "src/pkg/_a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        snap = _snapshot(tmp_path)
        record = next(
            r
            for r in snap.symbols.values()
            if r.id.path == "src/pkg/_a.py" and "own_obligations_clean" in r.symref
        )
        diff = working_diff(tmp_path, "main").danger_ok
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert record.id.path == "src/pkg/_a.py"
        assert not any(
            v.rule == "WIRE001" and "own_obligations_clean" in v.message
            for v in violations
        )

    # frob:ticket T-1431
    def test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1431 acceptance [1]: relocation-awareness must not blanket-
        # exempt a whole new file -- a symbol with no prior existence
        # anywhere at the merge-base still fires, even sitting right next
        # to a relocated one in the same new file.
        from frob.gates._wire import wire_gate

        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "def test_own_obligations_clean() -> None:\n"
            "    assert own_obligations_clean()\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add own_obligations_clean"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        (tmp_path / "src" / "a.py").unlink()
        _write(
            tmp_path,
            "src/pkg/_a.py",
            "def own_obligations_clean() -> bool:\n    return True\n\n\n"
            "def brand_new_helper() -> bool:\n    return False\n",
        )
        snap = _snapshot(tmp_path)
        diff = working_diff(tmp_path, "main").danger_ok
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "own_obligations_clean" in v.message
            for v in violations
        )
        assert any(
            v.rule == "WIRE001" and "brand_new_helper" in v.message for v in violations
        )

    # frob:ticket T-1430
    def test_new_kwonly_param_never_passed_is_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # T-1430 case 4: an EXISTING function (already has a non-test
        # caller, so case 1 never fires) grows a new keyword-only
        # parameter that no call site anywhere passes.
        from frob.gates._wire import wire_gate

        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "from a import own_obligations_clean\n\n\n"
            "def caller() -> bool:\n"
            "    return own_obligations_clean()\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add own_obligations_clean"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean(*, strict: bool = False) -> bool:\n"
            "    return True\n",
        )
        snap = _snapshot(tmp_path)
        diff = working_diff(tmp_path, "main").danger_ok
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "strict" in v.message
        assert v.severity == Severity.ERROR

    # frob:ticket T-1430
    def test_new_kwonly_param_passed_at_call_site_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _git_init(tmp_path)
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean() -> bool:\n    return True\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "from a import own_obligations_clean\n\n\n"
            "def caller() -> bool:\n"
            "    return own_obligations_clean()\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add own_obligations_clean"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(
            tmp_path,
            "src/a.py",
            "def own_obligations_clean(*, strict: bool = False) -> bool:\n"
            "    return True\n",
        )
        _write(
            tmp_path,
            "src/b.py",
            "from a import own_obligations_clean\n\n\n"
            "def caller() -> bool:\n"
            "    return own_obligations_clean(strict=True)\n",
        )
        snap = _snapshot(tmp_path)
        diff = working_diff(tmp_path, "main").danger_ok
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "strict" in v.message for v in violations
        )

    # frob:ticket T-1428
    def test_new_rule_id_missing_from_known_gate_rules_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Reconstructs T-1421's BUG002 shape: a gate emits a rule id string
        # that was never registered in _KNOWN_GATE_RULES.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/gate.py",
            "def test_new_gate() -> object:\n"
            '    return Violation(rule="ZZZQ999", severity=1, file="x", line=1, message="m")\n',
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=(Hunk(file="src/gate.py", span=(1, 2)),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert any(v.rule == "WIRE001" and "ZZZQ999" in v.message for v in violations)

    # frob:ticket T-1428
    def test_new_rule_id_present_in_known_gate_rules_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/gate.py",
            "def new_gate() -> object:\n"
            '    return Violation(rule="DEAD001", severity=1, file="x", line=1, message="m")\n',
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=(Hunk(file="src/gate.py", span=(1, 2)),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "DEAD001" in v.message for v in violations
        )

    # frob:ticket T-1428
    def test_new_cli_dest_missing_from_config_external_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Reconstructs T-1422's shape: argparse parses a flag whose dest
        # never made it into _config_external.py's copy lists.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/frob/_cli_parsers/_misc.py",
            'p.add_argument("--amend", dest="ticket_accept_amend_index")\n',
        )
        _write(tmp_path, "src/frob/app/_config_external.py", "# no fields wired\n")
        snap = _snapshot(tmp_path)
        diff = Diff(
            base="x",
            hunks=(Hunk(file="src/frob/_cli_parsers/_misc.py", span=(1, 1)),),
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "ticket_accept_amend_index" in v.message

    # frob:ticket T-1428
    # frob:ticket T-3149
    def test_new_cli_dest_present_in_config_external_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/frob/_cli_parsers/_misc.py",
            'p.add_argument("--amend", dest="ticket_accept_amend_index")\n',
        )
        _write(
            tmp_path,
            "src/frob/app/_config_external.py",
            # T-3149: must be a real module-level tuple ASSIGNMENT, not a
            # bare orphan string fragment -- _config_external_forwarded_
            # dest_names (T-2348) deliberately only collects literals
            # that are actual elements of an ast.Assign to a
            # tuple/list/set/frozenset(...), so a standalone fragment
            # (this fixture's pre-T-2348 shape) is correctly NOT
            # recognized as wired any more.
            '_STRING_FIELDS = (\n    "ticket_accept_amend_index",\n)\n',
        )
        snap = _snapshot(tmp_path)
        diff = Diff(
            base="x",
            hunks=(Hunk(file="src/frob/_cli_parsers/_misc.py", span=(1, 1)),),
        )
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(
            v.rule == "WIRE001" and "ticket_accept_amend_index" in v.message
            for v in violations
        )

    # frob:ticket T-1428
    def test_wire002_fires_when_follow_up_ticket_missing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive WIRE001 reason="public API, wired later"\n'
            "def own_obligations_clean() -> bool:\n"
            "    return True\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE002")
        assert v is not None
        assert "follow_up" in v.message
        assert v.severity == Severity.ERROR

    # frob:ticket T-1428
    def test_wire002_fires_when_follow_up_ticket_is_closed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive WIRE001 reason="wired later" follow_up="T-0001"\n'
            "def own_obligations_clean() -> bool:\n"
            "    return True\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE002")
        assert v is not None
        assert "T-0001" in v.message

    # frob:ticket T-1428
    def test_wire002_clean_when_follow_up_ticket_is_open(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive WIRE001 reason="wired later" follow_up="T-0001"\n'
            "def own_obligations_clean() -> bool:\n"
            "    return True\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(v.rule == "WIRE002" for v in violations)

    # frob:ticket T-1592
    def test_wire002_clean_when_permanent_true_on_private_test_helper(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """A `permanent="true"` waiver on a private helper (`_`-prefixed)
        under `tests/` needs no `follow_up=` -- the T-1592 fix, exercising
        the live incident's exact shape (`_make_ticket` used only by its
        own file's test methods)."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "tests/unit/test_a.py",
            '# frob:waive WIRE001 reason="private test-seed helper used only by '
            "this file's own test methods -- no production caller by design\" "
            'permanent="true"\n'
            "def _make_ticket() -> str:\n"
            "    return 'x'\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(v.rule == "WIRE002" for v in violations)

    # frob:ticket T-1592
    def test_wire002_still_fires_when_permanent_true_outside_tests_tree(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """`permanent="true"` does NOT satisfy WIRE002 outside `tests/` --
        production code cannot use it to dodge naming a real follow-up."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive WIRE001 reason="internal helper" permanent="true"\n'
            "def _helper() -> bool:\n"
            "    return True\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE002")
        assert v is not None

    # frob:ticket T-1592
    def test_wire002_still_fires_when_permanent_true_on_public_test_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """`permanent="true"` does NOT satisfy WIRE002 for a public (non
        `_`-prefixed) symbol, even under `tests/` -- restricted to private
        helpers only."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "tests/unit/test_a.py",
            '# frob:waive WIRE001 reason="helper" permanent="true"\n'
            "def make_ticket() -> str:\n"
            "    return 'x'\n",
        )
        snap = _snapshot(tmp_path)
        diff = Diff(base="x", hunks=())
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE002")
        assert v is not None

    # frob:ticket T-1725
    def test_wire003_matcher_pattern_stale_verb_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """The regex-matcher shape: a compiled `re.compile(...)` pattern
        naming a verb that no longer exists in the live CLI tree."""
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            ".claude/hooks/frob-timeout-guard.py",
            "import re\n"
            "PATTERN = re.compile(\n"
            '    r"frob +(ticket +(land|totallymadeupverb)|check|test)\\b"\n'
            ")\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add hook"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert any(
            v.rule == "WIRE003" and "totallymadeupverb" in v.message for v in violations
        )
        # Real verbs in the SAME pattern must not be flagged.
        assert not any(
            v.rule == "WIRE003" and "'ticket'" in v.message for v in violations
        )

    # frob:ticket T-1725
    def test_wire003_suggestion_string_stale_verb_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """The prose shape: a backtick-quoted suggestion string inside a
        hook's own refusal text, naming a verb that no longer exists."""
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            ".claude/hooks/frob-suggest.py",
            'MSG = "Use `uv run frob totallynotarealverb` instead."\n',
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add hook"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert any(
            v.rule == "WIRE003" and "totallynotarealverb" in v.message
            for v in violations
        )

    # frob:ticket T-1725
    def test_wire003_real_verbs_are_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/modules/example.md",
            "Run `frob ticket land T-0001` then `frob check`.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add doc"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert violations == []

    # frob:ticket T-1725
    def test_wire003_dotted_module_path_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """`` `frob.tickets._land` `` (a dotted module path mentioning the
        package name) must never be misread as a verb reference -- `.`
        is not a recognized separator, so extraction bails before ever
        reaching a candidate token."""
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            "docs/modules/example.md",
            "See `frob.tickets._land` and `frob-suggest.py` for detail.\n",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add doc"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert violations == []

    # frob:ticket T-3115
    def test_wire003_direct_dispatch_verb_refactor_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::_wire003_live_verb_tokens kind="unit"
        """`refactor` (and its `rename`/`move-module` subcommands) are
        real, working verbs dispatched by `frob.__main__._dispatch`'s raw
        argv scan BEFORE `_build_parser()` runs (T-3115) -- they must
        resolve as live, not be reported as stale just because they never
        reach the argparse tree the normal walk covers."""
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            ".claude/hooks/frob-suggest.py",
            'MSG = "Use `frob refactor rename` or `frob refactor move-module` '
            'instead of a hand edit."\n',
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add hook"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert not any(v.rule == "WIRE003" for v in violations)

    # frob:ticket T-3115
    # frob:waive DUP001 reason="deliberate must-fire/must-stay-quiet fixture pair \
    # sharing the standard _wire003_stale_verb_references test shape \
    # (git_init/_write/commit/assert) every other WIRE003 test in this class already \
    # uses; extracting a shared helper would only hide which assertion belongs to \
    # which scenario"
    def test_wire003_still_flags_a_verb_shaped_like_the_hidden_set(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::_wire003_live_verb_tokens kind="unit"
        """A verb that merely LOOKS like a direct-dispatch verb (same
        shape, never actually registered anywhere -- refactor's own
        `move`/`rename`/`split`/`move-module` real subcommand set, minus
        a fabricated fifth one) must still fire -- the T-3115 fix widens
        what counts as live, it does not turn WIRE003 off for this
        family."""
        from frob.gates._wire import _wire003_stale_verb_references

        _git_init(tmp_path)
        _write(
            tmp_path,
            ".claude/hooks/frob-suggest.py",
            'MSG = "Use `frob refactor totallynotarealsubcommand` instead."\n',
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add hook"], cwd=tmp_path, check=True
        )
        violations = _wire003_stale_verb_references(tmp_path)
        assert any(
            v.rule == "WIRE003" and "totallynotarealsubcommand" in v.message
            for v in violations
        )


# frob:ticket T-2928
class TestWire001DiffScopingMissesPreExistingDeadSymbols:
    """T-2928: measured on a real controlled deletion (T-2900/T-2905, two
    provably dead private helpers), WIRE001 MISSED both -- it never
    fired at all against a symbol with zero real callers. Root cause,
    confirmed here rather than inferred: WIRE001 case 1
    (`_wire001_unwired_symbol_violations`) only ever evaluates
    `_new_callable_records` -- symbols whose ENTIRE span sits inside one
    of THIS diff's added-line hunks (`_new_callable_records`'s own
    docstring: "the proxy this gate uses for 'this diff DEFINED this
    symbol'"). `_parse_bash`/`_parse_csharp` were added under a much
    earlier ticket (T-1604/T-1600); the T-2900/T-2905 diffs that
    measured them touched only a `frob:waive` comment, never the dead
    symbol's own lines, so `_new_callable_records` correctly found no
    matching record and WIRE001 correctly evaluated nothing. This is NOT
    a bug: WIRE001 is deliberately diff-scoped to catch a ticket
    INTRODUCING new dead code (T-1428's own "landed, passed every gate,
    did nothing" defect shape) -- it structurally cannot, and must not
    be made to, retroactively flag code that has been sitting dead since
    a prior ticket. That is DEAD001's job (`frob.gates._dead_symbols`,
    symbol-granularity, unconditional, WARN not ERROR) -- see
    docs/modules/gates.md's WIRE001 entry for the cross-reference this
    ticket added. Not fixable inside WIRE001 without turning it into a
    second, ERROR-severity repeat of DEAD001's own repo-wide scan,
    which is a distinct feature, not a bug fix, and out of this
    ticket's scope."""

    def test_pre_existing_dead_symbol_untouched_by_this_diff_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Reconstructs the T-2900/T-2905 shape directly: `_dead_helper`
        # already exists (zero callers, unrelated to this diff) and this
        # diff's own hunk only touches a DIFFERENT line in the same file
        # (its waiver comment) -- `_dead_helper`'s span is NOT inside the
        # diff's hunks, so `_new_callable_records` never produces a
        # record for it and WIRE001 has nothing to evaluate.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:waive WIRE001 reason="pre-existing, T-2928 fixture"\n'
            "def _dead_helper() -> int:\n"
            "    return 1\n\n"
            "\n"
            "def used() -> int:\n"
            "    return 2\n",
        )
        _write(
            tmp_path,
            "tests/test_a.py",
            "from src.a import used\n\n"
            "def test_used() -> None:\n"
            "    assert used() == 2\n",
        )
        snap = _snapshot(tmp_path)
        # This diff's own hunk covers ONLY the waiver-comment line (line
        # 1), never `_dead_helper`'s own body (lines 2-3) -- the exact
        # T-2900/T-2905 shape (removing/touching the waiver, not the
        # dead symbol itself).
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(1, 1)),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        assert not any(v.rule == "WIRE001" for v in violations), (
            "WIRE001 must stay silent -- _dead_helper's span is not "
            "inside this diff's own hunks, confirming the miss is "
            "WIRE001's deliberate diff-scoping, not a detection bug"
        )

    def test_the_same_dead_symbol_newly_added_by_this_diff_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        # Must-still-fire control: the IDENTICAL dead symbol, this time
        # genuinely introduced by the diff being measured (its span DOES
        # sit inside the diff's hunk) -- WIRE001 fires exactly as
        # designed, proving the prior test's silence is scope, not
        # breakage.
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/a.py",
            "def _dead_helper() -> int:\n    return 1\n",
        )
        snap = _snapshot(tmp_path)
        record = next(r for r in snap.symbols.values() if "_dead_helper" in r.symref)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=record.span),))
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        v = _first_rule(violations, "WIRE001")
        assert v is not None
        assert "_dead_helper" in v.message
        assert v.severity == Severity.ERROR


class TestWire001RuleIdViolationsUnion:
    """T-2454: `_wire001_rule_id_violations` (WIRE001 case 2, T-1421's
    BUG002 shape) is the diff-scoped check that actually serialized this
    ticket's measured incident -- it fires the instant a ticket's OWN
    diff constructs a new `rule="..."` literal, well before land/close
    time, and used to compare only against the hand-maintained
    `_KNOWN_GATE_RULES` literal. It now also recognizes a standard-shape
    construction via a fresh `generated_gate_rule_ids` scan, so a ticket
    adding a brand-new gate rule in its own module never needs to also
    take a write lease on `src/frob/gates/_waive.py` in the same diff."""

    # frob:ticket T-2454
    def test_standard_shape_new_rule_not_flagged_without_hand_registration(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/frob/gates/_new_synthetic_gate.py",
            "def new_synthetic_violation():\n"
            "    return Violation("
            + "rule"
            + '="ZZZTEST034", severity=Severity.ERROR)\n',
        )
        diff = Diff(
            base="x",
            hunks=(Hunk(file="src/frob/gates/_new_synthetic_gate.py", span=(1, 2)),),
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        rule_id_hits = [v for v in violations if "ZZZTEST034" in v.message]
        assert rule_id_hits == []

    # frob:ticket T-2454
    def test_shape_outside_scanned_bases_still_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_wire.py::wire_gate kind="unit"
        """The must-still-refuse control: `rule="..."` constructed
        OUTSIDE `SCANNED_BASES` (`src/frob/gates`, `src/frob/strata`) is
        the disclosed residual `generated_gate_rule_ids` does not cover
        (T-1010's own module docstring) -- still caught here exactly as
        before, proving this ticket did not widen what counts as safely
        auto-known beyond what was already proven."""
        from frob.gates._wire import wire_gate

        _write(
            tmp_path,
            "src/frob/perf/_new_synthetic_check.py",
            "def new_synthetic_violation():\n"
            "    return Violation("
            + "rule"
            + '="ZZZTEST035", severity=Severity.ERROR)\n',
        )
        diff = Diff(
            base="x",
            hunks=(Hunk(file="src/frob/perf/_new_synthetic_check.py", span=(1, 2)),),
        )
        snap = _snapshot(tmp_path)
        queue = TicketQueue(tickets={})
        violations = wire_gate(tmp_path, snap, diff, queue)
        rule_id_hits = [v for v in violations if "ZZZTEST035" in v.message]
        assert len(rule_id_hits) == 1
