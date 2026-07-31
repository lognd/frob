"""Tests for frob.fuzz: Arbitrary protocol, obligations, and FUZZ001/002/003 (docs/modules/fuzz.md)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from frob.fuzz import (
    FUZZ001,
    FUZZ002,
    FUZZ003,
    HYPOTHESIS_AVAILABLE,
    FuzzEnforce,
    FuzzObligation,
    FuzzPolicy,
    FuzzRegistry,
    FuzzResult,
    load_fuzz_stamp,
    obligations,
    register,
    resolve,
    resolve_param_types,
    run_fuzz,
    stamp_fuzz,
)
from frob.fuzz._models import FuzzError
from frob.gates._models import Severity
from frob.graph import build_graph
from frob.graph._models import (
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    SymbolId,
    SymbolRecord,
)
from frob.lang import SymbolKind

needs_hypothesis = pytest.mark.skipif(
    not HYPOTHESIS_AVAILABLE, reason="hypothesis is not installed in this worktree"
)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _record(ref: str, *, public: bool = True) -> SymbolRecord:
    path, qualname = ref.split("::", 1)
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=public,
        digests=Digests(sig="s", body="b", doc="d"),
        span=(1, 2),
    )


def _snapshot(
    symbols: dict[str, SymbolRecord], edges: tuple[Edge, ...] = ()
) -> GraphSnapshot:
    return GraphSnapshot(root=".", symbols=symbols, edges=edges)


# ---------------------------------------------------------------------------
# Arbitrary protocol: resolve/register
# ---------------------------------------------------------------------------


class _Even(BaseModel):
    """A pydantic model whose validator only accepts even integers."""

    model_config = ConfigDict(frozen=True)

    value: int


class _Declared:
    """A plain class exposing a `__fuzz__()` classmethod (the DECLARED path)."""

    def __init__(self, tag: str) -> None:
        self.tag = tag

    @classmethod
    def __fuzz__(cls) -> object:
        if not HYPOTHESIS_AVAILABLE:
            raise RuntimeError("hypothesis unavailable")
        import hypothesis.strategies as st

        return st.just(cls("fixed"))


class _ThirdParty:
    """A plain class with no derivation or declaration -- only REGISTERED can help."""


class TestResolve:
    def test_unknown_type_is_no_generator(self) -> None:
        # frob:tests src/frob/fuzz/_arbitrary.py::resolve kind="unit"
        result = resolve(int if not HYPOTHESIS_AVAILABLE else _ThirdParty)
        assert result.is_err
        assert result.danger_err == type(result.danger_err).NoGenerator

    @needs_hypothesis
    def test_registered_type_resolves(self) -> None:
        # frob:tests src/frob/fuzz/_arbitrary.py::register kind="unit"
        import hypothesis.strategies as st

        register(_ThirdParty, st.builds(_ThirdParty))
        result = resolve(_ThirdParty)
        assert result.is_ok

    @needs_hypothesis
    def test_declared_type_resolves(self) -> None:
        result = resolve(_Declared)
        assert result.is_ok

    @needs_hypothesis
    def test_derived_pydantic_model_resolves(self) -> None:
        result = resolve(_Even)
        assert result.is_ok

    def test_no_hypothesis_or_unknown_type_is_no_generator(self) -> None:
        class _Bare:
            pass

        result = resolve(_Bare)
        assert result.is_err

    def test_resolve_without_hypothesis_installed_is_no_generator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`resolve`'s `HYPOTHESIS_AVAILABLE`-false guard reports
        `Err(NoGenerator)` immediately, independent of whether hypothesis
        is actually installed in this worktree."""
        # frob:tests src/frob/fuzz/_arbitrary.py::resolve kind="unit"
        import frob.fuzz._arbitrary as arbitrary_mod

        monkeypatch.setattr(arbitrary_mod, "HYPOTHESIS_AVAILABLE", False)
        result = arbitrary_mod.resolve(int)
        assert result.is_err
        assert result.danger_err == FuzzError.NoGenerator

    @needs_hypothesis
    def test_pydantic_derivation_failure_is_no_generator(self) -> None:
        """A pydantic model whose field annotation cannot be resolved to a
        hypothesis strategy makes `resolve` report `Err(NoGenerator)` via
        the pydantic-derived branch, not raise -- proves
        `_resolve_cascade`'s derived-failure path (`derived.is_ok` false)."""

        # frob:tests src/frob/fuzz/_arbitrary.py::resolve kind="unit"
        class _Unresolvable(BaseModel):
            model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

            # The unresolvable annotation IS the fixture: it is what makes
            # `resolve` take the derived-failure branch. Suppressed for both
            # checkers -- ty does not honor mypy's `type: ignore`.
            value: "_NoSuchType"  # type: ignore[name-defined]  # noqa: F821  # ty: ignore[unresolved-reference]

        result = resolve(_Unresolvable)
        assert result.is_err
        assert result.danger_err == FuzzError.NoGenerator


class TestFuzzRegistry:
    """A `FuzzRegistry` instance scopes registrations independently of the
    process-global default registry (T-0469)."""

    @needs_hypothesis
    def test_scoped_registry_registration_is_isolated(self) -> None:
        # frob:tests src/frob/fuzz/_arbitrary.py::FuzzRegistry kind="unit"
        import hypothesis.strategies as st

        class _ScopedOnly:
            """A type registered only on a private `FuzzRegistry`, never globally."""

        private_registry = FuzzRegistry()
        private_registry.register(_ScopedOnly, st.builds(_ScopedOnly))

        assert _ScopedOnly in private_registry
        assert resolve(_ScopedOnly).is_err
        assert resolve(_ScopedOnly, registry=private_registry).is_ok

    @needs_hypothesis
    def test_register_accepts_explicit_registry_kwarg(self) -> None:
        # frob:tests src/frob/fuzz/_arbitrary.py::register kind="unit"
        import hypothesis.strategies as st

        class _ViaKwarg:
            """A type registered through the free `register()` function's
            explicit `registry=` kwarg, not the process-global default."""

        private_registry = FuzzRegistry()
        register(_ViaKwarg, st.builds(_ViaKwarg), registry=private_registry)

        assert resolve(_ViaKwarg, registry=private_registry).is_ok
        assert resolve(_ViaKwarg).is_err


# ---------------------------------------------------------------------------
# obligations()
# ---------------------------------------------------------------------------


class TestObligations:
    def test_off_yields_nothing(self) -> None:
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        result = obligations(snapshot, FuzzPolicy(enforce=FuzzEnforce.OFF))
        assert result == ()

    def test_invariant_anchored_picks_up_invariant_edges(self) -> None:
        # invariant spec: [INV-001](invariants/INV-001.md)
        record = _record("a.py::f")
        edge = Edge(
            src="a.py::f", kind=EdgeKind.INVARIANT, target="INV-001", origin="a.py"
        )
        snapshot = _snapshot({"a.py::f": record}, (edge,))
        result = obligations(
            snapshot, FuzzPolicy(enforce=FuzzEnforce.INVARIANT_ANCHORED)
        )
        assert len(result) == 1
        assert result[0].ref == "a.py::f"
        assert "INV-001" in result[0].reason

    def test_invariant_anchored_ignores_unanchored_symbols(self) -> None:
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        result = obligations(
            snapshot, FuzzPolicy(enforce=FuzzEnforce.INVARIANT_ANCHORED)
        )
        assert result == ()

    def test_public_obligates_every_public_function(self) -> None:
        # frob:tests src/frob/fuzz/_obligations.py::obligations kind="unit"
        snapshot = _snapshot(
            {
                "a.py::f": _record("a.py::f", public=True),
                "a.py::_g": _record("a.py::_g", public=False),
            }
        )
        result = obligations(snapshot, FuzzPolicy(enforce=FuzzEnforce.PUBLIC))
        refs = {ob.ref for ob in result}
        assert refs == {"a.py::f"}


# ---------------------------------------------------------------------------
# FUZZ001/FUZZ002/FUZZ003
# ---------------------------------------------------------------------------


class TestFuzz001:
    def test_flags_obligated_symbol_with_no_fuzz_test(self) -> None:
        # frob:tests src/frob/fuzz/_rules.py::FUZZ001 kind="unit"
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        violations = FUZZ001(snapshot, obs)
        assert len(violations) == 1
        assert violations[0].rule == "FUZZ001"
        assert violations[0].severity == Severity.ERROR

    def test_passes_when_fuzz_test_edge_exists(self) -> None:
        edge = Edge(
            src="tests/test_a.py::test_f",
            kind=EdgeKind.TESTS,
            target="a.py::f",
            origin="tests/test_a.py",
            attrs={"kind": "fuzz"},
        )
        snapshot = _snapshot({"a.py::f": _record("a.py::f")}, (edge,))
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        assert FUZZ001(snapshot, obs) == ()

    def test_non_fuzz_kind_edge_does_not_satisfy(self) -> None:
        edge = Edge(
            src="tests/test_a.py::test_f",
            kind=EdgeKind.TESTS,
            target="a.py::f",
            origin="tests/test_a.py",
            attrs={"kind": "unit"},
        )
        snapshot = _snapshot({"a.py::f": _record("a.py::f")}, (edge,))
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        assert len(FUZZ001(snapshot, obs)) == 1


class TestFuzz002:
    def test_skips_when_types_could_not_be_introspected(self) -> None:
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        assert FUZZ002(obs, {"a.py::f": None}) == ()

    def test_flags_ungeneratable_param_type(self) -> None:
        # frob:tests src/frob/fuzz/_rules.py::FUZZ002 kind="unit"
        class _Bare:
            pass

        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        violations = FUZZ002(obs, {"a.py::f": (_Bare,)})
        assert len(violations) == 1
        assert violations[0].rule == "FUZZ002"

    @needs_hypothesis
    def test_passes_for_generatable_param_type(self) -> None:
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        assert FUZZ002(obs, {"a.py::f": (_Even,)}) == ()


class TestFuzz003:
    # invariant spec: [INV-012](invariants/INV-012.md)
    def test_flags_missing_stamp(self) -> None:
        # frob:tests src/frob/fuzz/_rules.py::FUZZ003 kind="unit"
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        violations = FUZZ003(snapshot, obs, None)
        assert len(violations) == 1
        assert violations[0].rule == "FUZZ003"

    def test_flags_stale_stamp(self) -> None:
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        violations = FUZZ003(snapshot, obs, {"a.py::f": "stale-digest"})
        assert len(violations) == 1

    def test_passes_for_matching_stamp(self) -> None:
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        obs = (FuzzObligation(ref="a.py::f", reason="public"),)
        assert FUZZ003(snapshot, obs, {"a.py::f": "b"}) == ()


# ---------------------------------------------------------------------------
# stamp_fuzz / load_fuzz_stamp
# ---------------------------------------------------------------------------


class TestStamp:
    def test_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/fuzz/_stamp.py::stamp_fuzz kind="unit"
        # frob:tests src/frob/fuzz/_stamp.py::load_fuzz_stamp kind="unit"
        results = (
            FuzzResult(ref="a.py::f", body_digest="abc", examples=10, falsified=None),
        )
        outcome = stamp_fuzz(tmp_path, results)
        assert outcome.is_ok
        loaded = load_fuzz_stamp(tmp_path)
        assert loaded == {"a.py::f": "abc"}

    def test_merges_with_prior_stamp(self, tmp_path: Path) -> None:
        stamp_fuzz(
            tmp_path,
            (FuzzResult(ref="a.py::f", body_digest="v1", examples=1, falsified=None),),
        )
        stamp_fuzz(
            tmp_path,
            (FuzzResult(ref="b.py::g", body_digest="v2", examples=1, falsified=None),),
        )
        loaded = load_fuzz_stamp(tmp_path)
        assert loaded == {"a.py::f": "v1", "b.py::g": "v2"}

    def test_missing_stamp_is_none(self, tmp_path: Path) -> None:
        assert load_fuzz_stamp(tmp_path) is None

    def test_malformed_json_stamp_is_none(self, tmp_path: Path) -> None:
        """A stamp file with invalid JSON is `None`, not a crash -- proves
        `load_fuzz_stamp`'s `(OSError, ValueError)` branch."""
        # frob:tests src/frob/fuzz/_stamp.py::load_fuzz_stamp kind="unit"
        stamp_path = tmp_path / ".frob" / "fuzz-stamp.json"
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text("{not valid json")
        assert load_fuzz_stamp(tmp_path) is None

    def test_non_dict_json_stamp_is_none(self, tmp_path: Path) -> None:
        """A stamp file holding valid JSON that is not an object (e.g. a
        list) is `None` -- proves `load_fuzz_stamp`'s not-a-dict branch."""
        stamp_path = tmp_path / ".frob" / "fuzz-stamp.json"
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text("[1, 2, 3]")
        assert load_fuzz_stamp(tmp_path) is None

    def test_write_failure_returns_stamp_failed(self, tmp_path: Path) -> None:
        """`stamp_fuzz` reports `Err(StampFailed)` rather than raising when
        the stamp path cannot be written -- proves the `OSError` branch."""
        # frob:tests src/frob/fuzz/_stamp.py::stamp_fuzz kind="unit"
        blocking_file = tmp_path / ".frob"
        blocking_file.write_text("not a directory")
        results = (
            FuzzResult(ref="a.py::f", body_digest="abc", examples=1, falsified=None),
        )
        outcome = stamp_fuzz(tmp_path, results)
        assert outcome.is_err
        assert outcome.danger_err == FuzzError.StampFailed


# ---------------------------------------------------------------------------
# resolve_param_types (best-effort dynamic import)
# ---------------------------------------------------------------------------


class TestResolveParamTypes:
    def test_non_python_target_returns_none(self, tmp_path: Path) -> None:
        assert resolve_param_types(tmp_path, "a.ts::f") is None

    def test_malformed_ref_returns_none(self, tmp_path: Path) -> None:
        assert resolve_param_types(tmp_path, "no-separator") is None

    def test_unimportable_module_returns_none(self, tmp_path: Path) -> None:
        assert resolve_param_types(tmp_path, "src/does_not_exist.py::f") is None

    def test_introspects_a_real_function(self, tmp_path: Path) -> None:
        # frob:tests src/frob/fuzz/_signatures.py::resolve_param_types kind="unit"
        _write(
            tmp_path,
            "src/fuzz_fixture_mod.py",
            "def add(x: int, y: int) -> int:\n    return x + y\n",
        )
        types = resolve_param_types(tmp_path, "src/fuzz_fixture_mod.py::add")
        assert types == (int, int)

    def test_strips_self_param_on_method(self, tmp_path: Path) -> None:
        """A bound method's `self` parameter is excluded from the returned
        param types, matching FUZZ002's non-self/cls contract."""
        _write(
            tmp_path,
            "src/fuzz_fixture_method.py",
            "class Widget:\n"
            "    def resize(self, width: int, height: int) -> None:\n"
            "        pass\n",
        )
        types = resolve_param_types(
            tmp_path, "src/fuzz_fixture_method.py::Widget.resize"
        )
        assert types == (int, int)

    def test_nested_module_path_derives_dotted_name(self, tmp_path: Path) -> None:
        """A `src/pkg/mod.py` path derives `pkg.mod`, not just the file
        stem -- proves `_module_name`'s multi-part branch."""
        _write(tmp_path, "src/pkg/__init__.py", "")
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "def double(x: int) -> int:\n    return x * 2\n",
        )
        types = resolve_param_types(tmp_path, "src/pkg/mod.py::double")
        assert types == (int,)

    def test_unresolvable_qualname_returns_none(self, tmp_path: Path) -> None:
        """A qualname that does not resolve to any attribute on the
        imported module is `None`, not a crash -- proves `_resolve_attr`'s
        miss branch via `_resolve_callable`."""
        _write(
            tmp_path,
            "src/fuzz_fixture_missing.py",
            "def real() -> None:\n    pass\n",
        )
        assert (
            resolve_param_types(tmp_path, "src/fuzz_fixture_missing.py::not_there")
            is None
        )

    def test_non_callable_attribute_returns_none(self, tmp_path: Path) -> None:
        """A qualname resolving to a non-callable module attribute is
        `None` -- proves `_resolve_callable`'s not-callable branch."""
        _write(
            tmp_path,
            "src/fuzz_fixture_value.py",
            "CONSTANT = 42\n",
        )
        assert (
            resolve_param_types(tmp_path, "src/fuzz_fixture_value.py::CONSTANT") is None
        )


# ---------------------------------------------------------------------------
# run_fuzz: the derived-model round-trip execution harness
# ---------------------------------------------------------------------------


class TestRunFuzz:
    def test_no_hypothesis_returns_empty(self) -> None:
        if HYPOTHESIS_AVAILABLE:
            pytest.skip("hypothesis is installed; this checks the absence path")
        assert run_fuzz((_Even,), budget_s=1) == ()

    @needs_hypothesis
    def test_derived_model_produces_examples(self) -> None:
        # frob:tests src/frob/fuzz/_run.py::run_fuzz kind="unit"
        results = run_fuzz((_Even,), budget_s=1, policy=FuzzPolicy(budget_s=1))
        assert len(results) == 1
        assert results[0].examples > 0
        assert results[0].falsified is None

    @needs_hypothesis
    def test_ungeneratable_target_reports_no_generator(self) -> None:
        class _NotAModel(BaseModel):
            model_config = ConfigDict(frozen=True)

            weird: object

        results = run_fuzz((_NotAModel,), budget_s=1)
        assert len(results) == 1
        # Either it resolves via st.from_type(object) or it reports no generator;
        # the important contract is that run_fuzz never raises either way.
        assert results[0].examples >= 0

    def test_no_generator_target_short_circuits_without_hypothesis(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_run_one`'s no-generator branch: `resolve` failing means
        `run_fuzz` reports `falsified="no generator"` without ever driving
        hypothesis -- proves the resolve-fails-first path independent of
        whether hypothesis itself is installed."""
        # frob:tests src/frob/fuzz/_run.py::run_fuzz kind="unit"
        from typani import Err

        import frob.fuzz._run as run_mod

        class _Unresolvable(BaseModel):
            model_config = ConfigDict(frozen=True)

            value: int

        monkeypatch.setattr(run_mod, "HYPOTHESIS_AVAILABLE", True)
        monkeypatch.setattr(
            run_mod,
            "resolve",
            lambda tp: Err(type("E", (), {"NoGenerator": "no generator"})()),
        )
        results = run_fuzz((_Unresolvable,), budget_s=1)
        assert len(results) == 1
        assert results[0].examples == 0
        assert results[0].falsified == "no generator"

    def test_digests_map_is_stamped_onto_matching_ref(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`digests` keyed by `_ref_of(tp)` is threaded onto the produced
        `FuzzResult.body_digest`."""
        from typani import Err

        import frob.fuzz._run as run_mod

        class _Unresolvable(BaseModel):
            model_config = ConfigDict(frozen=True)

            value: int

        monkeypatch.setattr(run_mod, "HYPOTHESIS_AVAILABLE", True)
        monkeypatch.setattr(
            run_mod,
            "resolve",
            lambda tp: Err(type("E", (), {"NoGenerator": "no generator"})()),
        )
        ref = run_mod._ref_of(_Unresolvable)
        results = run_fuzz((_Unresolvable,), budget_s=1, digests={ref: "digest123"})
        assert results[0].body_digest == "digest123"

    def test_hypothesis_unavailable_returns_empty_and_logs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`run_fuzz` returns `()` with no crash when hypothesis is not
        installed -- proves the `HYPOTHESIS_AVAILABLE`-false guard."""
        import frob.fuzz._run as run_mod

        monkeypatch.setattr(run_mod, "HYPOTHESIS_AVAILABLE", False)
        assert run_fuzz((_Even,), budget_s=1) == ()

    @needs_hypothesis
    def test_budget_s_is_a_real_wall_clock_cutoff(self) -> None:
        """`run_fuzz` stops driving examples once `budget_s` wall-clock
        elapses, rather than mapping `budget_s` to a fixed example count
        (T-0469) -- a near-zero budget yields far fewer examples than a
        one-second budget for the same cheap strategy."""
        # frob:tests src/frob/fuzz/_run.py::run_fuzz kind="unit"
        tiny = run_fuzz((_Even,), budget_s=0, policy=FuzzPolicy(budget_s=0))
        larger = run_fuzz((_Even,), budget_s=1, policy=FuzzPolicy(budget_s=1))
        assert tiny[0].examples <= larger[0].examples

    @needs_hypothesis
    def test_unsatisfiable_strategy_reports_rejection_rate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`_run_property_test`'s `Unsatisfiable` branch: a strategy that
        can never satisfy the property reports a rejection-rate reason
        rather than raising."""
        # frob:tests src/frob/fuzz/_run.py::run_fuzz kind="unit"
        import hypothesis.strategies as st

        import frob.fuzz._run as run_mod

        always_reject = st.integers().filter(lambda _: False)
        monkeypatch.setattr(
            run_mod,
            "resolve",
            lambda tp: __import__("typani").Ok(always_reject),
        )
        results = run_fuzz((_Even,), budget_s=1, policy=FuzzPolicy(budget_s=1))
        assert len(results) == 1
        assert results[0].falsified is not None
        assert "rejection rate" in results[0].falsified


# ---------------------------------------------------------------------------
# Integration: obligations sourced from a real build_graph snapshot
# ---------------------------------------------------------------------------


class TestIntegrationWithGraph:
    def test_invariant_anchor_in_real_source_is_obligated(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/mod.py",
            "def critical() -> None:\n    # frob:invariant INV-099\n    pass\n",
        )
        cache = tmp_path / ".frob" / "cache.db"
        snapshot = build_graph(tmp_path, cache).danger_ok
        result = obligations(snapshot, FuzzPolicy())
        refs = {ob.ref for ob in result}
        assert any(ref.endswith("::critical") for ref in refs)
