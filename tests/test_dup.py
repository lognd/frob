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


class TestErrorChannelNormalization:
    """T-0785 unit coverage for `frob.dup._pipeline._normalize_error_channel`
    itself: audit M3 found the triplicated git-common-dir resolver slipped
    under DUP's similarity threshold purely because one implementation
    signals failure via `Result`'s `Err(...)`/`Ok(...)` and the other via
    plain `None`/the bare value. These are fast, core-independent checks on
    the token-level transform in isolation (no `frob_core`, no
    `find_clones`) -- `TestErrorChannelDupPairing` below covers the actual
    end-to-end pairing claim through `find_clones`."""

    # frob:tests tests/test_dup.py::TestErrorChannelNormalization.test_err_and_none_collapse_to_the_same_marker kind="unit"  # noqa: E501
    # frob:ticket T-0785
    def test_err_and_none_collapse_to_the_same_marker(self):
        from frob.dup._pipeline import _normalize_error_channel

        err_tokens = (
            "return",
            "Err",
            "(",
            "LeaseError",
            ".",
            "GitCommonDirUnavailable",
            ")",
        )
        none_tokens = ("return", "None")
        assert _normalize_error_channel(err_tokens) == _normalize_error_channel(
            none_tokens
        ), "Err(...) and None must canonicalize to the identical marker shape"

    # frob:tests tests/test_dup.py::TestErrorChannelNormalization.test_ok_unwraps_to_the_bare_payload kind="unit"  # noqa: E501
    # frob:ticket T-0785
    def test_ok_unwraps_to_the_bare_payload(self):
        from frob.dup._pipeline import _normalize_error_channel

        ok_tokens = ("return", "Ok", "(", "common_dir", ")")
        plain_tokens = ("return", "common_dir")
        assert (
            _normalize_error_channel(ok_tokens)
            == _normalize_error_channel(plain_tokens)
            == plain_tokens
        ), "Ok(x) must unwrap to the same bare `return x` an Optional payload uses"

    # frob:tests tests/test_dup.py::TestErrorChannelNormalization.test_raise_collapses_to_the_same_marker_as_err_and_none kind="unit"  # noqa: E501
    # frob:ticket T-0785
    def test_raise_collapses_to_the_same_marker_as_err_and_none(self):
        from frob.dup._pipeline import _normalize_error_channel

        raise_tokens = (
            "raise",
            "ValueError",
            "(",
            '"',
            "bad input",
            '"',
            ")",
            "return",
            "None",
        )
        # A `raise` statement followed by an unrelated `return None` should
        # collapse BOTH exits to the same marker shape, not just the second.
        normalized = _normalize_error_channel(raise_tokens)
        assert normalized == ("return", "$err_exit", "return", "$err_exit")

    # frob:tests tests/test_dup.py::TestErrorChannelNormalization.test_a_genuinely_different_return_value_is_not_collapsed kind="unit"  # noqa: E501
    # frob:ticket T-0785
    def test_a_genuinely_different_return_value_is_not_collapsed(self):
        from frob.dup._pipeline import _normalize_error_channel

        # Negative case: two DIFFERENT non-error-channel plain returns must
        # stay distinct -- normalization must not blur ordinary logic.
        a = ("return", "x", "+", "1")
        b = ("return", "x", "-", "1")
        assert _normalize_error_channel(a) != _normalize_error_channel(b)
        # And the payload-carrying shapes pass straight through unchanged.
        assert _normalize_error_channel(a) == a
        assert _normalize_error_channel(b) == b

    # frob:tests tests/test_dup.py::TestErrorChannelNormalization.test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan kind="unit"  # noqa: E501
    # frob:ticket T-0785
    def test_nested_err_argument_parens_do_not_confuse_the_close_paren_scan(self):
        from frob.dup._pipeline import _normalize_error_channel

        # `Err(SomeError(x, [1, 2]))` -- nested call/collection inside the
        # Err(...) argument list must not close the outer paren early.
        nested = (
            "return",
            "Err",
            "(",
            "SomeError",
            "(",
            "x",
            ",",
            "[",
            "1",
            ",",
            "2",
            "]",
            ")",
            ")",
            "pass",
        )
        assert _normalize_error_channel(nested) == (
            "return",
            "$err_exit",
            "pass",
        )


class TestErrorChannelDupPairing:
    """T-0785 (audit M3) end-to-end: the triplicated git-common-dir
    resolver -- one shaped like `frob.tickets._leases.git_common_dir`
    (`Result[Path, LeaseError]`, `Err(...)`/`Ok(...)`), the other shaped
    like `frob.gates._exclude_hazard._git_common_dir` (`Path | None`,
    `return None`/the bare value) -- must register as a duplicate group
    once error-channel shape is normalized away. Real repo shapes (message
    text, variable names, control-flow order) are kept as close to the two
    real functions as possible; the one deliberate simplification is
    collapsing `_git_common_dir`'s two separate early-return `if`s (each
    logging a DIFFERENT debug message) into the same single combined `if`
    `git_common_dir` uses (both of its branches share ONE error value) --
    that restructuring is a second, genuinely independent dimension this
    ticket's scope does not cover (`frob:todo T-0001`-class future work),
    and left uncollapsed it sinks R4's near-miss floor on its own,
    independent of the error-channel question this ticket is about."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "common_dir.py",
            "from pathlib import Path\n"
            "\n"
            "from typani import Err, Ok\n"
            "from typani.result import Result\n"
            "\n"
            "\n"
            "def git_common_dir(root: Path) -> Result[Path, LeaseError]:\n"
            '    """The shared `.git` directory for `root`\'s repository."""\n'
            "    spawned = run_argv(\n"
            '        ["git", "-C", str(root), "rev-parse", "--git-common-dir"]\n'
            "    )\n"
            "    if spawned.is_err or spawned.danger_ok.returncode != 0:\n"
            '        _log.warning("tickets: git-common-dir lookup failed under %s", root)\n'  # noqa: E501
            "        return Err(LeaseError.GitCommonDirUnavailable)\n"
            "    raw = spawned.danger_ok.stdout.strip()\n"
            "    if not raw:\n"
            "        return Err(LeaseError.GitCommonDirUnavailable)\n"
            "    common_dir = Path(raw)\n"
            "    if not common_dir.is_absolute():\n"
            "        common_dir = (root / common_dir).resolve()\n"
            "    return Ok(common_dir)\n"
            "\n"
            "\n"
            "def _git_common_dir(root: Path) -> Path | None:\n"
            '    """The shared `.git` common dir for `root`."""\n'
            "    spawned = run_argv(\n"
            '        ("git", "-C", str(root), "rev-parse", "--git-common-dir")\n'
            "    )\n"
            "    if spawned.is_err or spawned.danger_ok.returncode != 0:\n"
            '        _log.debug("exclude_hazard: git rev-parse failed under %s", root)\n'  # noqa: E501
            "        return None\n"
            "    raw = spawned.danger_ok.stdout.strip()\n"
            "    if not raw:\n"
            "        return None\n"
            "    common_dir = Path(raw)\n"
            "    if not common_dir.is_absolute():\n"
            "        common_dir = (root / common_dir).resolve()\n"
            "    return common_dir\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0785
    def test_result_and_optional_git_common_dir_register_as_a_duplicate_group(
        self, snapshot
    ):
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.01)
        ).danger_ok
        rungs = _rungs_for(report, "git_common_dir", "_git_common_dir")
        assert rungs, (
            "the Result-shaped and Optional-shaped git-common-dir resolvers "
            f"must register as a duplicate pair once error-channel shape is "
            f"normalized away; got 0 matching pairs, groups={report.groups!r}"
        )


class TestErrorChannelNormalizationDoesNotOverFire:
    """T-0785 negative control: genuinely different logic must NOT be
    dragged into a false pair just because both sides happen to use an
    error-channel exit somewhere in their body -- normalizing the exit
    SHAPE must not blur everything else two functions do."""

    @pytest.fixture()
    def snapshot(self, tmp_path):
        _write(
            tmp_path,
            "unrelated.py",
            "def parse_count(raw):\n"
            "    if not raw:\n"
            "        return None\n"
            "    return int(raw)\n"
            "\n"
            "\n"
            "def average(values):\n"
            "    if not values:\n"
            "        return None\n"
            "    total = 0\n"
            "    for v in values:\n"
            "        total = total + v\n"
            "    return total / len(values)\n",
        )
        cache = tmp_path / "graph-cache"
        result = build_graph(tmp_path, cache)
        assert result.is_ok, result.err
        return result.danger_ok

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0785
    def test_genuinely_different_logic_does_not_falsely_pair(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=3, threshold=0.01)
        ).danger_ok
        rungs = _rungs_for(report, "parse_count", "average")
        assert not rungs, (
            "sharing a `None`-shaped early-return must not, on its own, "
            f"pair two functions with genuinely different logic; got "
            f"rungs={rungs}, groups={report.groups!r}"
        )


class TestVerdictCacheRulesFingerprintInvalidation:
    """T-0798: `.frob/dup.db` was keyed by content digest only, so a dup
    rule/normalization change (e.g. T-0785) silently replayed pre-change
    verdicts until the db was hand-deleted -- a gate-integrity hole. The
    stored fingerprint now also covers `frob.dup`'s own source bytes
    (`_cache._dup_code_fingerprint`), so any such change must flip a
    cached verdict rather than serve it as still-current."""

    # frob:tests tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation.test_dup_code_fingerprint_change_invalidates_cached_verdict kind="unit"  # noqa: E501
    def test_dup_code_fingerprint_change_invalidates_cached_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.dup import _cache

        # Seed a verdict row as if `find_clones` wrote it under an OLD
        # frob.dup rule/normalization fingerprint (a landed rule change
        # like T-0785, with no package version bump -- the scenario the
        # version-only fingerprint (T-0517) could not catch).
        monkeypatch.setattr(_cache, "_dup_code_fingerprint", lambda: "old-rules")
        put_result = _cache.put_verdict(
            tmp_path, "d1", "d2", "r4", 0, (0.99, ()), cache_entries=200_000
        )
        assert put_result.is_ok, put_result.err
        assert _cache.get_verdict(tmp_path, "d1", "d2", "r4", 0) == [0.99, []]

        # The rules change (a real process would recompute this from the
        # edited source bytes) and a fresh connection opens, as a new
        # `frob check` run would. The stale verdict must be gone, not
        # served as current.
        _cache._close_all()
        monkeypatch.setattr(_cache, "_dup_code_fingerprint", lambda: "new-rules")
        assert _cache.get_verdict(tmp_path, "d1", "d2", "r4", 0) is None

    # frob:tests tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation.test_unchanged_dup_code_fingerprint_still_serves_cached_verdict kind="unit"  # noqa: E501
    def test_unchanged_dup_code_fingerprint_still_serves_cached_verdict(
        self, tmp_path: Path
    ) -> None:
        from frob.dup import _cache

        # Negative control: a same-fingerprint reconnect (the normal case,
        # no rule change) must NOT wipe the row.
        _cache.put_verdict(
            tmp_path, "d3", "d4", "r4", 0, (0.5, ()), cache_entries=200_000
        )
        _cache._close_all()
        assert _cache.get_verdict(tmp_path, "d3", "d4", "r4", 0) == [0.5, []]
