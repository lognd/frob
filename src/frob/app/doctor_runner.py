"""CLI wiring for `frob doctor` -- native-extension diagnosis (T-0319).

T-0448: migrated to `frob.render.Renderer` as the FOUNDATION exemplar for
the unified output layer; the `--json` path stays a separate channel per
the epic's "json is a separate channel" rule, but (T-0563) routes through
`_log.info` under `quiet_stdout_logs` rather than a bare `print`, matching
`frob map`/`frob dup` -- RENDER001 forbids bare stdout writes outside
`frob.render` everywhere, including the json escape hatch.
"""

from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0319
# frob:ticket T-0448
# frob:ticket T-0563
# frob:ticket T-1276
# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:doc docs/modules/render.md#exemplar-frob-doctor
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy.test_healthy_plain_prints_all_available_and_does_not_exit  # noqa: E501
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy.test_healthy_json_emits_parseable_report  # noqa: E501
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_plain_exits_1_and_prints_remediation  # noqa: E501
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_no_remediation_prints_empty_not_none  # noqa: E501
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_json_exits_1  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Render the `frob doctor` native-extension diagnosis; exits 1 when any
    extension is missing so `frob doctor` is scriptable as a preflight
    check, not just a human-readable report. `--usage` (T-1360) instead
    renders the local telemetry corpus's top time sinks and footgun
    totals -- a separate, non-exiting report, mutually exclusive with the
    native-extension check in practice (usage is checked first)."""
    if cfg.doctor_usage:
        _run_usage(cfg)
        return

    from frob.doctor import run_diagnosis

    if cfg.doctor_json:
        with quiet_stdout_logs():
            report = run_diagnosis()
        _log.info(report.model_dump_json(indent=2))
        if not report.healthy:
            sys.exit(1)
        return

    report = run_diagnosis()

    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    r.write.heading("frob doctor")
    r.blank()
    r.write.kv("frob version", report.frob_version)
    r.blank()
    for ext in report.extensions:
        if ext.available:
            r.write.good(
                f"  {ext.name}: available (version={ext.version or 'unknown'})"
            )
        else:
            r.write.critical(f"  {ext.name}: NOT importable")
    r.blank()
    if report.healthy:
        r.write.good("all native extensions available")
    else:
        r.write.warn("native extensions missing")
        # T-0448: deliberate fix, not a silent behavior change -- the
        # pre-migration code interpolated `report.remediation` (which is
        # `str | None`) straight into an f-string, so a healthy=False
        # report with no remediation text printed the literal word "None".
        # `write.kv` requires `str`, so the `or ""` here is intentional:
        # an empty remediation line is honest, printing "None" was a bug.
        r.write.kv("  remediation", report.remediation or "")

    if not report.healthy:
        sys.exit(1)


# frob:ticket T-1360
# frob:tests tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero
def _run_usage(cfg: AppConfig) -> None:
    """Render `frob doctor --usage` (T-1360): top time sinks and footgun
    totals mined from `.frob/telemetry.jsonl`. Never exits nonzero -- this
    is a report, not a health check."""
    from pathlib import Path

    from frob.app.telemetry import usage_report

    root = Path(".").resolve()
    with quiet_stdout_logs():
        report = usage_report(root)

    if cfg.doctor_json:
        _log.info(report.model_dump_json(indent=2))
        return

    r = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    r.write.heading("frob doctor --usage")
    r.blank()
    r.write.kv("total calls", str(report.total_calls))
    r.write.kv("total duration", f"{report.total_duration_ms / 1000.0:.1f}s")
    r.write.kv(
        "failure rate",
        f"{report.failure_rate * 100:.1f}% ({report.failures}/{report.total_calls})",
    )
    r.write.kv("redundant re-runs", str(report.redundant_rerun_count))
    r.write.kv(
        "redundant re-run cost",
        f"{report.redundant_rerun_wasted_ms / 1000.0:.1f}s",
    )
    r.write.kv("fast exit-1 runs", str(report.fast_exit1_count))
    r.write.kv("stuck-repeat streaks", str(report.repeated_failure_streaks))
    r.blank()
    r.write.heading("top time sinks")
    for sink in report.top_time_sinks:
        r.write.kv(
            f"  frob {sink.subcommand}",
            f"{sink.total_duration_ms / 1000.0:.1f}s over {sink.calls} call(s), "
            f"{sink.failures} failure(s)",
        )
