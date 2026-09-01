from pathlib import Path

import pytest

from frob.gates import (
    Severity,
    Violation,
    fmt_gate,
)
from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.tickets import TicketQueue
from tests.conftest import (
    _snapshot,
    _write,
)


# frob:ticket T-0851
# frob:ticket T-1763
class TestFmt001Gate:
    """T-0851: FMT001, the T-0441 follow-up -- a diff-touched `frob:`
    directive comment line over the configured line length gets a `frob
    fmt <path>` remediation hint; an ordinary long comment or long code
    line (neither is a `frob:` directive run) does not."""

    # frob:ticket T-0851
    # frob:ticket T-1763
    def test_directive_run_over_limit_flagged(self, tmp_path: Path) -> None:
        """A single-physical-line `frob:waive` directive over the default
        88-col limit is FMT001, naming `frob fmt <path>` as the fix."""
        long_reason = "x" * 70
        source = (
            "def helper(x):\n"
            f'    # frob:waive SCOPE001 reason="{long_reason}"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        hit = next((v for v in violations if v.rule == "FMT001"), None)
        assert hit is not None
        assert hit.file == "src/a.py"
        assert hit.line == 2
        assert "frob fmt src/a.py" in hit.message

    # frob:ticket T-0851
    def test_ordinary_long_comment_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit comment line that is NOT a `frob:` directive
        (near-miss #1) never fires FMT001 -- `frob fmt` would not touch it
        either, so a hint naming it as the fix would be false."""
        long_comment = "y" * 90
        source = f"def helper(x):\n    # {long_comment}\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    def test_long_code_line_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit CODE line (near-miss #2, no comment marker at all)
        never fires FMT001."""
        source = "def helper(x):\n    y = " + "1" * 90 + "\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    # frob:ticket T-1763
    def test_untouched_line_not_flagged(self, tmp_path: Path) -> None:
        """An over-limit directive line the diff does NOT touch is not
        flagged -- FMT001 is diff-scoped, same posture as TODO001."""
        long_reason = "x" * 70
        source = (
            "def helper(x):\n"
            f'    # frob:waive SCOPE001 reason="{long_reason}"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(3, 3)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)

    # frob:ticket T-0851
    def test_short_directive_not_flagged(self, tmp_path: Path) -> None:
        """A `frob:` directive line that already fits within the limit is
        not flagged, even when touched."""
        source = "def helper(x):\n    # frob:ticket T-0001\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        diff = Diff(base="x", hunks=(Hunk(file="src/a.py", span=(2, 2)),))
        violations = fmt_gate(tmp_path, diff)
        assert not any(v.rule == "FMT001" for v in violations)
class TestDupPipelineClosureConsumers:
    """T-0814: `frob.dup._pipeline`'s raw `CallGraph.calls` consumers share
    the same non-symref-entry assumption as the `frob.gates` COV006
    closure consumers (T-0809 reviewer condition b) -- covered here,
    scoped to `tests/test_gates.py` per T-0814's declared scope."""

    # frob:ticket T-0814
    # frob:tests \
    # tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers.test_is_symref_d\
    # up kind="unit"
    def test_is_symref_dup(self) -> None:
        """T-0814: `frob.dup._pipeline._is_symref` mirrors `frob.gates`'s
        helper of the same name -- both files are outside a shared home
        (`frob/graph/callgraph.py`) per T-0814's declared scope, so each
        keeps its own copy of this one-line predicate."""
        from frob.dup._pipeline import _is_symref
        from frob.graph.callgraph import UNRESOLVED_CALLEE

        assert _is_symref("src/a.py::_helper") is True
        assert _is_symref(UNRESOLVED_CALLEE) is False

    # frob:ticket T-0814
    # frob:tests tests/gates_suite/test_waive.py::TestDupPipelineClosureConsumers.test_callee_name_map_skips_unresolved_callee_sentinel kind="unit"  # noqa: E501
    def test_callee_name_map_skips_unresolved_callee_sentinel(self) -> None:
        """T-0814: `_callee_name_map` iterates `graph.calls.get(caller, ())`
        and used to do `callee_symref.split("::", 1)[1]` unconditionally --
        a bare `UNRESOLVED_CALLEE` sentinel entry (no `::`) IndexErrors
        that. A `CallGraph` carrying the sentinel alongside a real callee
        must not raise, and the real callee must still resolve -- the
        sentinel is skipped, not silently swallowing real entries too."""
        from frob.dup._pipeline import _callee_name_map
        from frob.graph.callgraph import UNRESOLVED_CALLEE, CallGraph

        graph = CallGraph(
            calls={
                "src/a.py::caller": ("src/a.py::_real_helper", UNRESOLVED_CALLEE),
            }
        )
        result = _callee_name_map(graph, "src/a.py::caller")
        assert result == {"_real_helper": "src/a.py::_real_helper"}
class TestDsl001:
    """T-0404 finding 5: a malformed `frob:` directive not already claimed
    by WAIVE001/TEST010/DEBT001 must still be surfaced, not silently
    dropped."""

    def test_malformed_frob_doc_directive_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_waive.py::_dsl001_violations kind="unit"
        # A bare `frob:doc` with no target parses to a MalformedDirective
        # ("missing target for verb 'doc'") -- before DSL001 existed this
        # produced NO violation at all.
        source = "def helper(x):\n    # frob:doc\n    return x\n"
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _dsl001_violations  # noqa: PLC0415

        violations = _dsl001_violations(snap)
        assert any(v.rule == "DSL001" for v in violations)
        assert violations[0].severity == Severity.ERROR

    def test_docarch001_wiring_comment_does_not_self_match(self) -> None:
        """T-3255 regression: a plain `#` comment near
        `docarch001_violations`'s `run_gates` call site used to describe
        the discriminator as applying to "frob:waive reasons" -- the
        literal `frob:waive` token mid-prose parsed as a malformed
        directive and DSL001 fired against the gate module's OWN source
        (production self-match, not a test fixture). Runs against the
        real, checked-out `src/frob/gates/__init__.py` (not a synthetic
        tmp_path fixture) so a future reintroduction of a bare `frob:`
        verb token in prose is caught the same way this one was."""
        from pathlib import Path as _Path

        from frob.gates import _dsl001_violations  # noqa: PLC0415

        repo_root = _Path(__file__).resolve().parents[2]
        snap = _snapshot(repo_root)
        hits = [
            v for v in _dsl001_violations(snap) if v.file.endswith("gates/__init__.py")
        ]
        assert hits == [], (
            f"DSL001 false-positive(s) reintroduced in gates/__init__.py: {hits}"
        )

    def test_waive_reason_and_tests_kind_not_double_flagged(
        self, tmp_path: Path
    ) -> None:
        # A malformed frob:waive (no reason) and a malformed frob:tests
        # (bad kind=) are already surfaced by WAIVE001/TEST010 -- DSL001
        # must not ALSO flag them (no double-reporting the same directive).
        source = (
            "def helper(x):\n"
            "    # frob:waive COV001\n"
            '    # frob:tests helper kind="bogus"\n'
            "    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        from frob.gates import _dsl001_violations  # noqa: PLC0415

        assert _dsl001_violations(snap) == ()
# frob:ticket T-1272
class TestWaivePresets:
    """T-1176: `frob:waive RULE preset="<name>"` resolves its reason from
    `frob.graph._waive_presets.WAIVE_PRESETS`, drift-locked against the
    documented table in `docs/modules/gates.md#waiver-presets`."""

    def test_docs_table_matches_waive_presets(self) -> None:
        # frob:tests src/frob/graph/_waive_presets.py::WAIVE_PRESETS kind="unit"
        # Parses docs/modules/gates.md's "Waiver presets" markdown table and
        # asserts its (name, reason) rows match WAIVE_PRESETS exactly -- a
        # preset added/edited in one place without the other fails here.
        from frob.graph._waive_presets import WAIVE_PRESETS

        doc_path = (
            Path(__file__).resolve().parent.parent.parent / "docs" / "modules" / "gates.md"
        )
        text = doc_path.read_text()
        start = text.index("### Waiver presets")
        table_start = text.index("| preset name |", start)
        section = text[table_start : text.index("\n\n", table_start)]
        rows = [
            line
            for line in section.splitlines()
            if line.startswith("| `") and "---" not in line
        ]
        assert rows, "expected at least one preset row in docs/modules/gates.md"
        doc_presets: dict[str, str] = {}
        for row in rows:
            cells = [c.strip() for c in row.strip("|").split("|")]
            name = cells[0].strip("`")
            reason = cells[1]
            doc_presets[name] = reason
        assert doc_presets == WAIVE_PRESETS

    def test_resolve_preset_known_name(self) -> None:
        # frob:tests src/frob/graph/_waive_presets.py::resolve_preset kind="unit"
        from frob.graph._waive_presets import WAIVE_PRESETS, resolve_preset

        assert (
            resolve_preset("split-carried-prose")
            == WAIVE_PRESETS["split-carried-prose"]
        )

    def test_resolve_preset_unknown_name_is_none(self) -> None:
        # frob:tests src/frob/graph/_waive_presets.py::resolve_preset kind="unit"
        from frob.graph._waive_presets import resolve_preset

        assert resolve_preset("no-such-preset") is None

    # frob:ticket T-1272
    # frob:waive COV006 reason="genuinely reachable via _snapshot -> build_graph -> \
    # parse_directives -> _parse_attrs -> _parse_attrs_verb_error -> \
    # _VERB_ATTRS_VALIDATORS[verb] -> _attrs_verb_error_waive, but \
    # frob.graph.callgraph's best-effort BFS cannot trace through that \
    # dict-of-callables dispatch, same blind spot as the T-1024 _scope_covers waivers \
    # above"
    def test_waive_preset_resolves_reason_and_matches_like_inline(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::_attrs_verb_error_waive kind="unit"
        # A preset= waiver suppresses a violation identically to an
        # equivalent inline reason= waiver -- same _apply_waivers spine.
        from frob.gates._waive import _apply_waivers
        from frob.graph._waive_presets import WAIVE_PRESETS

        source = (
            '# frob:waive DEAD001 preset="split-carried-prose"\n'
            "def helper(x):\n    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        assert snap.malformed == ()
        violation = Violation(
            rule="DEAD001",
            severity=Severity.ERROR,
            file="src/a.py",
            line=1,
            message="DEAD001 test violation",
        )
        kept, waived = _apply_waivers((violation,), snap)
        assert kept == ()
        assert len(waived) == 1
        assert waived[0].waived is not None
        assert waived[0].waived.reason == WAIVE_PRESETS["split-carried-prose"]

    # frob:ticket T-1272
    # frob:waive COV006 reason="genuinely reachable via _snapshot -> build_graph -> \
    # parse_directives -> _parse_attrs -> _parse_attrs_verb_error -> \
    # _VERB_ATTRS_VALIDATORS[verb] -> _attrs_verb_error_waive, but \
    # frob.graph.callgraph's best-effort BFS cannot trace through that \
    # dict-of-callables dispatch, same blind spot as the T-1024 _scope_covers waivers \
    # above"
    def test_unknown_preset_is_malformed_directive(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_attrs_verb_error_waive kind="unit"
        source = (
            '# frob:waive DEAD001 preset="does-not-exist"\n'
            "def helper(x):\n    return x\n"
        )
        _write(tmp_path, "src/a.py", source)
        snap = _snapshot(tmp_path)
        assert any(
            "frob:waive" in md.reason and "does-not-exist" in md.reason
            for md in snap.malformed
        )
class TestParseFailureGate:
    """T-0558: a swallowed frob.lang parse/IO failure must be an ERROR
    violation (PARSE001), not just a log line.

    frob:ticket T-0558
    frob:ticket T-0561
    """

    # frob:ticket T-0561
    def test_parse_failure_is_an_error_violation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.graph._models import ParseFailure

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        snap = snap.model_copy(
            update={
                "parse_failures": (
                    ParseFailure(file="src/broken.py", reason="ParseFailed"),
                )
            }
        )
        violations = parse_failure_gate(snap)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "PARSE001"
        assert v.severity == Severity.ERROR
        assert v.file == "src/broken.py"

    # frob:ticket T-0561
    def test_no_parse_failures_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        # T-0905/T-0902: reset frob.lang's process-lifetime partial-parse
        # set before asserting "clean" -- an earlier test in this xdist
        # worker that parsed a syntax-error fixture (any test calling
        # build_graph directly, bypassing frob.check's own once-per-run
        # reset) would otherwise leak a stale PARSE002 entry in here.
        reset_parse_cache()
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        assert parse_failure_gate(snap) == ()

    # frob:ticket T-0902
    def test_partial_parse_is_an_error_violation(self, tmp_path: Path) -> None:
        """T-0905/T-0902: a syntax error partway through a file (tree-sitter
        salvages a PARTIAL tree, not a hard failure) must fire PARSE002,
        symmetric with PARSE001's hard-failure handling -- the missing
        tail symbols are silently dropped from the salvaged tree
        otherwise, and no other gate would ever notice."""
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(
            tmp_path,
            "src/broken.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        assert "src/broken.py::good_one" in snap.symbols

        violations = parse_failure_gate(snap)
        reset_parse_cache()
        hits = [v for v in violations if v.rule == "PARSE002"]
        assert len(hits) == 1
        assert hits[0].severity == Severity.ERROR
        assert "broken.py" in hits[0].file

    # frob:ticket T-0942
    def test_partial_parse_in_graph_excluded_path_is_silent(
        self, tmp_path: Path
    ) -> None:
        """T-0942: a graph-excluded path (frob.toml [graph].exclude, e.g. a
        deliberately-broken parser fixture) contributes no symbols to the
        obligation graph, so PARSE002's missing-symbols claim is vacuous
        there -- and in-file waivers cannot bind on excluded paths. The
        gate must stay silent for it while still firing on a non-excluded
        partial parse in the same run."""
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(
            tmp_path,
            "frob.toml",
            '[graph]\nexclude = ["fixtures/**"]\n',
        )
        _write(
            tmp_path,
            "fixtures/broken_fixture.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        _write(
            tmp_path,
            "src/broken.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = parse_failure_gate(snap)
        reset_parse_cache()
        hits = [v for v in violations if v.rule == "PARSE002"]
        assert len(hits) == 1
        assert "src/broken.py" in hits[0].file

    # frob:ticket T-0902
    def test_no_partial_parses_is_clean(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_parse_failures.py::parse_failure_gate kind="unit"
        from frob.gates._parse_failures import parse_failure_gate
        from frob.lang import reset_parse_cache

        reset_parse_cache()
        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        violations = parse_failure_gate(snap)
        reset_parse_cache()
        assert not any(v.rule == "PARSE002" for v in violations)




# frob:ticket T-1323
class TestWaive004DegradedRunGuard:
    """`fix_waive004_stale_waiver`'s T-1323 prove-fresh-or-do-nothing guard:
    the 2026-07-29 incident's confirmed root-cause reproduction (a
    degraded self-manufactured `run_gates()` verification -- stale/missing
    natives or a skipped stage -- must never drive a deletion), plus the
    mass-invalidation shape (one rule's waivers all going stale together
    in a single run) as an independent, baseline-free signal of the same
    failure class."""

    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    def _fixture_with_one_dead_waiver(self, root: Path) -> None:
        (root / "src").mkdir(parents=True)
        (root / "src" / "m.py").write_text(
            '# frob:waive REF001 reason="genuinely dead waiver, T-1323 fixture"\n'
            "def f():\n    return 1\n",
            encoding="utf-8",
        )
        (root / "tickets.md").write_text("", encoding="utf-8")

    def test_native001_degraded_run_deletes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `NATIVE001` finding in the self-manufactured run (natives
        stale/missing) means `run_gates` returned its short-circuited
        single-finding report -- the guard must refuse to act on it."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        self._fixture_with_one_dead_waiver(root)
        snapshot = self._snap(root)

        native_report = GateReport(
            violations=(
                Violation(
                    rule="NATIVE001",
                    severity=Severity.ERROR,
                    file=str(root),
                    line=0,
                    message="NATIVE001: strata_core is unavailable",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(native_report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert applied == []
        original = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "frob:waive REF001" in original

    def test_skipped_stage_degraded_run_deletes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-empty `GateStats.skipped` means at least one gate stage
        did not run at all -- the guard must refuse to act, even though
        the WAIVE004 violation itself looks completely ordinary."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        self._fixture_with_one_dead_waiver(root)
        snapshot = self._snap(root)

        degraded_report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/m.py",
                    line=1,
                    message="WAIVE004: frob:waive REF001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(skipped=("archgate",)),
        )
        monkeypatch.setattr(
            "frob.gates.run_gates", lambda cfg, **kw: Ok(degraded_report)
        )

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert applied == []
        original = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "frob:waive REF001" in original

    def test_mass_invalidation_of_one_rule_deletes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single self-manufactured run proposing to delete many
        waivers of the SAME rule at once (the incident's own shape) is
        treated as anomalous-zero-findings evidence and refuses the
        WHOLE batch -- not just the excess above threshold."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import (
            _WAIVE004_MASS_INVALIDATION_THRESHOLD,
            fix_waive004_stale_waiver,
        )

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD):
            (root / "src" / f"m{i}.py").write_text(
                f'# frob:waive PERF00{i % 9} reason="fixture {i}"\n'
                "def f():\n    return 1\n",
                encoding="utf-8",
            )
        snapshot = self._snap(root)

        mass_violations = tuple(
            Violation(
                rule="WAIVE004",
                severity=Severity.ERROR,
                file=f"src/m{i}.py",
                line=1,
                message="WAIVE004: frob:waive PERF001 matches 0 findings",
            )
            for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD)
        )
        mass_report = GateReport(
            violations=mass_violations, waived=(), stats=GateStats()
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(mass_report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert applied == []
        for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD):
            content = (root / "src" / f"m{i}.py").read_text(encoding="utf-8")
            assert "frob:waive PERF00" in content

    def test_mass_invalidation_with_live_finding_elsewhere_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1592 regression lock: the SAME mass-stale shape as the test
        above, but this run ALSO reports a live, non-WAIVE004 finding of
        the target rule elsewhere. T-1579 treated that as proof the
        detector ran and deleted anyway; a PARTIALLY degraded run
        satisfies it just as easily, and doing so deleted 55 live waivers
        during a real land. Mass-staleness refuses regardless of live
        findings elsewhere."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import (
            _WAIVE004_MASS_INVALIDATION_THRESHOLD,
            fix_waive004_stale_waiver,
        )

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD):
            (root / "src" / f"m{i}.py").write_text(
                '# frob:waive PERF001 reason="fixture"\ndef f():\n    return 1\n',
                encoding="utf-8",
            )
        snapshot = self._snap(root)

        stale_violations = tuple(
            Violation(
                rule="WAIVE004",
                severity=Severity.ERROR,
                file=f"src/m{i}.py",
                line=1,
                message="WAIVE004: frob:waive PERF001 matches 0 findings",
            )
            for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD)
        )
        live_elsewhere = Violation(
            rule="PERF001",
            severity=Severity.WARN,
            file="src/other.py",
            line=7,
            message="PERF001: a real, live finding proving the detector ran",
        )
        mass_report = GateReport(
            violations=(*stale_violations, live_elsewhere), waived=(), stats=GateStats()
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(mass_report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert [a for a in applied if a.rule == "WAIVE004"] == []
        for i in range(_WAIVE004_MASS_INVALIDATION_THRESHOLD):
            content = (root / "src" / f"m{i}.py").read_text(encoding="utf-8")
            assert "frob:waive PERF001" in content

    def test_healthy_run_below_threshold_still_deletes(self, tmp_path: Path) -> None:
        """A genuine, non-degraded full run with a single stale waiver
        (no NATIVE001, no skipped stage, well under the mass-invalidation
        threshold) still deletes it -- the guard must not become a
        blanket no-op."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        self._fixture_with_one_dead_waiver(root)
        snapshot = self._snap(root)

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "frob:waive REF001" not in rewritten


# frob:ticket T-1942
class TestWaive004ExaminedSitesGuard:
    """T-1942: the THIRD, additive WAIVE004 guard -- an archgate-family
    candidate must not be deleted unless this run's real per-site
    examined-sites substrate (T-1921, `frob.gates._coverage_sites`)
    positively confirms the candidate's own file was examined.
    `fix_waive004_stale_waiver` enriches its self-manufactured report via
    `attach_examined_sites`, which recomputes the "archgate" entry for
    real against `root` -- so these fixtures control examined-ness by
    writing real, on-disk files a genuine `arch_examined_sites(root)`
    call will (or will not) parse, not by injecting a fake
    `GateStats.examined_sites` the real call would just overwrite."""

    # frob:ticket T-1942
    def _snap(self, root: Path):

        return build_graph(root, root / ".frob" / "cache.db").danger_ok

    # frob:ticket T-1942
    def test_examined_archgate_site_is_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A waiver on an archgate-rule site that a real
        `arch_examined_sites(root)` call DOES confirm was examined this
        run behaves exactly as before T-1942 -- the guard grants
        deletion, it does not additionally refuse a genuinely examined
        site."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        (root / "src" / "good.py").write_text(
            '# frob:waive ARCH001 reason="fixture, T-1942"\ndef f():\n    return 1\n',
            encoding="utf-8",
        )
        snapshot = self._snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/good.py",
                    line=1,
                    message="WAIVE004: frob:waive ARCH001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "good.py").read_text(encoding="utf-8")
        assert "frob:waive ARCH001" not in rewritten

    # frob:ticket T-1942
    def test_uninstrumented_family_is_unchanged_from_today(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A waiver targeting a rule NOT in the archgate family (e.g.
        PERF001 -- perf is deliberately uninstrumented per T-1921) must
        behave IDENTICALLY to pre-T-1942 -- this new guard grants nothing
        for any family it does not instrument, it must never additionally
        NARROW an uninstrumented family's existing behavior either. Proof
        that the guard is gated on `rule in archgate_rule_ids()`, not on
        an unconditional `site_examined` call that would trivially return
        False here and wrongly block this deletion."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        (root / "src" / "m.py").write_text(
            '# frob:waive PERF001 reason="fixture, T-1942, uninstrumented family"\n'
            "def f():\n    return 1\n",
            encoding="utf-8",
        )
        snapshot = self._snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/m.py",
                    line=1,
                    message="WAIVE004: frob:waive PERF001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "m.py").read_text(encoding="utf-8")
        assert "frob:waive PERF001" not in rewritten

    # frob:ticket T-1942
    def test_unexamined_archgate_site_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A degraded-shaped run: archgate IS instrumented (it always is,
        in this handler's self-manufactured run), but the candidate's own
        file is NOT a member of the real, freshly-computed examined set
        this time (unparseable python source, T-1921's own
        `_analyze_one_file` contract) -- the guard must refuse to delete
        it, even though the WAIVE004 finding itself looks completely
        ordinary. This is the exact shape (family instrumented, this file
        absent from the examined set) the ticket's acceptance criterion 3
        names."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        # A file with no tree-sitter grammar for its extension --
        # `_analyze_one_file` early-returns before any parse/checks run
        # (same "not examined" shape `test_examined_sites.py`'s own
        # `test_archgate_examined_sites_exclude_an_unparseable_file`
        # proves at the substrate layer), so this file never joins
        # `ArchResult.files_examined` this run.
        (root / "src" / "bad.bin").write_bytes(b"\x00\x01\x02")
        snapshot = self._snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/bad.bin",
                    line=1,
                    message="WAIVE004: frob:waive ARCH001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert applied == []

    # frob:ticket T-1942
    def test_original_55_waiver_incident_shape_partial_examination_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The original incident's own shape, reproduced narrowly: a
        batch of archgate-rule WAIVE004 candidates where the real
        examined-sites substrate confirms SOME sites but not ALL of
        them. A caller that trusted "the family fired, and some sites
        came back clean" as proof of coverage would delete the whole
        batch -- exactly `_rule_has_live_finding`'s falsified reasoning,
        one layer down at the per-site level instead of per-rule. This
        guard must keep the confirmed-examined candidate and drop the
        unconfirmed one, never all-or-nothing on the rule as a whole (the
        OTHER two guards already own the all-or-nothing shape; this one
        is strictly per-site)."""
        # frob:tests src/frob/gates/_fix_engine_sync.py::fix_waive004_stale_waiver \
        # kind="unit"
        from typani.result import Ok

        from frob.gates import GateReport, GateStats, Severity, Violation
        from frob.gates._fix_engine_sync import fix_waive004_stale_waiver

        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        (root / "src" / "examined.py").write_text(
            '# frob:waive ARCH001 reason="fixture, T-1942, examined site"\n'
            "def f():\n    return 1\n",
            encoding="utf-8",
        )
        # No tree-sitter grammar for this extension -- same "not
        # examined" mechanism as `test_unexamined_archgate_site_refuses`
        # above, deliberately using a bogus `frob:waive` comment so the
        # test also demonstrates the file NEVER GETS REWRITTEN, not just
        # that `applied` omits it.
        (root / "src" / "unexamined.bin").write_bytes(
            b'# frob:waive ARCH001 reason="fixture"\n'
        )
        snapshot = self._snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/examined.py",
                    line=1,
                    message="WAIVE004: frob:waive ARCH001 matches 0 findings",
                ),
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/unexamined.bin",
                    line=1,
                    message="WAIVE004: frob:waive ARCH001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert [a.file for a in waive004_applied] == ["src/examined.py"]
        assert "frob:waive ARCH001" not in (root / "src" / "examined.py").read_text(
            encoding="utf-8"
        )
        assert "frob:waive ARCH001" in (root / "src" / "unexamined.bin").read_text(
            encoding="utf-8"
        )
