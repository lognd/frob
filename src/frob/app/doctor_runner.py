# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
"""CLI wiring for `frob doctor` -- native-extension diagnosis (T-0319).

T-0448: migrated to `frob.render.Renderer` as the FOUNDATION exemplar for
the unified output layer -- the `--json` path is untouched (still a bare
`print` of the structured payload, per the epic's "json is a separate
channel" rule); only the human-facing report routes through `Renderer`.
"""

from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0319
# frob:ticket T-0448
# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:doc docs/modules/render.md#exemplar-frob-doctor
def run(cfg: AppConfig) -> None:
    """Render the `frob doctor` native-extension diagnosis; exits 1 when any
    extension is missing so `frob doctor` is scriptable as a preflight
    check, not just a human-readable report."""
    from frob.doctor import run_diagnosis

    if cfg.doctor_json:
        with quiet_stdout_logs():
            report = run_diagnosis()
        print(report.model_dump_json(indent=2))
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
