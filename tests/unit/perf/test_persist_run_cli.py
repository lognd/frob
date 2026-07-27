"""T-0712 mutation-evidence hardening (TEST016): behavioral CLI-level tests
invoking `frob.app.perf_runner.run` directly (the same production function
`frob perf collect`/`frob perf hot` dispatch to) and asserting on precise
rendered stdout/JSON values -- strong enough to fail on each of the
`_persist_run`/`_hot_sort_key`/`_print_findings` operator mutants a land
review found unkilled by the ticket's original evidence (line/mutation:
397 `or`->`and`, 403 `==`->`!=`, 405 `+`->`-`, 437x2 list `+`->`-`, 454
`or`->`and`, 455 `*`->`/`, 521 `==`->`!=` in src/frob/app/perf_runner.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.perf_runner import run as perf_run
from frob.perf._sketch_store import _close_all


@pytest.fixture(autouse=True)
def _teardown_sketch_store():
    yield
    _close_all()


def _perf_script(blocks: list[tuple[float, str]]) -> str:
    """Build a `perf script`-format profile from `(weight, frame_loc)`
    pairs, one blank-line-separated block (one `SampledStack`) per pair --
    `frob.perf._collectors.parse_perf_script`'s own format, matching
    `tests/system/test_cli_perf.py`'s fixture shape."""
    parts = []
    for weight, loc in blocks:
        parts.append(f"myprog  1 1 {weight}: 1 cycles:\n\t401234 fn+0x10 ({loc})\n")
    return "\n".join(parts)


def _write_workload(tmp_path: Path) -> tuple[Path, int]:
    """A tiny python module with one function -- returns (path, line) of
    a line inside the function body (a real, resolvable Section)."""
    text = (
        "# module comment, no enclosing function -- unattributed by design\n"
        "def hot_loop():\n"
        "    total = 0\n"
        "    total += 1\n"
        "    return total\n"
    )
    path = tmp_path / "workload.py"
    path.write_text(text)
    return path, 3  # "    total = 0" -- inside hot_loop's body


class TestPersistRunDefaultPath:
    """Kills the line-397 `cfg.perf_path or Path(".")` Or/And mutant: a
    missing `--path` (perf_path left `None`, exactly as an un-set config
    field would be) must resolve to the current working directory, not
    crash."""

    def test_missing_perf_path_resolves_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        workload, line = _write_workload(tmp_path)
        profile = tmp_path / "p.script"
        profile.write_text(_perf_script([(1.0, f"{workload}:{line}")]))

        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(
            perf_command="collect", perf_path=None, perf_file=profile, perf_json=True
        )
        # Correct code: root = Path(".").resolve() == tmp_path -- runs clean.
        # Mutated (`and`): None and Path(".") -> None -> None.resolve() raises.
        perf_run(cfg)
        capsys.readouterr()
        assert (tmp_path / ".frob" / "perf" / "ratchet_findings.json").is_file()


class TestPersistRunUnattributedExclusionAndWeightSum:
    """Kills the line-403 `== UNATTRIBUTED_SECTION_ID` Eq/NotEq mutant and
    the line-405 `+= hit.weight` Add/Sub mutant together: two attributed
    samples (weight 1.0 each) at the same real section, plus one
    unattributed sample (a location with no enclosing function), must
    persist exactly one stored section whose total observation weight is
    the SUM (2.0), not zero/negative and not excluded entirely."""

    def test_only_attributed_section_persists_with_summed_weight(
        self, tmp_path: Path, capsys
    ) -> None:
        workload, line = _write_workload(tmp_path)
        profile = tmp_path / "p.script"
        profile.write_text(
            _perf_script(
                [
                    (1.0, f"{workload}:{line}"),
                    (1.0, f"{workload}:{line}"),
                    # Line 1 is a bare comment outside any function --
                    # build_section_index has no Section covering it, so
                    # this resolves to UNATTRIBUTED_SECTION_ID.
                    (1.0, f"{workload}:1"),
                ]
            )
        )

        collect_cfg = AppConfig(
            perf_command="collect", perf_path=tmp_path, perf_file=profile
        )
        perf_run(collect_cfg)
        capsys.readouterr()

        hot_cfg = AppConfig(perf_command="hot", perf_path=tmp_path, perf_json=True)
        perf_run(hot_cfg)
        out = capsys.readouterr().out
        rows = json.loads(out)

        # Eq/NotEq mutant: with the check inverted, the ATTRIBUTED hits get
        # skipped instead of the unattributed one -- nothing real ever
        # reaches `sections.get(...)`, so the store stays empty and this
        # list is `[]` instead of exactly one row.
        assert len(rows) == 1, rows
        assert "hot_loop" in rows[0]["label"]
        # Add/Sub mutant: subtraction collapses two +1.0 weights to a
        # negative total (0.0 - 1.0 - 1.0 == -2.0); `add_value` silently
        # drops any negative observation (logs and returns the sketch
        # unchanged), so the stored sketch stays EMPTY and p50 reads 0.0
        # instead of the real summed weight, 2.0.
        assert rows[0]["p50"] == pytest.approx(2.0, rel=0.05)


class TestHotSortKeyMetricSelection:
    """Kills the line-521 `if by == "p90"` Eq/NotEq mutant: two stored
    sections ranked in OPPOSITE order under `--by p90` vs the default
    `--by p50xcount` prove the metric selector actually branches."""

    def test_by_p90_and_by_p50xcount_disagree_on_order(
        self, tmp_path: Path, capsys
    ) -> None:
        from frob.perf._sketch_store import SketchStoreConfig, put_sketch
        from frob.stats._sketch import add_value, new_sketch

        config = SketchStoreConfig()

        # Section "spike": one big observation (p50 == p90 == 100), low
        # count -> p50 * count == 100 (small under p50xcount).
        spike_sketch = add_value(new_sketch(alpha=config.alpha), 100.0)
        put_sketch(
            tmp_path, "key-spike", "loop", spike_sketch, config, label="pkg.spike"
        )

        # Section "frequent": 50 small observations of 10.0 each -- p50 ==
        # p90 == 10 (loses on p90), but p50 * count == 500 (wins on
        # p50xcount).
        frequent_sketch = new_sketch(alpha=config.alpha)
        for _ in range(50):
            frequent_sketch = add_value(frequent_sketch, 10.0)
        put_sketch(
            tmp_path,
            "key-frequent",
            "loop",
            frequent_sketch,
            config,
            label="pkg.frequent",
        )

        p90_cfg = AppConfig(
            perf_command="hot", perf_path=tmp_path, perf_by="p90", perf_json=True
        )
        perf_run(p90_cfg)
        p90_rows = json.loads(capsys.readouterr().out)
        assert [r["label"] for r in p90_rows] == ["pkg.spike", "pkg.frequent"]

        count_cfg = AppConfig(
            perf_command="hot",
            perf_path=tmp_path,
            perf_by="p50xcount",
            perf_json=True,
        )
        perf_run(count_cfg)
        count_rows = json.loads(capsys.readouterr().out)
        assert [r["label"] for r in count_rows] == ["pkg.frequent", "pkg.spike"]


class TestRatchetFindingRendering:
    """Kills the line-454 `finding.label or finding.section_key` Or/And
    mutant and the line-455 `worst_relative_shift * 100` Mult/Div mutant:
    a real regression (baseline weight 1.0, then weight 10.0 for the SAME
    section) must render the section's LABEL (not its opaque hash key)
    and the EXACT percentage (900%, not a divided-down ~0%)."""

    def test_regression_prints_label_and_exact_percentage(
        self, tmp_path: Path, capsys
    ) -> None:
        workload, line = _write_workload(tmp_path)

        baseline_profile = tmp_path / "baseline.script"
        baseline_profile.write_text(_perf_script([(1.0, f"{workload}:{line}")]))
        baseline_cfg = AppConfig(
            perf_command="collect", perf_path=tmp_path, perf_file=baseline_profile
        )
        perf_run(baseline_cfg)
        capsys.readouterr()

        regressed_profile = tmp_path / "regressed.script"
        regressed_profile.write_text(
            _perf_script([(1.0, f"{workload}:{line}") for _ in range(10)])
        )
        regressed_cfg = AppConfig(
            perf_command="collect", perf_path=tmp_path, perf_file=regressed_profile
        )
        perf_run(regressed_cfg)
        out = capsys.readouterr().out

        # Or/And mutant: `label and section_key` returns the (truthy)
        # section_key instead of the label when both are set -- this
        # would show a bare hex digest, never "hot_loop".
        assert "hot_loop" in out, out
        # Mult/Div mutant: the real relative shift is ~9.0 (900%, +/- a
        # few percent of DDSketch quantization noise); dividing instead
        # of multiplying by 100 collapses it to ~0.09 -> "0%". Assert a
        # percentage comfortably above what either quantization noise or
        # a divide-mutant could produce.
        import re

        match = re.search(r"regressed (\d+)%", out)
        assert match is not None, out
        assert int(match.group(1)) > 500, out
