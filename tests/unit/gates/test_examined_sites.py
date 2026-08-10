"""Tests for `frob.gates._coverage_sites` (T-1921): the per-site
analysis-coverage substrate filed from T-1904's investigation of the
falsified T-1579 WAIVE004 escape (`_rule_has_live_finding`, reverted
after deleting 55 live waivers). The single property every test here
ultimately checks: it must be impossible for a site the analysis did
not cover to be reported as covered."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._coverage_sites import (
    attach_examined_sites,
    is_family_instrumented,
    site_examined,
)
from frob.gates._models import GateReport, GateStats


def _empty_report(
    *, examined_sites: dict[str, frozenset[str]] | None = None
) -> GateReport:
    """Test helper: a `GateReport` with no violations, just the `stats`
    shape `site_examined`/`is_family_instrumented` read from."""
    return GateReport(
        violations=(),
        waived=(),
        stats=GateStats(examined_sites=examined_sites or {}),
    )


# frob:ticket T-1921
class TestSiteExaminedSoundness:
    """`site_examined`'s core contract: a family absent from
    `examined_sites` is "not instrumented", never silently "examined and
    clean" -- the exact distinction whose absence let the falsified
    T-1579 escape delete 55 live waivers."""

    def test_uninstrumented_family_reports_not_examined(self) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::site_examined kind="unit"
        report = _empty_report()
        assert (
            site_examined(report.stats, "totally_unknown_family", "any/file.py")
            is False
        )

    def test_instrumented_family_reports_true_for_a_known_site(self) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::site_examined kind="unit"
        report = _empty_report(examined_sites={"archgate": frozenset({"a.py", "b.py"})})
        assert site_examined(report.stats, "archgate", "a.py") is True

    def test_instrumented_family_reports_false_for_an_unexamined_site(self) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::site_examined kind="unit"
        report = _empty_report(examined_sites={"archgate": frozenset({"a.py"})})
        assert site_examined(report.stats, "archgate", "c.py") is False

    def test_instrumented_but_empty_family_still_reports_false_for_any_site(
        self,
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::site_examined kind="unit"
        # An instrumented family that genuinely examined nothing this run
        # (empty frozenset) must answer identically to "not instrumented"
        # for a per-site query -- the caller-visible signal is the same
        # (no proof of coverage), only `is_family_instrumented` should
        # tell the two situations apart.
        report = _empty_report(examined_sites={"archgate": frozenset()})
        assert site_examined(report.stats, "archgate", "anything.py") is False


# frob:ticket T-1921
class TestIsFamilyInstrumented:
    """`is_family_instrumented` distinguishes "not instrumented" from
    "instrumented, found nothing" -- the one case `site_examined` alone
    collapses (both answer False for a per-site query, by design)."""

    def test_absent_family_is_not_instrumented(self) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::is_family_instrumented \
        # kind="unit"
        report = _empty_report()
        assert is_family_instrumented(report.stats, "archgate") is False

    def test_present_empty_family_is_instrumented(self) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::is_family_instrumented \
        # kind="unit"
        report = _empty_report(examined_sites={"archgate": frozenset()})
        assert is_family_instrumented(report.stats, "archgate") is True


# frob:ticket T-1921
# frob:ticket T-1943
class TestAttachExaminedSites:
    """`attach_examined_sites` populates `archgate` for real against a
    fixture tree, and leaves every other family absent -- the acceptance
    property T-1921's brief demanded a regression test for: a partially-
    examined run's uninstrumented families must never look covered."""

    def test_archgate_examined_sites_include_a_real_python_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, "archgate", "m.py") is True

    def test_archgate_examined_sites_exclude_an_unparseable_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        # A file with no tree-sitter grammar for its extension (arch.py's
        # own `_analyze_one_file` early-returns before checks run) must
        # NOT be reported examined -- proves this substrate reflects
        # `_analyze_one_file`'s real success/failure outcome, not merely
        # "was in the walk's candidate list".
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, "archgate", "data.bin") is False

    # frob:ticket T-1943
    def test_families_this_module_does_not_know_about_stay_absent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        # The acceptance property, stated directly: a family this
        # substrate has no reporter for (today: everything except
        # "archgate"/"perf"/"strata"/"graph"/"vet") must never be claimed
        # examined by this call, no matter what the fixture tree contains
        # -- an uninstrumented family reports "not examined", never
        # "examined and clean".
        (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert is_family_instrumented(report.stats, "totally_unknown_family") is False
        assert (
            site_examined(report.stats, "totally_unknown_family", "m.py") is False
        )

    def test_preserves_examined_sites_a_prior_caller_already_attached(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        # A family key this module's own reporters do not own (say, a
        # future caller's own family) must survive a second enrichment
        # call untouched, not get silently dropped by the merge.
        pre = _empty_report(examined_sites={"future_family": frozenset({"x.py"})})
        report = attach_examined_sites(pre, tmp_path)
        assert site_examined(report.stats, "future_family", "x.py") is True


# frob:ticket T-1943
class TestPerfGraphVetExaminedSitesShareOneFixtureShape:
    """`_perf_examined_sites`/`_graph_examined_sites`/`_vet_examined_sites`
    all agree on the same two-case fixture shape (a plain `.py` file is
    examined, an unsupported-extension file is not) -- parametrized here
    instead of three (DUP001/DUP002-flagged) near-identical classes, one
    per family, so the shared property reads as ONE assertion repeated
    over families rather than three copies that could quietly drift out
    of sync with each other."""

    # frob:ticket T-1943
    # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites kind="unit"
    @pytest.mark.parametrize("family", ["perf", "graph", "vet"])
    def test_a_parseable_python_file_is_examined(
        self, tmp_path: Path, family: str
    ) -> None:
        (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, family, "m.py") is True

    # frob:ticket T-1943
    # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites kind="unit"
    @pytest.mark.parametrize("family", ["perf", "vet"])
    def test_an_unsupported_extension_is_not_examined(
        self, tmp_path: Path, family: str
    ) -> None:
        # graph has no extension allowlist of its own (build_graph's own
        # extension gate is frob.lang.supported_extensions, a strict
        # superset of perf's tree-sitter-only set) so it is exercised by
        # its own dedicated test below instead of joining this pair.
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, family, "data.bin") is False

    # frob:ticket T-1943
    def test_graph_reports_false_for_a_file_never_written(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        (tmp_path / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, "graph", "nonexistent.py") is False


# frob:ticket T-1943
class TestStrataExaminedSites:
    """`_strata_examined_sites`: a well-formed `.strata` file under
    `design/` is examined; a malformed one that fails to parse is not --
    the same real success/failure distinction `load_design_ids`'s own
    `.errors` collects."""

    # frob:ticket T-1943
    def test_a_parseable_strata_file_is_examined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        design = tmp_path / "design"
        design.mkdir()
        (design / "m.strata").write_text(
            'module m\n'
            'node client : foreign { clearance Public; }\n'
            'node api : authenticated { clearance Internal; }\n'
            'flow f_login : client -> api\n',
            encoding="utf-8",
        )
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, "strata", "design/m.strata") is True

    # frob:ticket T-1943
    def test_an_unparseable_strata_file_is_not_examined(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_coverage_sites.py::attach_examined_sites \
        # kind="unit"
        design = tmp_path / "design"
        design.mkdir()
        (design / "bad.strata").write_text("this is not valid strata {{{", encoding="utf-8")
        report = attach_examined_sites(_empty_report(), tmp_path)
        assert site_examined(report.stats, "strata", "design/bad.strata") is False
