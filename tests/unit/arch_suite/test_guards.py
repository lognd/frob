"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import HAS_ARCH

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")




# frob:ticket T-2539
class TestCaughtTypeNames:
    """`frob.arch._normalized.caught_type_names` (T-2539): a multi-type
    `except (A, B):` clause discharges EVERY member, not just the first
    one `NormalizedCatch.exception_type` can hold."""

    # frob:ticket T-2539
    def test_tuple_clause_reports_every_member(self) -> None:
        # frob:tests src/frob/arch/_normalized.py::caught_type_names kind="unit"
        from frob.arch._normalized import NormalizedCatch, caught_type_names

        assert caught_type_names(
            NormalizedCatch(
                line=1,
                exception_type="OSError",
                exception_types=("OSError", "ValueError"),
            )
        ) == ("OSError", "ValueError")
        assert caught_type_names(NormalizedCatch(line=1, exception_type="OSError")) == (
            "OSError",
        )
        assert caught_type_names(NormalizedCatch(line=1)) == (None,)

    # frob:ticket T-2539
    def test_python_adapter_records_every_tuple_member(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        # T-2539: `_py_except_exception_type` kept the tuple's FIRST member
        # only, so `ValueError` here read as uncaught downstream.
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = tmp_path / "mod.py"
        path.write_text(
            "import json\n"
            "\n"
            "def f(path):\n"
            "    try:\n"
            "        return json.loads(path.read_text())\n"
            "    except (OSError, ValueError):\n"
            "        return None\n"
        )
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok
        module = PythonAdapter().adapt(tree, source, "mod.py")

        catches = module.functions[0].catches
        assert [c.exception_types for c in catches] == [("OSError", "ValueError")]

    # frob:ticket T-2539
    def test_tuple_except_discharges_every_member(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        # A callee's raises ARE subject to the caller's own catches (a
        # function's OWN direct raises are not -- see
        # `_resolve_direct_raises`), so the propagated shape is what a
        # tuple `except` clause has to discharge.
        g = NormalizedFunction(
            name="g",
            line=1,
            body_line_count=3,
            raises=[
                NormalizedRaise(line=2, exception_type="ValueError"),
                NormalizedRaise(line=3, exception_type="OSError"),
            ],
        )
        f = NormalizedFunction(
            name="f",
            line=6,
            body_line_count=3,
            calls=[NormalizedCall(callee="g", line=7)],
            catches=[
                NormalizedCatch(
                    line=8,
                    exception_type="OSError",
                    exception_types=("OSError", "ValueError"),
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[g, f]
        )

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()



# frob:ticket T-2539
class TestSliceSubscriptRaisesNothing:
    """`NormalizedSubscript.is_slice` (T-2539): `xs[a:b]` clamps
    out-of-range bounds instead of raising, so it must not contribute the
    curated `KeyError` default a real index (`d[k]`) does."""

    # frob:ticket T-2539
    def test_python_adapter_marks_slice_subscripts(self, tmp_path: Path) -> None:
        # frob:tests src/frob/arch/_python.py::PythonAdapter.adapt kind="unit"
        from frob.arch._python import PythonAdapter
        from frob.lang import raw_tree

        path = tmp_path / "mod.py"
        path.write_text(
            "def f(lines, start, d, k):\n"
            "    tail = lines[start + 1 :]\n"
            "    value = d[k]\n"
            "    return tail, value\n"
        )
        parsed = raw_tree(path)
        assert parsed.is_ok
        tree, source, _language = parsed.danger_ok
        module = PythonAdapter().adapt(tree, source, "mod.py")

        flags = sorted(s.is_slice for s in module.functions[0].subscripts)
        assert flags == [False, True]

    # frob:ticket T-2539
    def test_slice_only_function_leaks_no_key_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedSubscript,
        )

        sliced = NormalizedFunction(
            name="sliced",
            line=1,
            body_line_count=2,
            subscripts=[NormalizedSubscript(line=2, is_slice=True)],
        )
        indexed = NormalizedFunction(
            name="indexed",
            line=5,
            body_line_count=2,
            subscripts=[NormalizedSubscript(line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[sliced, indexed]
        )

        result = compute_may_raise(module)
        assert result["pkg/mod.py::sliced"].raises == frozenset()
        # T-2543 (A2): an index contributes `LookupError`, the parent of
        # both KeyError and IndexError -- see TestSubscriptProvenance.
        assert result["pkg/mod.py::indexed"].raises == frozenset({"LookupError"})


# frob:ticket T-2552
class TestBuiltinRaiserPrecision:
    """`frob.arch._mayraise._BUILTIN_RAISERS` (T-2552): the curated table
    must not attribute an exception the call provably cannot raise --
    EXHAUST002 demanding a handler for an impossible path is the
    false-positive direction whose cheapest fix is the blanket `except
    Exception:` the gate family exists to prevent."""

    # frob:ticket T-2552
    def test_int_does_not_contribute_type_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `int(x)` raises TypeError only when x is not string/number-shaped
        # at all -- a STATIC type error the `ty` gate owns and reports at
        # ERROR severity, and one this resolver cannot narrow (it has no
        # None-guard flow analysis). ValueError, the genuine runtime input
        # condition, stays.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(callee="int", line=2, args=[NormalizedCallArg(index=0)])
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError"}
        )

    # frob:ticket T-2552
    def test_getattr_with_default_raises_nothing(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `getattr(o, name, default)` returns the default instead of
        # raising; the two-argument form still can.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        three = NormalizedFunction(
            name="three",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="getattr",
                    line=2,
                    args=[NormalizedCallArg(index=i) for i in range(3)],
                )
            ],
        )
        two = NormalizedFunction(
            name="two",
            line=5,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="getattr",
                    line=6,
                    args=[NormalizedCallArg(index=i) for i in range(2)],
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[three, two]
        )

        result = compute_may_raise(module)
        assert result["pkg/mod.py::three"].raises == frozenset()
        assert result["pkg/mod.py::two"].raises == frozenset({"AttributeError"})

    # frob:ticket T-2552
    def test_next_with_default_raises_no_stop_iteration(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="next",
                    line=2,
                    args=[NormalizedCallArg(index=0), NormalizedCallArg(index=1)],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()


# frob:ticket T-2568
class TestIsdigitGuardDischarge:
    """`frob.arch._mayraise._isdigit_guard_discharges` (T-2568): a
    preceding `.isdigit()` guard on `int(x)`/`float(x)`'s own argument
    expression rules out the `ValueError` the unguarded call would
    otherwise contribute -- the guard-predicate class that was, at T-2568
    filing, this repo's ENTIRE EXHAUST002 corpus (all 8 findings named
    `entry.name.isdigit()`-shaped guards)."""

    # frob:ticket T-2568
    def test_guarded_int_call_discharges_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `if not entry.name.isdigit(): continue` / `int(entry.name)` --
        # the exact shape every real finding in the corpus used.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=4,
            branches=[
                NormalizedBranch(line=2, condition_text="not entry.name.isdigit()")
            ],
            calls=[
                NormalizedCall(
                    callee="int",
                    line=4,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()

    # frob:ticket T-2568
    def test_unguarded_int_call_still_raises_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # No preceding branch at all -- `int(x)` on an unguarded string
        # must still be reported; T-2552's own doctrine (this ticket must
        # not weaken `_BUILTIN_RAISERS` for `int`/`float`) stays enforced
        # for the unguarded case.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="int",
                    line=2,
                    args=[NormalizedCallArg(index=0, text="raw")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError"}
        )

    # frob:ticket T-2568
    def test_guard_several_unrelated_branches_before_the_call_still_discharges(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The real corpus shape: `if not entry.name.isdigit(): continue`,
        # then one or more UNRELATED branches (a nested try/except's own
        # `if`) before int() is finally called. A plain "nearest preceding
        # branch of any kind" proxy would pick the unrelated branch and
        # never discharge -- this must filter to isdigit-matching branches
        # FIRST, then take the nearest among those.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=6,
            branches=[
                NormalizedBranch(line=2, condition_text="not entry.name.isdigit()"),
                NormalizedBranch(line=4, condition_text="cwd == resolved"),
            ],
            calls=[
                NormalizedCall(
                    callee="int",
                    line=6,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()

    # frob:ticket T-2568
    def test_isdigit_guard_on_a_different_expression_does_not_discharge(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The guard exists but names a DIFFERENT expression than the one
        # passed to int() -- must not discharge (the guard's precondition
        # covers a different value, so int()'s ValueError genuinely can
        # still occur).
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=4,
            branches=[NormalizedBranch(line=2, condition_text="other.isdigit()")],
            calls=[
                NormalizedCall(
                    callee="int",
                    line=4,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError"}
        )


# frob:ticket T-3473
class TestRegexGroupGuardDischarge:
    """`frob.arch._mayraise._regex_group_guard_discharges` (T-3473): a
    module-level `re.compile(PATTERN)` constant's own provably digit-only
    capture group, read via `match.group(N)` after an `if match is None:
    return` guard, rules out the `ValueError` `int()`/`float()` would
    otherwise contribute -- the corpus shape T-2568's isdigit-guard fix
    could not reach (`scripts/_require_python.py::_required_version`,
    `scripts/wait_for_land_slot.py::probe_lands_in_flight`)."""

    # frob:ticket T-3473
    def test_digit_only_group_after_none_guard_discharges_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `_required_version`'s own shape: `match = PATTERN.search(text)`,
        # `if match is None: return None`, `int(match.group(1))`.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=5,
            calls=[
                NormalizedCall(callee="_PATTERN.search", line=2),
                NormalizedCall(
                    callee="int",
                    line=4,
                    args=[NormalizedCallArg(index=0, text="match.group(1)")],
                ),
            ],
            branches=[NormalizedBranch(line=3, condition_text="match is None")],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[f],
            module_regex_patterns={"_PATTERN": r"(\d+)"},
        )

        # T-3473: the ValueError contribution from int()'s digit-only
        # group is discharged; "Unknown" remains because the resolver
        # cannot resolve _PATTERN.search itself (an unrelated, separate
        # resolution-coverage gap, not this fix's concern).
        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"Unknown"}
        )

    # frob:ticket T-3473
    def test_non_digit_group_still_raises_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Same shape, but the compiled pattern's group 1 is NOT digit-only
        # (`\w+`) -- int() can genuinely still raise, must not discharge.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=5,
            calls=[
                NormalizedCall(callee="_PATTERN.search", line=2),
                NormalizedCall(
                    callee="int",
                    line=4,
                    args=[NormalizedCallArg(index=0, text="match.group(1)")],
                ),
            ],
            branches=[NormalizedBranch(line=3, condition_text="match is None")],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[f],
            module_regex_patterns={"_PATTERN": r"(\w+)"},
        )

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError", "Unknown"}
        )

    # frob:ticket T-3473
    def test_missing_none_guard_still_raises_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The pattern is digit-only but there is no "match is None" guard
        # branch at all -- must not discharge (int() can still see a
        # None.group() AttributeError-adjacent path this resolver has no
        # visibility into, so the ValueError contribution stays reported
        # fail-closed).
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(callee="_PATTERN.search", line=2),
                NormalizedCall(
                    callee="int",
                    line=3,
                    args=[NormalizedCallArg(index=0, text="match.group(1)")],
                ),
            ],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[f],
            module_regex_patterns={"_PATTERN": r"(\d+)"},
        )

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError", "Unknown"}
        )

    # frob:ticket T-3473
    def test_ambiguous_regex_call_candidates_does_not_discharge(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Two DIFFERENT module-level patterns both get `.search()`'d in the
        # same function -- this resolver has no def-use binding of `match`
        # to either one, so it must fail closed rather than guess.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=6,
            calls=[
                NormalizedCall(callee="_PATTERN_A.search", line=2),
                NormalizedCall(callee="_PATTERN_B.search", line=3),
                NormalizedCall(
                    callee="int",
                    line=5,
                    args=[NormalizedCallArg(index=0, text="match.group(1)")],
                ),
            ],
            branches=[NormalizedBranch(line=4, condition_text="match is None")],
        )
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            functions=[f],
            module_regex_patterns={
                "_PATTERN_A": r"(\d+)",
                "_PATTERN_B": r"(\d+)",
            },
        )

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError", "Unknown"}
        )

    # frob:ticket T-3473
    def test_real_require_python_corpus_site_has_no_leaked_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # End-to-end via the real python adapter over the real corpus
        # site's own source shape (both groups digit-only, two int() calls
        # sharing one guard) -- the actual finding this ticket closes.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._python import PythonAdapter
        from frob.lang import get_parser

        src = (
            b"import re\n\n"
            b"_RE = re.compile(r'requires-python\\s*=\\s*\"[^\\d]*(\\d+)\\.(\\d+)')\n\n"
            b"def f(text):\n"
            b"    match = _RE.search(text)\n"
            b"    if match is None:\n"
            b"        return None\n"
            b"    return (int(match.group(1)), int(match.group(2)))\n"
        )
        tree = get_parser("python").parse(src)
        module = PythonAdapter().adapt(tree, src, "pkg/mod.py")

        # T-3473: no ValueError leak; "Unknown" remains from the
        # unresolved _RE.search call itself (unrelated resolution gap).
        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"Unknown"}
        )


# frob:ticket T-3474
class TestComprehensionGuardOrdering:
    """`frob.arch._mayraise._isdigit_guard_discharges`'s T-3474 extension:
    a comprehension's `if`-clause is written AFTER its own leading (output)
    expression but evaluates BEFORE it runs each iteration --
    `comprehension_id` correlation discharges that shape without a line-
    order requirement; two DIFFERENT comprehensions, or a comprehension
    branch against a NON-comprehension call, still fail closed."""

    # frob:ticket T-3474
    def test_trailing_if_clause_discharges_its_own_leading_expression(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `reap_orphaned_forkservers`'s own shape: `[int(entry.name) for
        # entry in entries if entry.name.isdigit() and ...]` -- the
        # output expr's own int() call sits at a LOWER line than its
        # guarding if-clause, same comprehension_id on both.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(
                    callee="int",
                    line=2,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                    comprehension_id=1,
                )
            ],
            branches=[
                NormalizedBranch(
                    line=4,
                    condition_text="entry.name.isdigit()",
                    comprehension_id=1,
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()

    # frob:ticket T-3474
    def test_different_comprehension_ids_do_not_discharge(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Two SEPARATE comprehensions in one function -- the guard in one
        # must not be credited to the other's output expression.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=6,
            calls=[
                NormalizedCall(
                    callee="int",
                    line=2,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                    comprehension_id=1,
                )
            ],
            branches=[
                NormalizedBranch(
                    line=6,
                    condition_text="entry.name.isdigit()",
                    comprehension_id=2,
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset(
            {"ValueError"}
        )

    # frob:ticket T-3474
    def test_comprehension_branch_does_not_discharge_a_non_comprehension_call(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The guard branch carries a comprehension_id but the LATER call
        # is plain code (comprehension_id=None) -- ordinary line-order
        # rules still apply and are satisfied here (branch precedes call),
        # so this one DOES discharge, exercising the "or" path's other arm
        # staying correct rather than accidentally always-true.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedBranch,
            NormalizedCall,
            NormalizedCallArg,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=4,
            branches=[
                NormalizedBranch(
                    line=2,
                    condition_text="entry.name.isdigit()",
                    comprehension_id=1,
                )
            ],
            calls=[
                NormalizedCall(
                    callee="int",
                    line=4,
                    args=[NormalizedCallArg(index=0, text="entry.name")],
                )
            ],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        assert compute_may_raise(module)["pkg/mod.py::f"].raises == frozenset()

    # frob:ticket T-3474
    def test_real_proc_scan_corpus_site_has_no_leaked_value_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # End-to-end via the real python adapter over the real corpus
        # site's own source shape.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._python import PythonAdapter
        from frob.lang import get_parser

        src = (
            b"def f(entries):\n"
            b"    return [\n"
            b"        int(entry.name)\n"
            b"        for entry in entries\n"
            b"        if entry.name.isdigit() and other(int(entry.name))\n"
            b"    ]\n"
        )
        tree = get_parser("python").parse(src)
        module = PythonAdapter().adapt(tree, src, "pkg/mod.py")

        result = compute_may_raise(module)["pkg/mod.py::f"]
        assert "ValueError" not in result.raises


# frob:ticket T-2543
class TestSubscriptProvenance:
    """`FunctionMayRaise.subscript_derived` (T-2543, A2+A4): the resolver
    names an unresolved-shape subscript's raise `LookupError` -- the type
    it actually knows -- and reports, exactly, which leaked types exist
    ONLY because of that rule, so the gate can split by confidence rather
    than by matching a type name."""

    # frob:ticket T-2543
    def test_subscript_raises_lookup_error_not_key_error(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # A2: the model cannot tell a mapping index (KeyError) from a
        # sequence index (IndexError); LookupError is their common parent
        # and is what it genuinely knows.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedSubscript,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=2,
            subscripts=[NormalizedSubscript(line=2)],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        result = compute_may_raise(module)["pkg/mod.py::f"]
        assert result.raises == frozenset({"LookupError"})
        assert result.subscript_derived == frozenset({"LookupError"})

    # frob:ticket T-2543
    def test_subscript_provenance_propagates_through_callees(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # A caller that never indexes anything itself, but calls something
        # that does, is still subscript-derived -- the suppressed pass runs
        # the same callee fixpoint, so provenance is transitive.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedSubscript,
        )

        helper = NormalizedFunction(
            name="helper",
            line=1,
            body_line_count=2,
            subscripts=[NormalizedSubscript(line=2)],
        )
        caller = NormalizedFunction(
            name="caller",
            line=5,
            body_line_count=2,
            calls=[NormalizedCall(callee="helper", line=6)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[helper, caller]
        )

        result = compute_may_raise(module)["pkg/mod.py::caller"]
        assert result.raises == frozenset({"LookupError"})
        assert result.subscript_derived == frozenset({"LookupError"})

    # frob:ticket T-2543
    def test_type_with_a_confirmed_source_is_not_subscript_derived(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Reachable by BOTH a subscript and an own raise -> it has a
        # confirmed non-subscript source, so it stays the higher-confidence
        # signal and must NOT be demoted.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
            NormalizedSubscript,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=3,
            raises=[NormalizedRaise(line=2, exception_type="LookupError")],
            subscripts=[NormalizedSubscript(line=3)],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        result = compute_may_raise(module)["pkg/mod.py::f"]
        assert "LookupError" in result.raises
        assert result.subscript_derived == frozenset()

    # frob:ticket T-2543
    def test_slice_only_function_has_no_subscript_provenance(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedFunction,
            NormalizedModule,
            NormalizedSubscript,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=2,
            subscripts=[NormalizedSubscript(line=2, is_slice=True)],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        result = compute_may_raise(module)["pkg/mod.py::f"]
        assert result.raises == frozenset()
        assert result.subscript_derived == frozenset()


# frob:ticket T-0686
class TestMayRaiseResolver:
    """`frob.arch._mayraise.compute_may_raise` (T-0686, child 1 of T-0685):
    per-function may-raise sets over `NormalizedModule` -- own raise sites
    + builtin-raiser table + same-module callee-graph fixpoint, except
    clauses subtracting what they discharge, unresolved callees/raises
    fail-closed to `UNKNOWN`."""

    # frob:ticket T-0686
    def test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # Ticket acceptance fixture: f -> g -> h where h raises ValueError,
        # g catches it (so g's own visible raises is empty), and f itself
        # indexes a subscript and separately calls g (whose raise is fully
        # discharged) -- f's own may-raise set must be exactly the
        # subscript rule's contribution.
        # T-2543 (A2): that contribution is now `LookupError`, not
        # `KeyError`. The model cannot tell a mapping index from a sequence
        # index without a resolved type, so it names their common parent --
        # what it genuinely knows -- instead of picking one child and being
        # wrong in both directions (KeyError claimed at list-indexing
        # sites, IndexError never reported at all).
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
            NormalizedSubscript,
        )

        h = NormalizedFunction(
            name="h",
            line=1,
            body_line_count=2,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
        )
        g = NormalizedFunction(
            name="g",
            line=5,
            body_line_count=4,
            calls=[NormalizedCall(callee="h", line=7)],
            catches=[NormalizedCatch(line=8, exception_type="ValueError")],
        )
        f = NormalizedFunction(
            name="f",
            line=12,
            body_line_count=3,
            calls=[NormalizedCall(callee="g", line=13)],
            subscripts=[NormalizedSubscript(line=14)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[h, g, f]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::h"].raises == frozenset({"ValueError"})
        assert result["pkg/mod.py::g"].raises == frozenset()
        assert result["pkg/mod.py::f"].raises == frozenset({"LookupError"})

    # frob:ticket T-1636
    def test_qualified_except_clause_discharges_bare_named_leak(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # T-1636: `except json.JSONDecodeError:` must discharge a
        # leaked bare "JSONDecodeError" (the shape every raiser table in
        # this module attributes) -- before the fix, `_catches` compared
        # the qualified caught text "json.JSONDecodeError" against the bare
        # raised text and never matched, so a function that genuinely
        # catches a qualified exception type still reported it as leaked.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=3,
            calls=[NormalizedCall(callee="json.loads", line=2)],
            catches=[NormalizedCatch(line=3, exception_type="json.JSONDecodeError")],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        result = compute_may_raise(module)

        assert result["pkg/mod.py::f"].raises == frozenset()

    # frob:ticket T-1636
    def test_bare_reraise_of_qualified_catch_type_is_normalized(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # T-1636: a bare `raise` re-raising a qualified caught
        # type (`except json.JSONDecodeError:` ... `raise`) must resolve
        # to the BARE name "JSONDecodeError", matching every raiser
        # table's own bare-name convention -- an unnormalized qualified
        # name here would never match a `# frob:raises JSONDecodeError`
        # directive or a caller's own bare-named catch.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        f = NormalizedFunction(
            name="f",
            line=1,
            body_line_count=3,
            catches=[NormalizedCatch(line=2, exception_type="json.JSONDecodeError")],
            raises=[NormalizedRaise(line=3, exception_type=None)],
        )
        module = NormalizedModule(path="pkg/mod.py", language="python", functions=[f])

        result = compute_may_raise(module)

        assert result["pkg/mod.py::f"].raises == frozenset({"JSONDecodeError"})

    # frob:ticket T-0686
    def test_unresolvable_call_yields_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="dispatch",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="plugin_hook", line=2)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::dispatch"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0686
    def test_bare_reraise_resolves_to_caught_type(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="reraiser",
            line=1,
            body_line_count=5,
            catches=[NormalizedCatch(line=2, exception_type="KeyError")],
            raises=[NormalizedRaise(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::reraiser"].raises == frozenset({"KeyError"})

    # frob:ticket T-0686
    def test_bare_except_reraise_is_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCatch,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        func = NormalizedFunction(
            name="reraiser",
            line=1,
            body_line_count=5,
            catches=[NormalizedCatch(line=2, exception_type=None)],
            raises=[NormalizedRaise(line=3, exception_type=None)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[func]
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::reraiser"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0686
    def test_recursive_cycle_converges(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # a <-> b mutual recursion: a raises ValueError, b calls a and a
        # calls b -- the fixpoint must terminate and both must see
        # ValueError in their visible set (no catch discharges it).
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        a = NormalizedFunction(
            name="a",
            line=1,
            body_line_count=3,
            raises=[NormalizedRaise(line=2, exception_type="ValueError")],
            calls=[NormalizedCall(callee="b", line=3)],
        )
        b = NormalizedFunction(
            name="b",
            line=6,
            body_line_count=2,
            calls=[NormalizedCall(callee="a", line=7)],
        )
        module = NormalizedModule(
            path="pkg/mod.py", language="python", functions=[a, b]
        )

        result = compute_may_raise(module)

        assert "ValueError" in result["pkg/mod.py::a"].raises
        assert "ValueError" in result["pkg/mod.py::b"].raises

    # frob:ticket T-0686
    def test_ambiguous_method_name_across_classes_is_unresolved(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedClass,
            NormalizedFunction,
            NormalizedModule,
            NormalizedRaise,
        )

        run_a = NormalizedFunction(name="run", line=2, body_line_count=1, raises=[])
        run_b = NormalizedFunction(
            name="run",
            line=12,
            body_line_count=1,
            raises=[NormalizedRaise(line=13, exception_type="ValueError")],
        )
        caller = NormalizedFunction(
            name="dispatch",
            line=20,
            body_line_count=2,
            calls=[NormalizedCall(callee="run", line=21)],
        )
        cls_a = NormalizedClass(name="A", line=1, methods=[run_a])
        cls_b = NormalizedClass(name="B", line=11, methods=[run_b])
        module = NormalizedModule(
            path="pkg/mod.py",
            language="python",
            classes=[cls_a, cls_b],
            functions=[caller],
        )

        result = compute_may_raise(module)

        assert result["pkg/mod.py::dispatch"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0689
    def test_undeclared_ctypes_style_call_is_unknown(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # A call into a ctypes/cffi-loaded handle (`lib.some_c_function(...)`)
        # is not a same-module function and not in either curated raiser
        # table -- opaque boundary, fail-closed to Unknown (T-0689's
        # acceptance criterion, first half).
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[NormalizedCall(callee="lib.some_c_function", line=2)],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset({UNKNOWN})

    # frob:ticket T-0689
    def test_declared_raises_substitutes_for_opaque_boundary_call(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # The SAME opaque ctypes-style call as the previous test, but now
        # carrying a `frob:callee-raises` declaration (NormalizedCall.
        # declared_raises, renamed from `frob:raises` by T-0931) -- the
        # declared set substitutes for Unknown
        # (T-0689's acceptance criterion, second half).
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="lib.some_c_function",
                    line=2,
                    declared_raises=frozenset({"OSError"}),
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset({"OSError"})
        assert UNKNOWN not in result["pkg/native.py::call_native"].raises

    # frob:ticket T-0689
    def test_declared_raises_empty_set_is_honored_not_treated_as_absent(
        self,
    ) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # `declared_raises=frozenset()` ("declared to raise nothing", the
        # valid errno-convention shape) must NOT fall through to Unknown --
        # callers check `is not None`, never truthiness.
        from frob.arch._mayraise import compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="call_native",
            line=1,
            body_line_count=2,
            calls=[
                NormalizedCall(
                    callee="lib.errno_style_call",
                    line=2,
                    declared_raises=frozenset(),
                )
            ],
        )
        module = NormalizedModule(
            path="pkg/native.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        assert result["pkg/native.py::call_native"].raises == frozenset()

    # frob:ticket T-0689
    def test_curated_stdlib_c_extension_table_resolves_precisely(self) -> None:
        # frob:tests src/frob/arch/_mayraise.py::compute_may_raise kind="unit"
        # json.loads/sqlite3.connect/struct.pack are curated stdlib
        # C-extension raisers (T-0689's user mandate) -- resolved
        # precisely, not Unknown, keyed on the full dotted callee text.
        from frob.arch._mayraise import UNKNOWN, compute_may_raise
        from frob.arch._normalized import (
            NormalizedCall,
            NormalizedFunction,
            NormalizedModule,
        )

        caller = NormalizedFunction(
            name="parse_all",
            line=1,
            body_line_count=4,
            calls=[
                NormalizedCall(callee="json.loads", line=2),
                NormalizedCall(callee="sqlite3.connect", line=3),
                NormalizedCall(callee="struct.pack", line=4),
            ],
        )
        module = NormalizedModule(
            path="pkg/parse.py", language="python", functions=[caller]
        )

        result = compute_may_raise(module)

        raises = result["pkg/parse.py::parse_all"].raises
        assert raises == frozenset({"JSONDecodeError", "sqlite3.Error", "struct.error"})
        assert UNKNOWN not in raises
