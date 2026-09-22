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
# frob:ticket T-4416
# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:doc docs/modules/render.md#exemplar-frob-doctor
# frob:doc docs/modules/land-profiles.md#land-profiles-rapid-vs-standard-t-4416
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
    if cfg.doctor_whereis:
        print_whereis(cfg)
        return

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

    _run_plain(cfg, run_diagnosis)


# frob:ticket T-2979
# frob:ticket T-4416
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted.test_plain_path_raises_stdout_handlers_to_warning_by_default  # noqa: E501
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted.test_plain_path_leaves_stdout_handlers_alone_under_frob_verbose  # noqa: E501
def _run_plain(cfg: AppConfig, run_diagnosis) -> None:  # noqa: ANN001
    """`run`'s plain (human, non-`--json`, non-`--usage`) path -- extracted
    out of `run` to keep it under ARCH001's 60-line threshold (same move
    as `_print_orphaned_land_lock_disclosure` below). `run_diagnosis()`
    used to be called unwrapped here -- unlike its `doctor_json` sibling
    in `run`, which already wraps the equivalent call. Every `frob.lang.
    parse_file` invocation `run_diagnosis`'s scaffold-conformance check
    makes logs an INFO "parsed ...: language=... symbols=N comments=N"
    line (per `quiet_stdout_logs`'s own module docstring), so the plain
    path was printing dozens of those ahead of the actual report (T-2979).
    `quiet_query_stdout` (not the unconditional `quiet_stdout_logs`) is
    used deliberately: this is a human-mode default, so `-v`/
    `FROB_VERBOSE=1` must still restore the chatter, matching every other
    human-mode runner (T-2582). The report itself is rendered below via
    `Renderer`, never via the logger, so quieting this call cannot hide
    any of the real result."""
    from frob.logging.quiet import quiet_query_stdout

    with quiet_query_stdout():
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
        _print_unhealthy_summary(r, report)

    _print_orphaned_land_lock_disclosure(r, report)
    _print_scaffold_disclosure(r, report)
    _print_profile_recommendation(r, report)

    if not report.healthy:
        sys.exit(1)


# frob:ticket T-3725
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerUnhealthy.test_unhealthy_plain_exits_1_and_prints_remediation  # noqa: E501
def _print_unhealthy_summary(r: Renderer, report) -> None:
    """`_run_plain`'s unhealthy-branch status line + remediation, extracted
    (T-3725) to keep `_run_plain` under ARCH103's decision-point threshold.
    This used to print the fixed label "native extensions missing"
    whenever `report.healthy` was False for ANY reason -- CI run
    33715737237 hit exactly this: `frob_core`/`strata_core` both reported
    `available=True` (only their `version` was `unknown`, an unset
    `__version__` attribute, not a misclassification -- `_extension_status`
    already treats `available=True` as healthy regardless of version
    string) while the report was unhealthy for an unrelated reason
    (missing managed git hooks), and the printed line still blamed
    extensions. Naming the actual failing extensions keeps the label
    honest; a non-extensions failure gets a neutral heading instead of a
    false accusation."""
    unavailable = [ext.name for ext in report.extensions if not ext.available]
    if unavailable:
        r.write.warn("native extensions missing: " + ", ".join(unavailable))
    else:
        r.write.warn("frob doctor found issue(s)")
    # T-0448: deliberate fix, not a silent behavior change -- the
    # pre-migration code interpolated `report.remediation` (which is
    # `str | None`) straight into an f-string, so a healthy=False report
    # with no remediation text printed the literal word "None". `write.kv`
    # requires `str`, so the `or ""` here is intentional: an empty
    # remediation line is honest, printing "None" was a bug.
    r.write.kv("  remediation", report.remediation or "")


# frob:ticket T-1634
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosure.test_healthy_report_with_confirmed_dead_holder_prints_self_healing_line  # noqa: E501
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerOrphanedLandLockDisclosure.test_healthy_report_with_no_land_lock_prints_nothing_extra  # noqa: E501
def _print_orphaned_land_lock_disclosure(r: Renderer, report) -> None:
    """T-1634: extracted out of `run` to keep it under ARCH001's 60-line
    threshold. A confirmed-dead land.lock holder no longer makes the
    overall report unhealthy (self-healing -- the OS already released the
    `flock`) -- but it is still a real, discoverable finding, so print it
    even on the otherwise-healthy path, in addition to the unhealthy-path
    `remediation` block `run` already prints above."""
    live = report.live_land_process
    if report.healthy and live is not None and live.alive is False:
        r.blank()
        r.write.warn(
            f"  orphaned land.lock found (pid {live.pid} confirmed NOT "
            "running) -- self-healing, no action needed; the next `frob "
            "ticket land` reclaims it automatically"
        )


# frob:ticket T-3725
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerScaffoldDisclosure.test_healthy_report_with_scaffold_needs_apply_prints_disclosure_line  # noqa: E501
# frob:tests \
# tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerScaffoldDisclosure.test_healthy_report_with_no_scaffold_blocks_prints_nothing_extra  # noqa: E501
# frob:waive DUP001 reason="deliberate structural mirror of this same file's \
# _print_orphaned_land_lock_disclosure directly above -- both are the identical \
# 'informational-only finding, disclose on the otherwise-healthy path' shape T-1634 \
# established; the detector's other 7 cross-file hits (refactor/vet/strata capability \
# scanners, an unrelated deploy pilot test) are coincidental control-flow shape only, \
# no shared domain"
def _print_scaffold_disclosure(r: Renderer, report) -> None:
    """T-3725: missing/stale LOCAL managed git hooks (`scaffold_blocks`,
    T-0736) no longer make the overall report unhealthy (see
    `frob.doctor._doctor_healthy`'s docstring for why -- a CI checkout
    structurally never runs `frob scaffold apply`, so failing a build on
    their absence was a false positive, not a real health signal) -- but
    it is still a real, discoverable, human-actionable finding, so print
    it even on the otherwise-healthy path, in addition to the unhealthy-
    path `remediation` block `run` already prints above (which still
    names it when some OTHER check also failed)."""
    needs_apply = [s for s in report.scaffold_blocks if not s.present or s.stale]
    if report.healthy and needs_apply:
        r.blank()
        names = ", ".join(f"{s.block_id} ({s.target})" for s in needs_apply)
        r.write.warn(
            f"  managed boilerplate blocks missing/stale: {names} -- run "
            "`frob scaffold apply` (informational only, does not affect "
            "the exit code)"
        )


# frob:ticket T-4416
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerProfileRecommendation.test_recommendation_printed_when_present  # noqa: E501
# frob:tests tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerProfileRecommendation.test_no_recommendation_prints_nothing_extra  # noqa: E501
def _print_profile_recommendation(r: Renderer, report) -> None:
    """T-4416: print `report.profile_recommendation` (advisory-only nudge
    toward `[profile] profile = "rapid"` once the repo crosses
    `frob.doctor._PROFILE_RECOMMEND_THRESHOLD`) whenever present, on both
    the healthy and unhealthy paths -- unlike `_print_scaffold_disclosure`/
    `_print_orphaned_land_lock_disclosure` above (both gated on `report.
    healthy`, since they are self-healing/already-covered-by-remediation
    findings), a profile recommendation is orthogonal to health and stays
    worth surfacing either way. Prints nothing when `None` (a repo below
    threshold, matching T-4416's acceptance criterion 3: never force
    `rapid`, never even mention it, below the measured threshold)."""
    if report.profile_recommendation:
        r.blank()
        r.write.warn(f"  {report.profile_recommendation}")


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


# frob:ticket T-4690
# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:tests tests/unit/test_cli_shims.py::TestPrintWhereis.test_plain_output_names_the_live_executable  # noqa: E501
# frob:tests tests/unit/test_cli_shims.py::TestPrintWhereis.test_json_output_is_parseable  # noqa: E501
def print_whereis(cfg: AppConfig) -> None:
    """`frob doctor --whereis` (folded from the standalone `frob whereis`,
    T-4299/T-4690): print the interpreter/site-packages path of the frob
    package ACTUALLY EXECUTING this invocation -- the LIVE process's own
    `sys.executable`/package `__file__`, never a `shutil.which`-style PATH
    lookup or a hardcoded install-layout assumption, since this repo
    already warns elsewhere that an invoked binary's source identity can
    silently diverge from a given checkout. Shared by `frob doctor
    --whereis` and the deprecated `frob whereis` shim
    (`frob.__main__._dispatch_whereis`) so the reporting logic exists in
    exactly one place."""
    import json
    import site
    from pathlib import Path

    import frob as _frob_pkg

    package_dir = str(Path(_frob_pkg.__file__).resolve().parent)
    try:
        site_packages = site.getsitepackages()
    except AttributeError:
        # T-4299: some venvs (built without site.ENABLE_USER_SITE support)
        # lack getsitepackages entirely -- fall back to the package
        # directory's own parent, which IS the site-packages dir for a
        # normally-installed package, so this never reports nothing.
        site_packages = [str(Path(package_dir).parent)]

    payload = {
        "executable": sys.executable,
        "frob_package": package_dir,
        "site_packages": site_packages,
    }
    renderer = Renderer.for_stream(
        sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
    )
    if cfg.doctor_json:
        renderer.line(json.dumps(payload, indent=2))
        return
    renderer.line(f"executable: {payload['executable']}")
    renderer.line(f"frob package: {payload['frob_package']}")
    for path in payload["site_packages"]:
        renderer.line(f"site-packages: {path}")
