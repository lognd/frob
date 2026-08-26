"""Register `frob status` (T-2911): a delta-first movement summary --
findings burned/introduced since the last stamped baseline, verification
lag against the watermark, and ticket landing velocity -- so a large
absolute finding count does not read as "no progress" on its own."""

from __future__ import annotations


# frob:tests tests/test_status.py::TestAddStatusParser.test_registers_status_subcommand_with_expected_flags kind="unit"  # noqa: E501
# frob:tests tests/test_status.py::TestAddStatusParser.test_bare_status_has_no_op_defaults kind="unit"  # noqa: E501
# frob:ticket T-2911
def _add_status_parser(sub) -> None:  # noqa: ANN001 -- argparse _SubParsersAction
    """Register the `frob status` subcommand: no sub-actions of its own
    (unlike `frob verify`), just flags -- this is a single glanceable
    report, not an operable surface."""
    status_p = sub.add_parser(
        "status",
        help="delta-first movement summary: findings burned/introduced "
        "since the last baseline, verification lag, ticket landing "
        "velocity -- reuses frob check --stamp-baseline/frob verify "
        "status/frob ticket flow's own data, invents no new counter",
    )
    status_p.add_argument("--path", dest="status_path", metavar="DIR")
    status_p.add_argument("--json", dest="status_json", action="store_true")
    status_p.add_argument(
        "--only",
        dest="status_only",
        action="append",
        default=[],
        metavar="GATE",
        help="gate id(s) to scan for the findings-movement section "
        "(repeatable; default: the existing gates-fast stage group)",
    )
    status_p.add_argument(
        "--no-tickets",
        dest="status_no_tickets",
        action="store_true",
        help="skip the ticket-flow section (it mines the whole ledger's "
        "git history and is the most expensive part of this command)",
    )
