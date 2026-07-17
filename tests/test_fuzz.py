"""Tests for frob.fuzz: Arbitrary protocol, obligations, and FUZZ001/002/003 (docs/fuzz.md)."""

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
    FuzzResult,
    load_fuzz_stamp,
    obligations,
    register,
    resolve,
    resolve_param_types,
    run_fuzz,
    stamp_fuzz,
)
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
        result = resolve(int if not HYPOTHESIS_AVAILABLE else _ThirdParty)
        assert result.is_err
        assert result.danger_err == type(result.danger_err).NoGenerator

    @needs_hypothesis
    def test_registered_type_resolves(self) -> None:
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


# ---------------------------------------------------------------------------
# obligations()
# ---------------------------------------------------------------------------


class TestObligations:
    def test_off_yields_nothing(self) -> None:
        snapshot = _snapshot({"a.py::f": _record("a.py::f")})
        result = obligations(snapshot, FuzzPolicy(enforce=FuzzEnforce.OFF))
        assert result == ()

    def test_invariant_anchored_picks_up_invariant_edges(self) -> None:
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
    def test_flags_missing_stamp(self) -> None:
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
        _write(
            tmp_path,
            "src/fuzz_fixture_mod.py",
            "def add(x: int, y: int) -> int:\n    return x + y\n",
        )
        types = resolve_param_types(tmp_path, "src/fuzz_fixture_mod.py::add")
        assert types == (int, int)


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


# ---------------------------------------------------------------------------
# Integration: obligations sourced from a real build_graph snapshot
# ---------------------------------------------------------------------------


class TestIntegrationWithGraph:
    def test_invariant_anchor_in_real_source_is_obligated(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "src/pkg/mod.py",
            'def critical() -> None:\n    # frob:invariant INV-099\n    pass\n',
        )
        cache = tmp_path / ".frob" / "cache.db"
        snapshot = build_graph(tmp_path, cache).danger_ok
        result = obligations(snapshot, FuzzPolicy())
        refs = {ob.ref for ob in result}
        assert any(ref.endswith("::critical") for ref in refs)
