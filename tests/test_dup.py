"""T-0447: R3 canonicalization (literal abstraction + `elif` control-flow
desugar) and a real cross-language dup litmus fixture.

Before this ticket `r3_canonical_hash` (`frob-core/src/lib.rs`) folded the
exact same R2-normalized token stream R2 hashes -- `docs/modules/dup.md`
and `frob.dup._exhaustiveness.DUP_MATRIX_EXCUSES` both recorded this as a
real doc/implementation drift (T-0199 finding): no fixture could isolate
an R3-only fire from R2. `r3_canonicalize` (frob-core/src/lib.rs) closes
two of the three named gaps with real, tractable-without-an-AST token
transforms:

- literal abstraction: numeric/string-literal-shaped tokens collapse to a
  shared placeholder per kind.
- `elif` control-flow desugar: `elif` is real syntactic sugar for
  `else: if` (true in every grammar with an `elif` keyword) -- expanded to
  three tokens before folding.

Commutative-operand reordering and real for/while loop-shape desugaring
still need actual AST structure (not a token fold) and remain future work
(`frob:todo T-0001`, `docs/modules/dup.md`'s R3 deviations note) -- not
claimed fixed here.

The cross-language section proves R5 (Weisfeiler-Lehman hash over the
REAL def-use/control-flow graph, `_real_dataflow_graph`) already fires
cross-language for a structurally-identical function, unlike R1/R2/R3
which bucket on literal token vocabulary the grammars do not share (see
`tests/test_dup_cross_lang.py`'s characterization of that R1/R2/R3 limit).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones
from frob.dup import _core as dup_core
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    """Write `source` to `tmp_path/name` (test helper, mirrors
    tests/test_dup_r5_multilang.py's `_write`)."""
    path = tmp_path / name
    path.write_text(source)
    return path


def _rungs_for(report, left_needle: str, right_needle: str) -> set[str]:
    """Every rung that grouped a pair matching `left_needle`/`right_needle`
    (in either left/right order) across `report.groups` (test helper)."""
    out: set[str] = set()
    for group in report.groups:
        for pair in group.pairs:
            names = {pair.left.ref, pair.right.ref}
            if any(left_needle in n for n in names) and any(
                right_needle in n for n in names
            ):
                out.add(pair.rung)
    return out


class TestR3LiteralAbstraction:
    """R2 misses / R3 catches: two functions identical in shape, differing
    only by a numeric literal. R2's `_r2_normalize` alpha-renames
    identifiers only -- literal tokens pass through unchanged, so R2's hash
    differs. R3's literal abstraction collapses both literals to the same
    placeholder, so R3 independently groups the pair."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "mod_lit.py",
            "def offset_by_one(x):\n"
            "    return x + 1\n"
            "\n"
            "\n"
            "def offset_by_two(x):\n"
            "    return x + 2\n"
            "\n"
            "\n"
            "def offset_by_subtracting(x):\n"
            "    return x - 1\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r3_fires_where_r2_does_not(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=3, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "offset_by_one", "offset_by_two")
        assert "r2" not in rungs, (
            "r2 should NOT bucket a literal-only difference (it does not "
            f"abstract literals); got rungs={rungs}"
        )
        assert "r3" in rungs, (
            f"expected r3 to independently fire on the literal-abstracted "
            f"pair; got rungs={rungs}"
        )

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r3_does_not_collapse_a_different_operator(self, snapshot):
        # Negative pair: `x - 1` differs from `x + 1` by operator, not
        # literal -- literal abstraction must not paper over that.
        report = find_clones(
            snapshot, DupConfig(min_tokens=3, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "offset_by_one", "offset_by_subtracting")
        assert "r3" not in rungs, (
            f"r3 must not merge a different-operator pair via literal "
            f"abstraction; got rungs={rungs}"
        )


class TestR3ElifDesugar:
    """R2 misses / R3 catches: an `if/elif/else` chain and its manually
    nested `if/else: if/else` equivalent. `elif` is real syntactic sugar
    for `else: if` -- R3's desugar expands it before folding so the two
    spellings hash identically; R2 (no desugar) sees different tokens."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "mod_elif.py",
            "def classify_with_elif(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    elif x < 0:\n"
            "        return 2\n"
            "    else:\n"
            "        return 3\n"
            "\n"
            "\n"
            "def classify_nested(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    else:\n"
            "        if x < 0:\n"
            "            return 2\n"
            "        else:\n"
            "            return 3\n"
            "\n"
            "\n"
            "def classify_different_condition(x):\n"
            "    if x > 0:\n"
            "        return 1\n"
            "    elif x <= 0:\n"
            "        return 2\n"
            "    else:\n"
            "        return 3\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r3_fires_where_r2_does_not(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=3, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "classify_with_elif", "classify_nested")
        assert "r2" not in rungs, (
            "r2 should NOT bucket elif vs manually-nested if/else (no "
            f"control-flow desugar); got rungs={rungs}"
        )
        assert "r3" in rungs, (
            f"expected r3 to independently fire on the elif-desugared "
            f"pair; got rungs={rungs}"
        )

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r3_does_not_collapse_a_different_condition(self, snapshot):
        # Negative pair: the elif branch tests a different condition
        # (`<=` vs `<`) -- desugar must not paper over that.
        report = find_clones(
            snapshot, DupConfig(min_tokens=3, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "classify_with_elif", "classify_different_condition")
        assert "r3" not in rungs, (
            f"r3 must not merge a different-condition elif chain via "
            f"control-flow desugar; got rungs={rungs}"
        )


class TestCrossLanguageR5Litmus:
    """T-0199 gap: no cross-language dup litmus fixture existed proving ANY
    rung fires across grammars (`tests/test_dup_cross_lang.py` proves the
    NEGATIVE for R1/R2/R3 -- lexical token vocabulary never aligns across
    grammars). R5's WL-hash operates on `_real_dataflow_graph`'s pure
    "def"/"use" structural labels + adjacency -- no literal token identity
    involved -- so a structurally-identical function (same statement
    shape, same def/use pattern) written once in Python and once in Rust
    DOES collide at R5, independent of R1/2/3's lexical miss.

    The fixture is deliberately a single bare `return a + b` (no local
    `let`/assignment), isolating the claim this class proves (R5 fires
    cross-language because its labels are structural, not lexical) from
    the separate `let`-as-identifier gap `TestCrossLanguageR5WithLet`
    (T-0487) now covers directly with a fixture that DOES declare a local
    binding."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "add.py",
            "def sum_py(a, b):\n    return a + b\n",
        )
        _write(
            tmp_path,
            "add.rs",
            "fn sum_rs(a: i32, b: i32) -> i32 {\n    return a + b;\n}\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_both_languages_parse_into_the_snapshot(self, snapshot):
        refs = set(snapshot.symbols)
        assert any("sum_py" in r for r in refs)
        assert any("sum_rs" in r for r in refs)

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r5_fires_across_languages(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=1, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "sum_py", "sum_rs")
        assert "r5" in rungs, (
            f"expected r5 (structural def-use graph) to fire across "
            f"python/rust for a structurally-identical function; got "
            f"rungs={rungs}, groups={report.groups!r}"
        )

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0447
    def test_r1_r2_r3_do_not_fire_across_languages(self, snapshot):
        # Characterizes the known lexical-vocabulary limit for the
        # token-bucketed rungs (same posture as test_dup_cross_lang.py) --
        # the R5 fire above is real BECAUSE it does not depend on token
        # vocabulary, not because the pipeline stopped honoring that limit.
        report = find_clones(
            snapshot, DupConfig(min_tokens=1, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "sum_py", "sum_rs")
        assert rungs.isdisjoint({"r1", "r2", "r3"}), (
            f"r1/r2/r3 bucket on literal token vocabulary the python/rust "
            f"grammars do not share; unexpected fire: {rungs}"
        )


class TestCrossLanguageR5WithLet:
    """T-0487 regression: `frob.dup._pipeline._KEYWORDS` was python-only,
    so a Rust `let` in a `let_declaration` matched `_IDENT_RE` and was
    never excluded, mis-labeling it as an extra def/use node
    (`_labeled_ids`/`_statement_ids`) and diverging the def-use graph from
    an equivalent Python function's -- unlike `TestCrossLanguageR5Litmus`
    above (which deliberately avoids a local binding to isolate R5's
    structural-collision claim from this gap), this fixture DOES declare
    one on both sides, so it fails if the `let`-as-identifier bug is
    reintroduced."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "add_let.py",
            "def sum_with_local_py(a, b):\n    total = a + b\n    return total\n",
        )
        _write(
            tmp_path,
            "add_let.rs",
            "fn sum_with_local_rs(a: i32, b: i32) -> i32 {\n"
            "    let total = a + b;\n"
            "    return total;\n"
            "}\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0487
    def test_r5_fires_across_languages_with_a_let_binding(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=1, threshold=0.99)
        ).danger_ok
        rungs = _rungs_for(report, "sum_with_local_py", "sum_with_local_rs")
        assert "r5" in rungs, (
            f"expected r5 to fire across python/rust even when the rust "
            f"side declares a local `let` binding; got rungs={rungs}, "
            f"groups={report.groups!r}"
        )
