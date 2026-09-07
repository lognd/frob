"""CLI parser builders for the ticket closeout subcommands: attach/block/
unblock/close/reverify/review.

Split out of `_cli_parsers/_ticket.py` (T-1270) -- no behavior change, same
argparse tree. Split again (T-4145) once T-4106/T-4108's argparse guards
pushed this file past the LARGE gate threshold: the remaining evidence-
lifecycle subcommands (fail/evidence/drop/reopen/archive/restore/done-
report/waive-audit/sweep-async) now live in `_closeout_evidence.py`,
mirroring the same per-concern split T-1270 already used for this
package's `_metadata.py`/`_new.py`/`_progress.py`/`_query.py` siblings.
`_RefuseRepeatedEvidenceCmd`, `_EVIDENCE_CMD_KIND_HELP`, and
`_add_evidence_cwd_arg` stay here (this file's own close/reverify parsers
need them) and are imported by `_closeout_evidence.py` rather than
duplicated.
"""

from __future__ import annotations

import argparse


# frob:ticket T-4108
class _RefuseRepeatedEvidenceCmd(argparse.Action):
    """argparse `Action` that refuses a SECOND `--evidence-cmd` in one
    invocation (T-4108), instead of argparse's default single-value
    `store` behavior of silently keeping only the LAST occurrence.

    Reported as F-306 (T-0265): `--evidence-cmd` (this block, no
    `action=`) LAST-WINS while the adjacent `--accepts` (`action=
    "append"`) ACCUMULATES every value given -- so `--evidence-cmd A
    --accepts 1 --evidence-cmd B --accepts 2` silently records ONLY
    command B, bound to BOTH criteria 1 and 2. The close then SUCCEEDS,
    with the ticket's own record now asserting command B is the evidence
    for criterion 1, which is false -- worse than a dropped flag, since a
    lost flag would have failed the close loudly (an unbound criterion)
    and the wrong record instead looks clean.

    THE FIX IS NOT `action="append"`: two flat lists whose pairing is
    implied by position is the exact fragile shape that produced this
    report, and it would silently change what a single `--evidence-cmd`
    with several `--accepts` means today (correctly: one command bound to
    every listed criterion, a legitimate and unchanged use, T-4108's own
    must-stay-quiet fixture). Refusing the SECOND occurrence outright
    costs one retry; the correct multi-command shape already exists and
    already works per call: bind each command with its own `frob ticket
    evidence <id> --evidence-cmd COMMAND --accepts N` call, then close
    with no `--evidence-cmd` of its own (T-4106 covers making that verb
    itself easier to find; this ticket is the accounting fix, not the
    discoverability one)."""

    # frob:waive OPAQUE001 reason="standard argparse.Action shape: self.dest IS the \
    # dest= string argparse itself assigned when this Action was registered on the \
    # parser (never externally-influenced input), and getattr/setattr(namespace, \
    # self.dest, ...) is exactly how argparse's own builtin Action subclasses (e.g. \
    # _StoreAction) read/write the parsed namespace -- there is no alternative, \
    # non-dynamic API for this"  # noqa: E501
    def __call__(self, parser, namespace, values, option_string=None):  # noqa: ANN001
        """Raise `argparse.ArgumentError` if `self.dest` was already set
        by a prior `--evidence-cmd` in this same invocation; otherwise
        store `values` normally (the ordinary single-command case, T-4108's
        must-stay-quiet fixture)."""
        if getattr(namespace, self.dest, None) is not None:
            raise argparse.ArgumentError(
                self,
                f"{option_string} given more than once -- a single "
                "invocation binds ONE evidence command to every --accepts "
                "index given (T-0572), never several commands to several "
                "indexes by position (T-4108: that pairing-by-position "
                "shape is exactly what silently bound the wrong command "
                "to a criterion in F-306). To bind DIFFERENT commands to "
                "different criteria, call `frob ticket evidence <id> "
                "--evidence-cmd COMMAND --accepts N` once per command "
                "first, then run this command with no --evidence-cmd of "
                "its own",
            )
        setattr(namespace, self.dest, values)


# frob:waive AFFECT001 reason="T-2254 adds --backfill-drafts/--apply flags to the \
# existing attach subcommand; docs/guides/agentic-workflow.md#the-humanai-split \
# describes the human/AI ticket-queue split at large, not this parser's individual \
# flag surface, and pulling it into scope for two new store_true flags is out of \
# proportion to this ticket's narrowed scope (T-2220 held a live lease on \
# src/frob/app/ticket_runner/_lifecycle.py for this ticket's whole duration, which is \
# why the dispatch decision itself lives in a new sibling module instead) -- the new \
# flags are documented in their own --help text and in \
# frob.app.ticket_runner._attach_backfill's module docstring"
def _add_ticket_attach_and_lifecycle_end_parsers(ticket_sub) -> list:
    """Register `attach`/`block`/`unblock`/`close`: the non-evidence closeout
    subcommands."""
    ticket_attach_p = ticket_sub.add_parser(
        "attach", help="attach a file or clipboard image to a ticket"
    )
    # T-2254: `ticket_id` becomes OPTIONAL (was `metavar="id"` alone, always
    # required) so `--backfill-drafts` below -- a repo-wide repair with no
    # single target ticket -- can omit it; the runner
    # (`frob.app.ticket_runner._attach_backfill._attach_dispatch`) still
    # requires it for the ordinary single-file attach path, unchanged.
    ticket_attach_p.add_argument("ticket_id", metavar="id", nargs="?", default=None)
    ticket_attach_p.add_argument(
        "ticket_attach_path", metavar="path", nargs="?", default=None
    )
    ticket_attach_p.add_argument("--caption", dest="ticket_caption", default="")
    # frob:ticket T-1615
    ticket_attach_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1615's uniform auto-commit of this ledger change; "
        "WARNS that the ledger is left dirty and will DirtyMain-block a "
        "concurrent `frob ticket land`",
    )
    # frob:ticket T-2254
    ticket_attach_p.add_argument(
        "--backfill-drafts",
        dest="ticket_attach_backfill_drafts",
        action="store_true",
        help="repair attachment path fields a pre-T-2199 draft promotion "
        "left dangling at a vanished T-draft-<hash> directory (T-2226's "
        "backfill_stale_draft_attachment_paths); repo-wide, no ticket id "
        "needed. Report-only by default -- pass --apply to actually write",
    )
    ticket_attach_p.add_argument(
        "--apply",
        dest="ticket_attach_backfill_apply",
        action="store_true",
        help="with --backfill-drafts, write the repairs found (default: "
        "dry-run report only, same shape as `frob ticket reconcile`)",
    )

    ticket_block_p = ticket_sub.add_parser("block", help="record a blocker")
    ticket_block_p.add_argument("ticket_id", metavar="id")
    ticket_block_p.add_argument("--by", dest="ticket_by", required=True)
    # frob:ticket T-1615
    ticket_block_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1615's uniform auto-commit of this ledger change; "
        "WARNS that the ledger is left dirty and will DirtyMain-block a "
        "concurrent `frob ticket land`",
    )

    # frob:ticket T-2681
    # frob:ticket T-3113
    ticket_unblock_p = ticket_sub.add_parser(
        "unblock",
        help="remove a blocker (correcting a wrong/obsolete edge), with a "
        "mandatory dated --reason (T-3113)",
    )
    ticket_unblock_p.add_argument("ticket_id", metavar="id")
    ticket_unblock_p.add_argument("--by", dest="ticket_by", required=True)
    # frob:ticket T-3113
    ticket_unblock_p.add_argument(
        "--reason",
        dest="ticket_reason",
        required=True,
        metavar="TEXT",
        help="why this edge is being removed (T-3113); recorded as a "
        "dated line in the ticket's own '## Unblock log' section, "
        "mirroring `frob ticket reopen`'s --reason precedent",
    )
    # frob:ticket T-1615
    ticket_unblock_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1615's uniform auto-commit of this ledger change; "
        "WARNS that the ledger is left dirty and will DirtyMain-block a "
        "concurrent `frob ticket land`",
    )

    ticket_close_p = _add_ticket_close_parser(ticket_sub)
    return [ticket_attach_p, ticket_block_p, ticket_unblock_p, ticket_close_p]


# frob:ticket T-4000
# F-215: help text used to say docs-kind tickets only, never matched ux
_EVIDENCE_CMD_KIND_HELP = (
    "kind gated by CMD_EVIDENCE_ALLOWED_KINDS (docs/ux), code kinds still "
    "require pytest/--evidence node ids"
)


def _add_evidence_cwd_arg(parser) -> None:  # noqa: ANN001
    """Register `--cwd DIR` (T-4000, F-215), shared by close/reverify/evidence."""
    parser.add_argument(
        "--cwd",
        dest="ticket_evidence_cwd",
        metavar="DIR",
        help="with --evidence-cmd: run COMMAND from DIR under the ticket's "
        "--path root, not the root itself (F-215, vs. `cd DIR && cmd`/`npx "
        "--prefix DIR`)",
    )


def _add_ticket_close_parser(ticket_sub):
    """Register `frob ticket close` and return its subparser."""
    ticket_close_p = ticket_sub.add_parser("close", help="transition to done")
    ticket_close_p.add_argument("ticket_id", metavar="id")
    ticket_close_p.add_argument(
        "--evidence",
        dest="ticket_evidence_ids",
        action="append",
        default=[],
        metavar="NODE-ID",
        help="pytest node id to record as evidence before closing (repeatable)",
    )
    # frob:ticket T-4108
    ticket_close_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        action=_RefuseRepeatedEvidenceCmd,
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215): run COMMAND, record its "
        "exit/digest as evidence before closing -- "
        + _EVIDENCE_CMD_KIND_HELP
        + " NOT repeatable (T-4108): a single invocation binds one command "
        "to every --accepts index given; a second --evidence-cmd is "
        "refused rather than silently discarding the first.",
    )
    _add_evidence_cwd_arg(ticket_close_p)
    ticket_close_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 1-based ticket.acceptance position (T-3837; see "
        "`frob ticket show`'s [N] list) that --evidence/--evidence-cmd's "
        "id(s) also bind to (repeatable); an unbound acceptance criterion "
        "refuses the close",
    )
    # frob:ticket T-0571
    ticket_close_p.add_argument(
        "--strict",
        dest="ticket_close_strict",
        action="store_true",
        help="require an approve-verdict `frob ticket review` record "
        "naming the current commit before closing (T-0571); combined with "
        "`[tickets] require_review_for_close` in frob.toml, which must "
        "also be true for this to actually gate -- off by default",
    )
    # frob:ticket T-0844
    ticket_close_p.add_argument(
        "--skip-mutation-evidence",
        dest="ticket_close_skip_mutation_evidence",
        action="store_true",
        help=(
            "T-0844 escape hatch (the close-path twin of `frob ticket land "
            "--skip-mutation-evidence`): do not let a TEST016 confirmatory-"
            "only-evidence finding refuse the close (the check still runs "
            "and logs its findings at WARNING; this only stops it from "
            "blocking). Use for a genuine false positive, not to wave "
            "through real confirmatory evidence."
        ),
    )
    # frob:ticket T-1178
    ticket_close_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the close ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )
    # frob:ticket T-2393
    ticket_close_p.add_argument(
        "--no-behavior-change",
        dest="ticket_close_no_behavior_change",
        action="store_true",
        help="the first-class front door (T-2393) for a doc-only/epic-"
        "rollup/structural ticket with no runtime defect to reproduce: "
        'writes `frob:no-behavior-change reason="..."` into the ticket\'s '
        "body (via `frob.tickets.set_body`, T-2392) before BUG002 runs, "
        "the SAME remedy that previously required a hand-edit of "
        "tickets/T-####/ticket.md. Requires --no-behavior-change-reason/"
        "-reason-file; BUG002 itself still runs and still refuses a "
        "genuinely confirmatory-only evidence claim -- this only lets a "
        "ticket with no behavioral delta AT ALL declare that honestly.",
    )
    ticket_close_p.add_argument(
        "--no-behavior-change-reason",
        dest="ticket_close_no_behavior_change_reason",
        metavar="TEXT",
        help="why this ticket has no behavioral delta (recorded both in "
        "the frob:no-behavior-change directive AND, via set_body, in "
        "ticket.body_changes); required with --no-behavior-change unless "
        "--no-behavior-change-reason-file is given",
    )
    ticket_close_p.add_argument(
        "--no-behavior-change-reason-file",
        dest="ticket_close_no_behavior_change_reason_file",
        metavar="PATH",
        help="read the --no-behavior-change reason verbatim from PATH "
        "instead of the shell (T-0737); mutually exclusive with "
        "--no-behavior-change-reason",
    )
    return ticket_close_p


# frob:ticket T-1005
def _add_ticket_reverify_parser(ticket_sub):
    """Register `frob ticket reverify <id>` -- re-run the full close-time
    verification suite (evidence re-run, mutation evidence, covers-scope,
    acceptance binding, live-tracker citation) against an already-DONE
    ticket and refresh its recap, with NO state transition (T-1005, the
    post-close send-back verb `close`/`start`/`sweep` all refuse to be).
    Shares `close`'s own `--evidence`/`--evidence-cmd`/`--accepts`/
    `--strict`/`--skip-mutation-evidence` flags verbatim (same dest names,
    so `frob.app.ticket_runner._close_guards_for_ticket` works unmodified
    for either command) plus `done-report`'s `--base-ref` (the recap
    refresh re-derives the Changed section against it)."""
    ticket_reverify_p = ticket_sub.add_parser(
        "reverify",
        help="re-run close verification on a done ticket, refresh its "
        "recap, no state transition",
    )
    ticket_reverify_p.add_argument("ticket_id", metavar="id")
    ticket_reverify_p.add_argument(
        "--evidence",
        dest="ticket_evidence_ids",
        action="append",
        default=[],
        metavar="NODE-ID",
        help="pytest node id to record as evidence before reverifying (repeatable)",
    )
    # frob:ticket T-4108
    ticket_reverify_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        action=_RefuseRepeatedEvidenceCmd,
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215), same semantics as "
        "`close --evidence-cmd` -- including T-4108's not-repeatable "
        "refusal, since this verb's own docstring already commits to "
        "sharing close's evidence flags verbatim",
    )
    _add_evidence_cwd_arg(ticket_reverify_p)
    ticket_reverify_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 1-based ticket.acceptance position (T-3837; see "
        "`frob ticket show`'s [N] list) --evidence/--evidence-cmd's "
        "id(s) also bind to (repeatable)",
    )
    ticket_reverify_p.add_argument(
        "--strict",
        dest="ticket_close_strict",
        action="store_true",
        help="require an approve-verdict `frob ticket review` record "
        "naming the current commit (T-0571), same semantics as "
        "`close --strict`",
    )
    ticket_reverify_p.add_argument(
        "--skip-mutation-evidence",
        dest="ticket_close_skip_mutation_evidence",
        action="store_true",
        help="T-0844 escape hatch, same semantics as `close --skip-mutation-evidence`",
    )
    ticket_reverify_p.add_argument(
        "--base-ref",
        dest="ticket_base_ref",
        default="main",
        metavar="REF",
        help="base ref the refreshed recap's Changed section diffs "
        "against (default: main)",
    )
    return ticket_reverify_p


# frob:ticket T-0571
def _add_ticket_review_parser(ticket_sub):
    """Register `frob ticket review <id> --verdict approve|reject
    --reviewer NAME --findings-file PATH [--commit SHA]` (T-0571): writes a
    structured review record (verdict, reviewer, findings summary,
    timestamp, commit reviewed) into the ticket's ledger entry as
    first-class evidence -- the fix for adversarial review's verdict living
    only in dispatch-chat prose."""
    ticket_review_p = ticket_sub.add_parser(
        "review",
        help="record a structured adversarial-review verdict (T-0571)",
    )
    ticket_review_p.add_argument("ticket_id", metavar="id")
    ticket_review_p.add_argument(
        "--verdict",
        dest="ticket_review_verdict",
        required=True,
        choices=["approve", "reject"],
        help="the reviewer's verdict",
    )
    ticket_review_p.add_argument(
        "--reviewer",
        dest="ticket_reviewer",
        required=True,
        metavar="NAME",
        help="who performed the review",
    )
    ticket_review_p.add_argument(
        "--findings-file",
        dest="ticket_findings_file",
        required=True,
        metavar="PATH",
        help="file containing the findings summary",
    )
    ticket_review_p.add_argument(
        "--commit",
        dest="ticket_review_commit",
        metavar="SHA",
        help="the commit reviewed (default: current HEAD)",
    )
    return ticket_review_p
