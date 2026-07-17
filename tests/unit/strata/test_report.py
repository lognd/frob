"""Unit tests for the strata verdict report (docs/strata/kernel.md#verdict-report)."""

from __future__ import annotations

from frob.strata import ClaimResult, Quantifier, Verdict, render_report, summarize


def _result(
    claim_id: str,
    verdict: Verdict,
    *,
    quantifier: Quantifier = Quantifier.FORALL,
    counterexample: tuple[str, ...] = (),
    detail: str = "",
) -> ClaimResult:
    return ClaimResult(
        claim_id=claim_id,
        verdict=verdict,
        quantifier=quantifier,
        counterexample=counterexample,
        detail=detail,
    )


class TestOrdering:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_refuted_sorts_first_regardless_of_input_order(self):
        results = (
            _result("c3", Verdict.PROVED, detail="proved"),
            _result("c1", Verdict.ASSUMED, detail="assumed by bob"),
            _result("c2", Verdict.REFUTED, detail="refuted"),
        )
        report = render_report(results)
        lines = [
            line for line in report.splitlines() if line and not line.startswith(" ")
        ]
        assert lines[0].startswith("REFUTED")
        assert lines[1].startswith("ASSUMED")
        assert lines[2].startswith("PROVED")


class TestCounterexamplePath:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_refuted_line_followed_by_exact_path_line(self):
        results = (
            _result(
                "c1",
                Verdict.REFUTED,
                counterexample=("a", "f1", "b"),
                detail="bad path",
            ),
        )
        report = render_report(results)
        lines = report.splitlines()
        assert lines[0] == "REFUTED  c1 [forall] -- bad path"
        assert lines[1] == "  path: a -> f1 -> b"

    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_refuted_without_counterexample_has_no_path_line(self):
        results = (_result("c1", Verdict.REFUTED, detail="bad"),)
        report = render_report(results)
        assert "path:" not in report


class TestSummaryLine:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_summary_line_counts(self):
        results = (
            _result("c1", Verdict.PROVED),
            _result("c2", Verdict.PROVED),
            _result("c3", Verdict.REFUTED),
            _result("c4", Verdict.ASSUMED),
            _result("c5", Verdict.EVIDENCED),
        )
        report = render_report(results)
        assert "5 claim(s): 2 proved, 1 refuted, 1 assumed, 1 evidenced" in report


class TestAssumptionLedger:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_ledger_section_present_when_assumed_exists(self):
        results = (_result("c1", Verdict.ASSUMED, detail="assumed by alice"),)
        report = render_report(results)
        assert "## Assumption ledger" in report
        assert "c1: assumed by alice" in report

    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_ledger_section_absent_without_assumed(self):
        results = (_result("c1", Verdict.PROVED, detail="proved"),)
        report = render_report(results)
        assert "## Assumption ledger" not in report


class TestSummarize:
    # frob:tests src/frob/strata/_report.py::summarize kind="unit"
    def test_all_four_keys_always_present(self):
        counts = summarize(())
        assert counts == {"proved": 0, "refuted": 0, "assumed": 0, "evidenced": 0}

    # frob:tests src/frob/strata/_report.py::summarize kind="unit"
    def test_counts_match_results(self):
        results = (
            _result("c1", Verdict.PROVED),
            _result("c2", Verdict.REFUTED),
            _result("c3", Verdict.REFUTED),
        )
        counts = summarize(results)
        assert counts == {"proved": 1, "refuted": 2, "assumed": 0, "evidenced": 0}


class TestColor:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_color_false_emits_pure_ascii(self):
        results = (_result("c1", Verdict.REFUTED, detail="bad"),)
        report = render_report(results, color=False)
        assert "\x1b" not in report
        assert all(ord(ch) < 128 for ch in report)

    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_color_true_wraps_tags_with_ansi(self):
        results = (_result("c1", Verdict.REFUTED, detail="bad"),)
        report = render_report(results, color=True)
        assert "\x1b[" in report


class TestDeterminism:
    # frob:tests src/frob/strata/_report.py::render_report kind="unit"
    def test_same_input_renders_identical_string(self):
        results = (
            _result("c1", Verdict.PROVED, detail="proved"),
            _result("c2", Verdict.REFUTED, counterexample=("a", "b"), detail="bad"),
            _result("c3", Verdict.ASSUMED, detail="assumed by carol"),
        )
        assert render_report(results) == render_report(results)
