"""T-1225: PERF010/011/013/014 -- the four EPIC A hot-graph root-cause
detectors, each proven against a regression-corpus fixture reproducing the
EXACT pre-fix shape the 2026-07-29 hot-graph report mined it from
(`src/frob/tickets/_store.py` pre-T-1206, `src/frob/gates/_debt_deprecated.py`
pre-T-1207, `src/frob/gates/_pii_structural/__init__.py` pre-T-1209,
`src/frob/gates/_secrets.py` pre-T-1211), plus a negative case per rule
proving the corresponding FIXED shape stays silent -- so a future
regression re-introducing any of the four patterns is caught statically,
and the fixed code this repo actually ships never trips its own new rule."""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file
from frob.perf import hotpath_smell_violations, perf_rules


# frob:waive WIRE001 reason="test-fixture builder for this module's own tests -- \
# WIRE001's reachability scan skips test paths by design, same precedent as \
# tests/test_tickets_migration.py's _git_init (T-1490)" follow_up="T-1558"
def _parsed(root: Path, name: str, src: str):
    path = root / name
    path.write_text(src, encoding="utf-8")
    return parse_file(path).danger_ok


class TestPerf010YamlCLoader:
    """Mined from `src/frob/tickets/_store.py`'s pre-T-1206 shape: every
    per-document `yaml.safe_load` call defaulted to the pure-python
    `SafeLoader`."""

    def test_fires_on_pre_fix_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader.test_fires_on_pre_fix_shape  # noqa: E501
        src = (
            "import yaml\n"
            "\n"
            "def load_ticket(text):\n"
            "    data = yaml.safe_load(text)\n"
            "    return data\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert any(v.rule == "PERF010" for v in violations)

    def test_does_not_fire_on_fixed_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader.test_does_not_fire_on_fixed_shape  # noqa: E501
        src = (
            "import yaml\n"
            "\n"
            "def _yaml_loader():\n"
            "    return yaml.CSafeLoader\n"
            "\n"
            "def load_ticket(text):\n"
            "    data = yaml.safe_load(text, Loader=yaml.CSafeLoader)\n"
            "    return data\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF010" for v in violations)

    def test_does_not_fire_in_test_paths(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader.test_does_not_fire_in_test_paths  # noqa: E501
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        src = "import yaml\n\ndef test_x():\n    return yaml.safe_load('a: 1')\n"
        parsed = _parsed(tests_dir, "test_mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF010" for v in violations)

    def test_does_not_fire_on_helper_loader_indirection(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader.test_does_not\
        # _fire_on_helper_loader_indirection  # noqa: E501
        """T-1204: a genuine PERF010 false positive -- calling a shared
        `*_loader()` factory (`frob.yaml_io.fast_yaml_loader`'s own
        established shape) that itself resolves to `yaml.CSafeLoader`
        used to still fire, because the rule's original bare-token scan
        can only ever see a LITERAL `CSafeLoader`/`CLoader` token inside
        the calling symbol's own body, never through a helper call
        boundary."""
        src = (
            "import yaml\n"
            "\n"
            "from frob.yaml_io import fast_yaml_loader\n"
            "\n"
            "def load_ticket(text):\n"
            "    data = yaml.load(text, Loader=fast_yaml_loader())\n"
            "    return data\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF010" for v in violations)


class TestPerf011RepoScanInLoop:
    """Mined from `src/frob/gates/_debt_deprecated.py`'s pre-T-1207 shape:
    a per-symbol `exports_consumers`+`xref` double full-repo scan inside a
    loop over every tracked symbol."""

    def test_fires_on_pre_fix_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop.test_fires_on_pre_fix_shape  # noqa: E501
        src = (
            "def check_debt(symbols):\n"
            "    stale = []\n"
            "    for sym in symbols:\n"
            "        consumers = exports_consumers(sym)\n"
            "        if not consumers:\n"
            "            stale.append(sym)\n"
            "    return stale\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert any(v.rule == "PERF011" for v in violations)

    def test_does_not_fire_when_scan_is_hoisted(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop.test_does_not_fire_when_scan_is_hoisted  # noqa: E501
        src = (
            "def check_debt(symbols):\n"
            "    index = iter_files()\n"
            "    stale = []\n"
            "    for sym in symbols:\n"
            "        if sym not in index:\n"
            "            stale.append(sym)\n"
            "    return stale\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF011" for v in violations)

    def test_does_not_fire_when_scan_is_the_loops_own_iterable(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop.test_does_\
        # not_fire_when_scan_is_the_loops_own_iterable  # noqa: E501
        """T-1647: a real PERF011 false positive on `main` -- the repo-scan
        call is the sole, first loop's own iterable expression
        (`for path in iter_files(root):`), evaluated exactly once to build
        the iterator, never "once per iteration" the way the mined T-1207
        shape is (mirrors `src/frob/arch/__init__.py::_collect_files`'s
        real pre-fix shape)."""
        src = (
            "def collect(root):\n"
            "    result = []\n"
            "    for p in iter_files(root):\n"
            "        result.append(p)\n"
            "    return result\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF011" for v in violations)

    def test_does_not_fire_when_earlier_loop_is_an_unrelated_genexpr(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop.test_does_\
        # not_fire_when_earlier_loop_is_an_unrelated_genexpr  # noqa: E501
        """T-1647: a real PERF011 false positive on `main`
        (`tests/integration/test_integration.py::
        test_outline_line_matches_xref_definition`) -- an unrelated
        generator expression's own `for`-clause earlier in the function
        used to flip the rule's loop-context flag, so a later, entirely
        un-looped repo-scan call was misread as being inside a loop."""
        src = (
            "def find(items, root):\n"
            "    cls = next(c for c in items if c.name == 'X')\n"
            "    xr = xref('X', root)\n"
            "    return cls, xr\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF011" for v in violations)

    def test_fires_when_scan_is_a_nested_loops_own_iterable(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop.test_fires\
        # _when_scan_is_a_nested_loops_own_iterable  # noqa: E501
        """T-1647: the genuine-debt counterpart to the two false-positive
        tests above -- a repo-scan call that IS a loop's own iterable but
        that loop is nested inside an earlier, still-live outer loop (the
        real `src/frob/vet/_capability_scan.py::_aggregate_capabilities`
        shape) really does re-run the scan once per outer iteration, and
        must keep firing."""
        src = (
            "def scan(root, exts):\n"
            "    out = []\n"
            "    for ext in exts:\n"
            "        for path in iter_files(root, suffix=ext):\n"
            "            out.append(path)\n"
            "    return out\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert any(v.rule == "PERF011" for v in violations)


class TestPerf013RepeatedAstWalk:
    """Mined from `src/frob/gates/_pii_structural/__init__.py`'s
    pre-T-1209 shape: each sub-scan independently ran its own
    `ast.walk(tree)` pass over the SAME parsed tree."""

    def test_fires_on_pre_fix_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk.test_fires_on_pre_fix_shape  # noqa: E501
        src = (
            "def scan_all(tree):\n"
            "    emails = [n for n in ast.walk(tree) if is_email(n)]\n"
            "    keywords = [n for n in ast.walk(tree) if is_keyword(n)]\n"
            "    return emails, keywords\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert any(v.rule == "PERF013" for v in violations)

    def test_does_not_fire_on_shared_index(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk.test_does_not_fire_on_shared_index  # noqa: E501
        src = (
            "def scan_all(tree):\n"
            "    index = list(ast.walk(tree))\n"
            "    emails = [n for n in index if is_email(n)]\n"
            "    keywords = [n for n in index if is_keyword(n)]\n"
            "    return emails, keywords\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF013" for v in violations)

    def test_does_not_fire_on_two_different_trees(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf013RepeatedAstWalk.test_does_not_fire_on_two_different_trees  # noqa: E501
        src = (
            "def scan_two(tree_a, tree_b):\n"
            "    a = list(ast.walk(tree_a))\n"
            "    b = list(ast.walk(tree_b))\n"
            "    return a, b\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF013" for v in violations)


class TestPerf014FinditerInNestedLoop:
    """Mined from `src/frob/gates/_secrets.py`'s pre-T-1211 shape: 33
    compiled patterns x one `finditer` call per PHYSICAL LINE -- a
    pattern-list loop nested inside a per-line loop."""

    def test_fires_on_pre_fix_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop.test_fires_on_pre_fix_shape  # noqa: E501
        src = (
            "def scan_secrets(lines, patterns):\n"
            "    hits = []\n"
            "    for line in lines:\n"
            "        for pattern in patterns:\n"
            "            for match in pattern.finditer(line):\n"
            "                hits.append(match)\n"
            "    return hits\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert any(v.rule == "PERF014" for v in violations)

    def test_does_not_fire_on_whole_text_single_pass(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf014FinditerInNestedLoop.test_does_not_fire_on_whole_text_single_pass  # noqa: E501
        src = (
            "def scan_secrets(text, patterns):\n"
            "    hits = []\n"
            "    for pattern in patterns:\n"
            "        for match in pattern.finditer(text):\n"
            "            hits.append(match)\n"
            "    return hits\n"
        )
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert not any(v.rule == "PERF014" for v in violations)


class TestHotpathSmellsWiredIntoPerfRules:
    """`perf_rules` (the real dispatch surface `frob check`'s PERF gate
    consumes) must actually include these four detectors, not just the
    standalone function -- a wiring regression here would silently drop
    all four rules from the live gate while `hotpath_smell_violations`
    itself kept passing its own direct tests."""

    def test_perf_rules_includes_perf010_finding(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestHotpathSmellsWiredIntoPerfRules.test_perf_rules_includes_perf010_finding  # noqa: E501
        from frob.graph import build_graph

        src = "import yaml\n\ndef load_ticket(text):\n    return yaml.safe_load(text)\n"
        _parsed(tmp_path, "mod.py", src)
        cache = tmp_path / ".frob" / "cache.db"
        snapshot = build_graph(tmp_path, cache).danger_ok
        parsed = parse_file(tmp_path / "mod.py").danger_ok
        violations = perf_rules(snapshot, [parsed])
        assert any(v.rule == "PERF010" for v in violations)


class TestPerf011SkipsNonFunctionSymbols:
    """A module with no function/method symbols at all (constants only)
    never reaches either detector's inner loop -- the `kind not in
    _FUNCTION_KINDS` early-return branch."""

    def test_module_level_constant_produces_no_findings(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/perf/test_hotpath_smells.py::TestPerf011SkipsNonFunctionSymbols.test_module_level_constant_produces_no_findings  # noqa: E501
        src = "X = 1\n"
        parsed = _parsed(tmp_path, "mod.py", src)
        violations = hotpath_smell_violations([parsed])
        assert violations == ()
