"""Direct (non-CLI) unit tests for frob.check's public functions and CheckResult."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Callable

from frob.check import (
    CheckResult,
    _collect_results,
    detect_project_type,
    run_check,
    run_check_cpp,
    run_check_rust,
    run_check_ts,
)
from frob.process.parsers.common import Diagnostic, ToolResult


class TestCheckResultCounts:
    def test_total_errors_sums_across_results(self) -> None:
        # frob:tests src/frob/check/__init__.py::CheckResult.total_errors kind="unit"
        result = CheckResult(
            path=".",
            results=[
                ToolResult(
                    tool="a",
                    diagnostics=[
                        Diagnostic(severity="error", message="x"),
                        Diagnostic(severity="warning", message="y"),
                    ],
                ),
                ToolResult(
                    tool="b",
                    diagnostics=[Diagnostic(severity="error", message="z")],
                ),
            ],
        )
        assert result.total_errors == 2

    def test_total_warnings_sums_across_results(self) -> None:
        # frob:tests src/frob/check/__init__.py::CheckResult.total_warnings kind="unit"
        result = CheckResult(
            path=".",
            results=[
                ToolResult(
                    tool="a",
                    diagnostics=[
                        Diagnostic(severity="warning", message="x"),
                        Diagnostic(severity="warning", message="y"),
                    ],
                ),
                ToolResult(tool="b", diagnostics=[]),
            ],
        )
        assert result.total_warnings == 2

    def test_zero_results_is_zero(self) -> None:
        result = CheckResult(path=".", results=[])
        assert result.total_errors == 0
        assert result.total_warnings == 0


class TestRunCheck:
    def test_all_stages_skipped_returns_empty_result_for_root(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        result = run_check(
            tmp_path,
            skip_ruff=True,
            skip_ty=True,
            skip_arch=True,
            skip_cycle=True,
            skip_dup=True,
            skip_bind=True,
            skip_exports=True,
            skip_gates=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []
        assert result.total_errors == 0


class TestRunCheckCpp:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_cpp kind="unit"
        result = run_check_cpp(
            tmp_path,
            skip_build=True,
            skip_clang_tidy=True,
            skip_clang_format=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestRunCheckRust:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_rust kind="unit"
        result = run_check_rust(
            tmp_path,
            skip_check=True,
            skip_clippy=True,
            skip_fmt=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestRunCheckTs:
    def test_all_stages_skipped_returns_empty_result(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::run_check_ts kind="unit"
        result = run_check_ts(
            tmp_path,
            skip_tsc=True,
            skip_eslint=True,
            skip_prettier=True,
            skip_tests=True,
        )
        assert isinstance(result, CheckResult)
        assert result.path == str(tmp_path)
        assert result.results == []


class TestDetectProjectType:
    def test_cargo_toml_is_rust(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/__init__.py::detect_project_type kind="unit"
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        assert detect_project_type(tmp_path) == "rust"

    def test_cmakelists_is_cpp(self, tmp_path: Path) -> None:
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.20)\n"
        )
        assert detect_project_type(tmp_path) == "cpp"

    def test_pyproject_is_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        assert detect_project_type(tmp_path) == "python"

    def test_package_json_and_tsconfig_is_typescript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "tsconfig.json").write_text("{}")
        assert detect_project_type(tmp_path) == "typescript"

    def test_package_json_alone_is_typescript(self, tmp_path: Path) -> None:
        """T-0404 finding 11: `detect_project_type` and
        `app.check_runner._detected_types` must agree on what counts as a
        TypeScript repo -- `_detected_types` only requires `package.json`,
        so this single-winner detector must not additionally demand
        `tsconfig.json`.
        """
        (tmp_path / "package.json").write_text("{}")
        assert detect_project_type(tmp_path) == "typescript"

    def test_no_sentinel_is_unknown(self, tmp_path: Path) -> None:
        assert detect_project_type(tmp_path) == "unknown"


class TestRunGatesQueueFailure:
    """T-0102: a malformed ticket queue must fail check loudly, not vanish."""

    def test_malformed_tickets_md_is_hard_error_not_silent_skip(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        # Deliberately malformed: a `## T-0001` marker with no ```yaml
        # frontmatter fence at all -- exactly the class of hand-edit that
        # made load_queue fail during the T-0067/68 review.
        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n<!-- ticket:T-0001 -->\nnot even close to yaml\n"
        )
        result = _run_gates(tmp_path)
        # A load failure (this test's case) always reports as the single
        # "gates" ToolResult, never the T-0420 per-family list.
        assert isinstance(result, ToolResult)
        assert result.tool == "gates"
        assert result.exit_code != 0, (
            "a failed ticket queue load must fail the gates stage, "
            "never exit 0 with gates silently skipped"
        )
        assert "skipped" not in result.summary
        assert any(d.severity == "error" for d in result.diagnostics)


class TestRunGatesDelta:
    """T-0095: --delta filters to violations new since .frob/baseline."""

    def test_no_baseline_falls_back_to_full_set_with_warning(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from frob.check._python import _run_gates

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        # T-0420: a successful run now reports as a list of per-family
        # ToolResults plus a trailing gate-summary line, not one "gates"
        # ToolResult -- flatten diagnostics across the list to check the
        # fallback warning landed somewhere in it.
        results = _run_gates(tmp_path, delta=True)
        assert isinstance(results, list)
        assert any(r.tool == "gate-summary" for r in results)
        all_diags = [d for r in results for d in r.diagnostics]
        assert any("no baseline found" in d.message for d in all_diags)

    def test_stale_baseline_falls_back_to_full_set_with_warning(
        self, tmp_path: Path
    ) -> None:
        from frob.check._python import _run_gates
        from frob.gates import Severity, Violation, stamp_baseline

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        (tmp_path / "a.py").write_text("x = 1\n")
        stamp_baseline(
            tmp_path,
            (
                Violation(
                    rule="R1", severity=Severity.WARN, file="a.py", line=1, message="m"
                ),
            ),
        )
        (tmp_path / "a.py").write_text("x = 2\n")
        # T-0420: same list-of-ToolResults shape as the no-baseline case above.
        results = _run_gates(tmp_path, delta=True)
        assert isinstance(results, list)
        all_diags = [d for r in results for d in r.diagnostics]
        assert any("stale" in d.message for d in all_diags)


class TestSummarySeverityHonesty:
    """T-0228: a passing gate must never render its warn-class findings as a
    bare, alarming 'violation(s)' count -- every summary line splits into
    errors/warnings (and waived, for gates)."""

    def test_warn_only_gate_summary_splits_errors_and_warnings(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_gates kind="unit"
        from typani import Ok

        from frob.check._python import _run_gates
        from frob.gates import GateReport, GateStats, Severity, Violation

        report = GateReport(
            violations=(
                Violation(
                    rule="R1",
                    severity=Severity.WARN,
                    file="a.py",
                    line=1,
                    message="warn finding",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr(
            "frob.gates.run_gates",
            lambda cfg: Ok(report),  # noqa: ARG005
        )
        (tmp_path / "tickets.md").write_text("# Tickets\n")
        # T-0420: the overall totals now live on the trailing gate-summary
        # ToolResult, not a single "gates" result.
        results = _run_gates(tmp_path)
        assert isinstance(results, list)
        result = next(r for r in results if r.tool == "gate-summary")

        assert result.exit_code == 0, "warn-only findings must not fail the stage"
        assert "violation" not in result.summary, (
            "warn-class findings on a passing gate must never be labeled "
            f"'violation(s)': got {result.summary!r}"
        )
        assert "1 warning" in result.summary
        assert "0 error" in result.summary
        assert "0 waived" in result.summary

    def test_cycle_summary_splits_by_severity(self) -> None:
        # T-0523: this test directly imports and calls
        # _severity_counts_summary, never _run_cycle -- the frob:tests
        # binding was stale/wrong (a COV006 finding correctly caught it).
        # frob:tests src/frob/check/_python.py::_severity_counts_summary kind="unit"  # noqa: E501
        from frob.check._python import _severity_counts_summary
        from frob.process.parsers.common import Diagnostic

        diags = [Diagnostic(severity="warning", message="import cycle: a -> b -> c")]
        summary = _severity_counts_summary(diags, no_issues="no cycles")

        assert "violation" not in summary
        assert "found" not in summary, (
            "a bare 'N cycle(s) found' phrasing reads as alarming even when "
            "the finding is only warn-class"
        )
        assert summary == "1 warning"


class TestDupArchWaiverAwareSummaries:
    """T-0375: the frob-dup and frob-arch stage summaries must subtract
    findings already covered by a reasoned `frob:waive`, mirroring the
    gates stage's error/warning/waived split -- a waived group/finding
    stays listed (as a `note` diagnostic), never hidden, but no longer
    inflates the headline count."""

    _DUP_BODY = (
        "    total = 0\n"
        "    for item in items:\n"
        "        total = total + item\n"
        "        if total > 100:\n"
        "            total = 100\n"
        "    return total\n"
    )
    _WAIVER = '# frob:waive DUP001 reason="documented shared shape, T-0375 fixture"\n'

    def _dup_source(self, *, waive_foo: bool = False, waive_bar: bool = False) -> str:
        """Two functions with an identical (exact-clone) body, either
        optionally preceded by a `frob:waive` directive."""
        foo_waiver = self._WAIVER if waive_foo else ""
        bar_waiver = self._WAIVER if waive_bar else ""
        lines = [f"{foo_waiver}def foo(items):\n{self._DUP_BODY}"]
        lines.append(f"{bar_waiver}def bar(items):\n{self._DUP_BODY}")
        return "\n\n".join(lines)

    def test_dup001_waived_group_excluded_from_headline_but_listed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # Full-coverage rule (T-0375 review fix): the group has exactly two
        # fragments (foo, bar) -- waiving BOTH covers the whole group.
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source(waive_foo=True, waive_bar=True))

        result = _run_dup(tmp_path)

        assert result.summary == "0 duplicate groups (1 waived)", result.summary
        waived_diags = [d for d in result.diagnostics if d.severity == "note"]
        assert len(waived_diags) == 1
        assert "waived:" in waived_diags[0].message
        assert not any(d.severity == "warning" for d in result.diagnostics)

    def test_dup001_partial_group_waiver_does_not_hide_whole_group(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # T-0375 review fix: waiving only ONE fragment of a 2-fragment group
        # must NOT mark the group waived -- an "any fragment matches"
        # (rather than "every fragment matches") rule would silently treat
        # a partially-reasoned-about group as fully accounted for.
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source(waive_foo=True))

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group", result.summary
        assert any(d.severity == "warning" for d in result.diagnostics)
        assert not any(d.severity == "note" for d in result.diagnostics)

    def test_dup001_waiver_on_shared_symbol_does_not_hide_distinct_superset_group(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # T-0375 review fix (reviewer-reproduced regression): frob.dup's
        # legacy scanner deliberately lets one symbol sit in BOTH an exact
        # group and a DISTINCT, larger renamed-superset group --
        # `_renamed_groups` only drops a renamed group when it is WHOLLY
        # covered by a single exact group (frob/dup/_legacy.py). Here foo/
        # bar form an exact group; foo/bar/baz (alpha-renamed) form a
        # separate renamed group containing the new, un-reasoned-about baz.
        # Fully waiving DUP001 on foo+bar (covering the exact group) must
        # NOT also silently exclude the renamed group -- baz's fragment is
        # not covered by any waiver, so that group must still count.
        from frob.check._python import _run_dup

        renamed_body = (
            "    result = 0\n"
            "    for value in values:\n"
            "        result = result + value\n"
            "        if result > 100:\n"
            "            result = 100\n"
            "    return result\n"
        )
        source = (
            self._dup_source(waive_foo=True, waive_bar=True)
            + "\n\n"
            + f"def baz(values):\n{renamed_body}"
        )
        (tmp_path / "a.py").write_text(source)

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group (1 waived)", result.summary
        codes = {(d.severity, d.code) for d in result.diagnostics}
        assert ("note", "exact") in codes, (
            "the fully-waived exact {foo,bar} group must still be listed, "
            f"not hidden: {result.diagnostics}"
        )
        assert ("warning", "renamed") in codes, (
            "the renamed {foo,bar,baz} superset group must still count "
            f"unaccounted -- baz was never waived: {result.diagnostics}"
        )

    def test_dup001_waiving_every_fragment_of_superset_group_waives_it_too(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        # The flip side of the above: once baz is ALSO waived, the renamed
        # superset group is fully covered and is excluded from the
        # headline too -- full coverage, not "never waivable".
        from frob.check._python import _run_dup

        renamed_body = (
            "    result = 0\n"
            "    for value in values:\n"
            "        result = result + value\n"
            "        if result > 100:\n"
            "            result = 100\n"
            "    return result\n"
        )
        source = (
            self._dup_source(waive_foo=True, waive_bar=True)
            + "\n\n"
            + f"{self._WAIVER}def baz(values):\n{renamed_body}"
        )
        (tmp_path / "a.py").write_text(source)

        result = _run_dup(tmp_path)

        assert result.summary == "0 duplicate groups (2 waived)", result.summary
        assert not any(d.severity == "warning" for d in result.diagnostics)

    def test_dup001_unwaived_group_still_counts(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_run_dup kind="unit"
        from frob.check._python import _run_dup

        (tmp_path / "a.py").write_text(self._dup_source())

        result = _run_dup(tmp_path)

        assert result.summary == "1 duplicate group", result.summary
        assert any(d.severity == "warning" for d in result.diagnostics)
        assert not any(d.severity == "note" for d in result.diagnostics)

    def _arch_source(self, *, waiver: str = "") -> str:
        """A long AND structurally complex function (fires ARCH001's
        long-function rule), optionally preceded by a `frob:waive`."""
        lines = [waiver] if waiver else []
        lines += [
            "def complex_long(items):",
            '    """Long and complex."""',
            "    total = 0",
        ]
        for i in range(30):
            lines.append(
                f"    try:\n        if items[{i}] and total:\n"
                "            for x in range(3):\n"
                "                if x:\n                    total += x\n"
                "    except Exception:\n        pass"
            )
        lines.append("    return total")
        return "\n".join(lines) + "\n"

    def test_arch001_waived_long_function_excluded_from_headline_but_listed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        waiver = '# frob:waive ARCH001 reason="justified, T-0375 fixture"\n'
        (tmp_path / "src" / "big.py").write_text(self._arch_source(waiver=waiver))

        result = _run_arch(tmp_path / "src")

        assert "0 warnings (1 waived)" in result.summary, result.summary
        waived = [
            d
            for d in result.diagnostics
            if d.code == "long-function" and d.severity == "note"
        ]
        assert len(waived) == 1
        assert "waived:" in waived[0].message
        assert not any(
            d.code == "long-function" and d.severity == "warning"
            for d in result.diagnostics
        )

    def test_arch001_unwaived_long_function_still_counts(self, tmp_path: Path) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "big.py").write_text(self._arch_source())

        result = _run_arch(tmp_path / "src")

        assert "1 warning" in result.summary
        assert "waived" not in result.summary
        assert any(
            d.code == "long-function" and d.severity == "warning"
            for d in result.diagnostics
        )

    @staticmethod
    def _calibrated_source(fn_name: str = "do_work") -> str:
        """A function long enough to trip `frob.arch.analyze_project`'s bare
        30-line `max_function_lines` default but short enough to stay under
        the calibrated 60-line default (T-0373's frob.toml [arch] table),
        and structurally complex enough (>=8 branches) to pass
        `_py_is_complex`'s cyclomatic-proxy filter. Mirrors
        `tests/test_gates.py::_complex_function_source`."""
        lines = [f"def {fn_name}(cfg):", "    result = {}"]
        for i in range(8):
            lines.append(f'    if cfg.get("flag_{i}"):')
            lines.append(f'        result["k{i}"] = {i}')
        for i in range(20):
            lines.append(f'    step_{i} = cfg.get("step_{i}", "default")')
        lines.append("    return result, " + ", ".join(f"step_{i}" for i in range(20)))
        return "\n".join(lines) + "\n"

    def test_arch_stage_uses_calibrated_default_not_library_default(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        # T-0442: without threading load_arch_config's calibrated 60-line
        # default through, this tool-summary stage would use
        # analyze_project's bare 30-line default and flag this ~39-line
        # function -- disagreeing with ARCH001's own T-0373-fixed gate over
        # the identical source. No frob.toml present: the calibrated
        # default alone must suppress the finding.
        from frob.arch import analyze_project
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text(self._calibrated_source())

        raw_result = analyze_project(tmp_path / "src")
        assert "long-function" in {s.category for s in raw_result.suggestions}, (
            "fixture must trip the library's own bare default to prove anything"
        )

        result = _run_arch(tmp_path / "src")

        assert not any(d.code == "long-function" for d in result.diagnostics), (
            result.diagnostics
        )

    def test_arch_stage_respects_explicit_frob_toml_override(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_arch kind="unit"
        # T-0442: an explicit frob.toml [arch] override (well below both the
        # library default and the calibrated default) must still surface,
        # proving _run_arch actually reads frob.toml via load_arch_config
        # rather than a hardcoded calibrated constant.
        from frob.check._python import _run_arch

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text(self._calibrated_source())
        (tmp_path / "src" / "frob.toml").write_text("[arch]\nmax_function_lines = 20\n")

        result = _run_arch(tmp_path / "src")

        assert any(d.code == "long-function" for d in result.diagnostics), (
            result.diagnostics
        )


def test_check_run_check_arch_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/check kind="integration"
    # Exercises frob.check across a real analysis boundary: run_check with the
    # arch stage drives frob.arch.analyze_project over a real source tree and
    # aggregates its diagnostics into a CheckResult. A file with a deliberately
    # over-long AND structurally complex function (T-0289: a merely long-but-
    # flat body like a linear `x0 = 0; x1 = 1; ...` block no longer fires,
    # by design) must surface a frob-arch diagnostic, proving the
    # orchestration wiring reaches the analyzer and back, not a stub.
    branches = "\n".join(
        f"    if items[{i}] and total:\n        total += items[{i}]" for i in range(30)
    )
    body = f"def huge(items):\n    total = 0\n{branches}\n    return total\n"
    (tmp_path / "big.py").write_text(body)

    result = run_check(tmp_path, only=frozenset({"arch"}))
    assert isinstance(result, CheckResult)
    arch_results = [r for r in result.results if r.tool in {"frob-arch"}]
    assert arch_results, "arch stage should have produced a ToolResult"
    codes = {d.code for r in arch_results for d in r.diagnostics}
    assert "long-function" in codes


class TestCollectResultsLogLevelRace:
    """T-0122: concurrent check tasks racing the shared stdout log handler
    must never leave it stuck, or `run_check`'s caller silently loses its
    final summary log with no exception and exit code 0 (the vacuous-pass
    class T-0102 targets)."""

    def test_racing_tasks_restore_original_stdout_handler_level(self) -> None:
        # frob:tests src/frob/check/__init__.py::_collect_results kind="unit"
        # Mirrors the real bug: frob.arch.analyze_project and
        # frob.dup.find_duplicates each save/restore the shared root
        # logger's stdout handler level around their work (to keep
        # frob.lang's per-parse INFO logs off stdout). Two such
        # save/restore blocks racing on DIFFERENT threads, with staggered
        # timing, can interleave so the LAST one to exit restores a level
        # that was already stale -- leaving the handler stuck. This
        # reproduces that interleaving directly against `_collect_results`
        # (no need for the real, slow arch/dup analyses).
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        try:

            def racy_quiet(delay_before: float, delay_after: float):
                def _task() -> None:
                    saved = handler.level
                    handler.setLevel(logging.WARNING)
                    time.sleep(delay_before)
                    time.sleep(delay_after)
                    handler.setLevel(saved)

                return _task

            # Task A enters first and exits LAST (long inner sleep) --
            # task B enters second (sees A's WARNING as its "saved" level)
            # and exits FIRST. B's restore is a no-op (WARNING->WARNING);
            # A's restore correctly puts DEBUG back... UNLESS B starts
            # after A already flipped the level, which is exactly what
            # the stagger below forces, leaving the classic stuck case
            # when three or more overlap. Assert on the OUTCOME, not the
            # interleaving mechanics: after _collect_results returns, the
            # level must equal what it was before the batch ran no matter
            # how the tasks raced.
            tasks: list[Callable[[], ToolResult | list[ToolResult] | None]] = [
                lambda: (racy_quiet(0.05, 0.0)(), None)[1],
                lambda: (racy_quiet(0.0, 0.05)(), None)[1],
                lambda: (racy_quiet(0.02, 0.02)(), None)[1],
            ]
            before = handler.level
            _collect_results(tasks)
            assert handler.level == before, (
                "_collect_results must restore the stdout handler level "
                "after racing tasks, or the caller's own summary log can "
                "be silently swallowed"
            )
        finally:
            root_logger.removeHandler(handler)

    def test_all_none_tasks_still_restore_level(self) -> None:
        # frob:tests src/frob/check/__init__.py::_collect_results kind="unit"
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        try:

            def flip_and_leave_stuck() -> None:
                handler.setLevel(logging.WARNING)

            before = handler.level
            _collect_results([lambda: (flip_and_leave_stuck(), None)[1]])
            assert handler.level == before
        finally:
            root_logger.removeHandler(handler)


class TestCheckBuildsGraphOnce:
    """T-0122: `frob check` must build the obligation graph exactly once
    per invocation, never once per stage that happens to touch it."""

    def test_run_check_calls_build_graph_exactly_once(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests src/frob/check/__init__.py::run_check kind="unit"
        import frob.gates as gates_mod

        (tmp_path / "tickets.md").write_text("# Tickets\n")
        calls: list[int] = []
        real_build_graph = gates_mod.build_graph

        def counting_build_graph(*args, **kwargs):
            calls.append(1)
            return real_build_graph(*args, **kwargs)

        monkeypatch.setattr(gates_mod, "build_graph", counting_build_graph)

        run_check(tmp_path, only=frozenset({"gates", "arch", "dup"}))

        assert len(calls) == 1, (
            f"build_graph called {len(calls)} times in one frob check run "
            "(expected exactly 1) -- a stage is rebuilding the graph "
            "instead of reusing the one build"
        )
