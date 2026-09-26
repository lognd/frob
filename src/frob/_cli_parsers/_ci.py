"""Register `frob ci report <run-id>` (T-2982, CI-1): the CLI surface over
`frob.ci_report.build_run_report`/`frob.ghio` -- see `frob.app.ci_runner`'s
module docstring for what the subcommand renders."""

from __future__ import annotations


# frob:ticket T-draft-c099f096
def _add_ci_parser(sub) -> None:  # noqa: ANN001 -- argparse _SubParsersAction
    """Register the `frob ci` subcommand and its `report` action, mirroring
    `frob verify`'s own `_add_verify_parser` precedent (T-1697)."""
    ci_p = sub.add_parser(
        "ci",
        help="talk to gh/CI: per-job, per-platform failure report for one run",
    )
    ci_sub = ci_p.add_subparsers(dest="ci_command")

    report_p = ci_sub.add_parser(
        "report",
        help="per job/platform failing test node ids and failing steps, "
        "the cross-platform diff, and clusters by file, for one run",
    )
    report_p.add_argument("ci_run_id", metavar="run-id", help="the gh run id")
    report_p.add_argument("--path", dest="ci_path", metavar="DIR")
    report_p.add_argument("--json", dest="ci_json", action="store_true")
