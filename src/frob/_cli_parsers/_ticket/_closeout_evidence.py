"""CLI parser builders for the ticket evidence-lifecycle subcommands:
fail/evidence/drop/reopen/archive/restore/done-report/waive-audit/
sweep-async.

Split out of `_closeout.py` (T-4145) once T-4106/T-4108's argparse guards
pushed that file past the LARGE gate's 800-line threshold -- no behavior
change, same argparse tree, same per-concern split precedent T-1270 used
for this package's other submodules. `_RefuseRepeatedEvidenceCmd`,
`_EVIDENCE_CMD_KIND_HELP`, and `_add_evidence_cwd_arg` still live in
`_closeout.py` (its own close/reverify parsers need them too) and are
imported from there rather than duplicated.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from frob._cli_parsers._ticket._closeout import (
    _EVIDENCE_CMD_KIND_HELP,
    _add_evidence_cwd_arg,
    _RefuseRepeatedEvidenceCmd,
)
from frob._cli_parsers._ticket._metadata import _CrossVerbFlagHint


# frob:ticket T-0579
def _add_ticket_fail_evidence_archive_parsers(ticket_sub) -> list:
    """Register `fail`/`drop`/`evidence`/`archive`: the remaining closeout
    subcommands."""
    ticket_fail_p = ticket_sub.add_parser(
        "fail", help="record a failed attempt in the failure log"
    )
    ticket_fail_p.add_argument("ticket_id", metavar="id")
    ticket_fail_p.add_argument("--summary", dest="ticket_summary", required=True)
    # frob:ticket T-1130
    ticket_fail_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the fail-log/requeue ledger "
        "change (parity with `start`'s T-1054 auto-commit)",
    )

    ticket_evidence_p = ticket_sub.add_parser(
        "evidence",
        help="append pytest node ids to a ticket's structured evidence list",
    )
    ticket_evidence_p.add_argument("ticket_id", metavar="id")
    ticket_evidence_p.add_argument(
        "ticket_evidence_ids", metavar="node-id", nargs="*", default=[]
    )
    # frob:ticket T-1929
    ticket_evidence_p.add_argument(
        "--base-ref",
        dest="ticket_base_ref",
        default="main",
        metavar="REF",
        help="T-1929: base ref --designate-repro/--check-repro's parent-"
        "commit repro check diffs against (default: main), same semantics "
        "as `close`/`reverify --base-ref`",
    )
    # frob:ticket T-4108
    ticket_evidence_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        action=_RefuseRepeatedEvidenceCmd,
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215): run COMMAND, record its "
        "exit/digest as evidence -- "
        + _EVIDENCE_CMD_KIND_HELP
        + " NOT repeatable (T-4108): the SAME single-command/accumulating-"
        "--accepts asymmetry F-306 found on `close` exists here identically "
        "-- one invocation binds one command to every --accepts index "
        "given; call this verb once per command instead of repeating "
        "--evidence-cmd in one call.",
    )
    _add_evidence_cwd_arg(ticket_evidence_p)
    # frob:ticket T-1537
    ticket_evidence_p.add_argument(
        "--replace",
        dest="ticket_evidence_replace",
        nargs=2,
        metavar=("OLD-NODE-ID", "NEW-NODE-ID"),
        default=[],
        help="rebind one evidence id everywhere it appears (the flat "
        "evidence list AND every acceptance criterion's own binding) in "
        "one atomic write -- for a renamed/parametrized test whose old "
        "node id no longer resolves; mutually usable alongside positional "
        "node-id ids/--evidence-cmd in the same invocation",
    )
    # frob:ticket T-1733
    ticket_evidence_p.add_argument(
        "--reason",
        dest="ticket_evidence_replace_reason",
        metavar="TEXT",
        help="required with --replace (T-1733): why this evidence id is "
        "being rebound, recorded in the ticket's evidence_changes audit "
        "trail -- the same T-0455 `frob ticket scope --reason` "
        "precedent applied to evidence, so weakening what proves a "
        "ticket costs at least as much bookkeeping as the honest "
        "--skip-mutation-evidence escape hatch. Not required for a "
        "plain positional-node-id/--evidence-cmd append, only --replace",
    )
    ticket_evidence_p.add_argument(
        "--reason-file",
        dest="ticket_evidence_replace_reason_file",
        metavar="PATH",
        help="read --replace's reason verbatim from PATH instead of the "
        "shell (T-0737 precedent); mutually exclusive with --reason",
    )
    # frob:ticket T-1561
    ticket_evidence_p.add_argument(
        "--archived",
        dest="ticket_evidence_archived",
        action="store_true",
        help="with --replace/--remove, target an ARCHIVED ticket instead of "
        "an active one -- a stale binding on an already-archived ticket "
        "needs this to be reachable at all (T-1561)",
    )
    # frob:ticket T-4000
    ticket_evidence_p.add_argument(
        "--remove",
        dest="ticket_evidence_remove",
        metavar="EVIDENCE-ID",
        help="permanently drop one evidence id -- for a false/no-op `cmd:` "
        "entry --replace cannot correct (F-215). Requires --reason",
    )
    ticket_evidence_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 1-based ticket.acceptance position (T-3837; see "
        "`frob ticket show`'s [N] list) the node id(s) above also bind "
        "to (repeatable) -- binds evidence to a specific acceptance "
        "criterion instead of only the ticket's flat evidence list",
    )
    # frob:ticket T-1178
    ticket_evidence_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the evidence ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )
    # frob:ticket T-1670
    ticket_evidence_p.add_argument(
        "--designate-repro",
        dest="ticket_designate_repro",
        metavar="NODE-ID",
        help="T-1670: mark NODE-ID as the explicit test BUG002 re-runs at "
        "the parent commit, regardless of bind order -- without this, "
        "BUG002 always takes the FIRST pytest-node-id in the ticket's "
        "evidence list, an invisible bind-order dependency that silently "
        "checks the wrong test when a pre-existing test is bound before "
        "the real new repro test. NODE-ID must already be bound as "
        "evidence on this ticket (bind it first in the same or an "
        "earlier `frob ticket evidence` call)",
    )
    # frob:ticket T-1851
    ticket_evidence_p.add_argument(
        "--designate-repro-reason",
        dest="ticket_designate_repro_reason",
        metavar="TEXT",
        help="required with --designate-repro when it REdesignates an "
        "already-set repro test to a different bound id (T-1851, "
        "mirroring T-1733's --replace --reason precedent): why the "
        "designation changed, recorded in the ticket's "
        "designated_repro_changes audit trail. Not required for a "
        "first-time designation or a redundant re-designation of the "
        "same id -- only a genuine change of which id is designated",
    )
    ticket_evidence_p.add_argument(
        "--designate-repro-reason-file",
        dest="ticket_designate_repro_reason_file",
        metavar="PATH",
        help="read --designate-repro's reason verbatim from PATH instead "
        "of the shell (T-0737 precedent); mutually exclusive with "
        "--designate-repro-reason",
    )
    # frob:ticket T-1929
    ticket_evidence_p.add_argument(
        "--designate-repro-force",
        dest="ticket_designate_repro_force",
        action="store_true",
        help="T-1929 loud override: let --designate-repro through even "
        "when NODE-ID does not genuinely FAIL at the ticket's parent "
        "commit (the validate-at-designate check still runs and logs its "
        "verdict at WARNING; this only stops it from refusing the write). "
        "Use for a genuine false positive (e.g. a native-extension-only "
        "parent-commit gap), not to wave through real confirmatory-only "
        "evidence -- mirrors --skip-mutation-evidence's posture",
    )
    # frob:ticket T-1929
    ticket_evidence_p.add_argument(
        "--check-repro",
        dest="ticket_check_repro",
        nargs="?",
        const="",
        default=None,
        metavar="NODE-ID",
        help="T-1929: run BUG002's parent-commit repro classification "
        "on demand, without mutating anything -- reports FAILED_AT_PARENT "
        "(genuine repro) / PASSED_AT_PARENT (confirmatory-only) / "
        "NO_VERDICT (could not even collect at the parent) / TIMEOUT "
        "(T-2480: did not finish within the budget -- distinct from "
        "NO_VERDICT, may still genuinely reproduce) / SAME_AS_HEAD "
        "(base_ref resolves to HEAD itself) and exits nonzero unless "
        "FAILED_AT_PARENT. NODE-ID is optional: omitted, resolves the "
        "same test BUG002 itself would (explicit --designate-repro, else "
        "the first pytest-node-id evidence)",
    )
    # frob:ticket T-2480
    ticket_evidence_p.add_argument(
        "--repro-timeout-s",
        dest="ticket_repro_timeout_s",
        type=float,
        default=None,
        metavar="SECONDS",
        help="T-2480: override BUG002's default repro-check subprocess "
        "budget (60s) for --check-repro/--designate-repro on THIS "
        "invocation only -- repro tests for design/architecture-level "
        "defects are structurally the slowest (demonstrating the defect "
        "means elaborating the whole model), so a test that TIMEOUTs at "
        "the default budget is not necessarily confirmatory-only; raise "
        "this instead of reaching for --designate-repro-force on a test "
        "you have not actually verified fails at the parent commit",
    )

    # frob:ticket T-4106
    # T-4106 mirror direction: an agent who has learned evidence binds
    # here may then reach for CRITERION TEXT management flags on this
    # verb instead of `accept`. `--criterion`/`--criterion-file`/`--amend`
    # exist ONLY on `accept` (never legitimately typed here), so trapping
    # them is exactly as cheap as the forward direction -- see
    # `_CrossVerbFlagHint`'s own docstring. `--remove`/`--reason` are
    # deliberately NOT trapped here: both already exist on THIS verb with
    # a different meaning (`--remove EVIDENCE-ID` drops an evidence id,
    # `accept --remove INDEX` drops a criterion) -- an agent typing either
    # here gets a real flag, not an unrecognized one, so there is no
    # argparse error to attach a hint to without changing what a
    # legitimate `--remove`/`--reason` on evidence does, which is exactly
    # the aliasing this ticket rules out.
    _CRITERION_HINT = (
        "criterion text is managed on `frob ticket accept <id> "
        "--criterion TEXT` (or --amend INDEX --text TEXT --reason ..., "
        "--remove INDEX --reason ...) -- not `evidence`, which only binds "
        "evidence to an already-existing criterion index (--accepts N); "
        "see `frob ticket accept --help`"
    )
    ticket_evidence_p.add_argument(
        "--criterion",
        action=_CrossVerbFlagHint,
        hint=_CRITERION_HINT,
        help=argparse.SUPPRESS,
    )
    ticket_evidence_p.add_argument(
        "--criterion-file",
        action=_CrossVerbFlagHint,
        hint=_CRITERION_HINT,
        help=argparse.SUPPRESS,
    )
    ticket_evidence_p.add_argument(
        "--amend",
        action=_CrossVerbFlagHint,
        hint=_CRITERION_HINT,
        help=argparse.SUPPRESS,
    )

    ticket_drop_p = ticket_sub.add_parser(
        "drop",
        help="transition to dropped with a dated --reason (T-0579): "
        "absorbed elsewhere, obsolete, or subsumed work",
    )
    ticket_drop_p.add_argument("ticket_id", metavar="id")
    ticket_drop_p.add_argument(
        "--reason", dest="ticket_reason", required=True, metavar="TEXT"
    )
    ticket_drop_p.add_argument(
        "--absorbed-by",
        dest="ticket_absorbed_by",
        default=None,
        metavar="T-####",
        help="cross-reference the ticket this work was folded into",
    )
    # frob:ticket T-1130
    ticket_drop_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the drop ledger change (parity "
        "with `start`'s T-1054 auto-commit)",
    )

    # frob:ticket T-3087
    ticket_reopen_p = ticket_sub.add_parser(
        "reopen",
        help="transition a done ticket back to queued with a dated --reason "
        "(T-3087): the audited escape hatch for a FALSELY-closed ticket",
    )
    ticket_reopen_p.add_argument("ticket_id", metavar="id")
    ticket_reopen_p.add_argument(
        "--reason", dest="ticket_reason", required=True, metavar="TEXT"
    )
    ticket_reopen_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the reopen ledger change (parity "
        "with `drop`/`fail`/`start`'s auto-commit)",
    )

    ticket_archive_p = ticket_sub.add_parser(
        "archive", help="move done/dropped tickets into tickets-archive.md"
    )
    ticket_archive_p.add_argument(
        "--force",
        dest="ticket_force",
        action="store_true",
        help="T-0810: override the T-0764 refusal when a live cross-"
        "worktree lease exists anywhere in the repo -- archive anyway. "
        "T-1762: requires --reason/--reason-file, recorded in "
        "force-overrides.jsonl",
    )
    # frob:ticket T-1762
    ticket_archive_p.add_argument(
        "--reason", dest="ticket_force_reason", metavar="TEXT", default=None
    )
    ticket_archive_p.add_argument(
        "--reason-file", dest="ticket_force_reason_file", metavar="PATH", type=Path
    )
    # frob:ticket T-1615
    ticket_archive_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1615's auto-commit of the whole-ledger archive "
        "change; WARNS that the ledger is left dirty and will "
        "DirtyMain-block a concurrent `frob ticket land`",
    )

    # frob:ticket T-2954
    ticket_restore_p = ticket_sub.add_parser(
        "restore",
        help="move a ticket OUT of tickets/archive/ back into the active "
        "store (T-2954): the repair verb for a ticket stranded archived "
        "in a non-terminal state (e.g. a hand-edited ledger)",
    )
    ticket_restore_p.add_argument("ticket_id", metavar="id")
    ticket_restore_p.add_argument(
        "--reason", dest="ticket_reason", required=True, metavar="TEXT"
    )
    ticket_restore_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip the auto-commit of the restore ledger change (parity "
        "with `drop`/`reopen`'s auto-commit)",
    )
    return [
        ticket_fail_p,
        ticket_evidence_p,
        ticket_drop_p,
        ticket_archive_p,
        ticket_restore_p,
    ]


# frob:ticket T-0458
def _add_ticket_done_report_parser(ticket_sub):
    """Register `frob ticket done-report <id> (--why TEXT | --why-file PATH)`
    -- the atomic, auto-composing Done-report writer (T-0458): the caller
    supplies ONLY the narrative why; Changed and Evidence are auto-filled
    from git and the ticket's recorded evidence. `--why -` (or neither flag
    given) reads the narrative from stdin."""
    ticket_done_report_p = ticket_sub.add_parser(
        "done-report",
        help="atomically write/update a ticket's Done report (Changed + "
        "Evidence auto-composed -- never hand-edit tickets.md)",
    )
    ticket_done_report_p.add_argument("ticket_id", metavar="id")
    # frob:ticket T-0578
    # `--body` is a deprecated back-compat alias for `--why` (the canonical
    # name here -- `new`'s own `--body` means something different, the
    # ticket's initial description, which is exactly the cross-subcommand
    # naming drift T-0578 exists to close): observed misuse guessed
    # `--body` for the Done-report narrative and got an unrecognized-
    # argument error instead of a result.
    ticket_done_report_p.add_argument(
        "--why",
        "--body",
        dest="ticket_why",
        metavar="TEXT",
        help="the narrative why (pass '-' or omit both --why/--why-file to "
        "read from stdin; --body accepted as a deprecated alias)",
    )
    ticket_done_report_p.add_argument(
        "--why-file",
        dest="ticket_why_file",
        metavar="PATH",
        help="read the narrative why from PATH",
    )
    ticket_done_report_p.add_argument(
        "--base-ref",
        dest="ticket_base_ref",
        default="main",
        metavar="REF",
        help="base ref the auto-filled Changed section diffs against (default: main)",
    )
    # frob:ticket T-1178
    ticket_done_report_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the done-report ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )
    return ticket_done_report_p


# frob:ticket T-1684
# frob:ticket T-2467
def _add_ticket_waive_audit_parser(ticket_sub):
    """Register `frob ticket waive-audit {scan,complete}` -- T-2467's
    watermark-scoped successor to T-1614's unreachable one-shot audit.
    `scan` is read-only; `complete` records a finished pass's verdict and
    advances the persisted watermark (see `frob.gates._waive_audit_watermark`
    and `frob.app.ticket_runner._waive_audit` for the fail-loudly
    verdict shape this deliberately does not collapse)."""
    waive_audit_p = ticket_sub.add_parser(
        "waive-audit",
        help="periodic, watermark-scoped frob:waive honesty audit (T-1614/T-2467)",
    )
    waive_audit_sub = waive_audit_p.add_subparsers(
        dest="waive_audit_subcommand", required=True
    )
    scan_p = waive_audit_sub.add_parser(
        "scan",
        help="read-only: report frob:waive directives needing classification "
        "since the last watermark (or a bounded first-run catch-up set)",
    )
    scan_p.add_argument("--json", dest="ticket_json", action="store_true")
    # frob:ticket T-2496
    scan_p.add_argument(
        "--check-collisions",
        dest="waive_audit_check_collisions",
        action="store_true",
        help="T-2496: opt-in, report-only. Also runs find_collision_"
        "suspects (T-2493) -- flags a frob:waive only when an ACTIVE, "
        "UNSUPPRESSED violation of the SAME rule sits in the SAME file as "
        "the waiver, a direct presence-based counter-example that the "
        "waiver failed to suppress something it names. Never reasons from "
        "absence: a waiver whose site has ZERO current violations "
        "anywhere is INVISIBLE to this check, indistinguishable from a "
        "genuinely inert waiver using only this signal (T-1579's own "
        "incident is why -- see find_collision_suspects's module-level "
        "docstring for the full history). Runs a real, unscoped "
        "`frob check` gate pass to get the current kept-violation set, so "
        "expect this to cost roughly what a full `frob check` costs -- "
        "opt in deliberately, do not make this the default. Purely "
        "additive to scan's own report: never removes, rewrites, or "
        "auto-drops a waiver, and never gates this command's own exit "
        "status -- a collision is reported for a human/agent to "
        "classify, same posture as scan's own NEEDS_REVIEW list.",
    )
    # frob:ticket T-2740
    scan_p.add_argument(
        "--check-liveness",
        dest="waive_audit_check_liveness",
        action="store_true",
        help="T-2740: opt-in, report-only. Classifies each scanned waiver "
        "as NECESSARY (a current gate run's `waived` set shows it actively "
        "suppressing a violation), INERT (its rule has a registered scan-"
        "membership predicate and the waiver's own file structurally falls "
        "outside that rule's scan set -- provably not evaluated, not an "
        "absence-of-finding inference), or UNVERIFIED (neither could be "
        "established; never guessed). This is the honesty audit's missing "
        "half: T-1614 judged a waiver's REASON, never whether the rule "
        "evaluating it can even reach the file it sits in -- 11 RENDER001 "
        "waivers in .claude/hooks/ sat INERT behind exactly that blind "
        "spot (T-2719/T-2740). REPORT-ONLY: never removes a waiver, never "
        "gates this command's exit status -- an INERT verdict is also "
        "evidence the RULE's own scan pathspec may be wrong, not only that "
        "the waiver is stale; treat it as a lead for a human/agent to "
        "investigate the gate, not license to bulk-delete the waiver.",
    )
    complete_p = waive_audit_sub.add_parser(
        "complete",
        help="record a finished pass's verdict and advance the watermark",
    )
    complete_p.add_argument("--json", dest="ticket_json", action="store_true")
    complete_p.add_argument(
        "--reviewed-count",
        dest="waive_audit_reviewed_count",
        type=int,
        required=True,
        metavar="N",
        help="how many waivers were actually classified this pass -- must "
        "match the scan's own count or the watermark is not advanced",
    )
    complete_p.add_argument(
        "--cop-outs",
        dest="waive_audit_cop_outs",
        type=int,
        default=0,
        metavar="N",
        help="how many of the reviewed waivers were cop-outs (0 means the "
        "pass was genuinely clean, not merely unexamined)",
    )
    complete_p.add_argument(
        "--partial",
        dest="waive_audit_partial",
        action="store_true",
        help="T-2485: explicit acknowledgement that this batch does NOT "
        "cover a bounded catch-up pass's whole backlog -- banks exactly "
        "the reviewed batch (advancing catchup_remaining/catchup_covered "
        "in the watermark) instead of refusing outright. Without this "
        "flag, complete still refuses on an incomplete catch-up exactly "
        "as before; passing it never yields a CLEAN verdict while "
        "waivers remain uncovered",
    )
    return waive_audit_p


def _add_ticket_sweep_async_parser(ticket_sub):
    """Register `frob ticket sweep-async <id> --commit <sha>` -- the
    detached child half of the rapid profile's deferred post-land sweep
    (T-1684). Not a verb a developer normally types: `frob ticket land`
    spawns it. It exists as a real subcommand rather than a `-c` code
    string so the deferred sweep is inspectable, re-runnable by hand
    against any commit, and covered by the same CLI surface tests as
    every other verb."""
    ticket_sweep_async_p = ticket_sub.add_parser(
        "sweep-async",
        help="run the deferred post-land unscoped sweep for a landed "
        "ticket (rapid profile; normally spawned by `land`)",
    )
    ticket_sweep_async_p.add_argument("ticket_id", metavar="id")
    ticket_sweep_async_p.add_argument(
        "--commit",
        dest="ticket_sweep_commit",
        required=True,
        metavar="SHA",
        help="the land commit this sweep is verifying, recorded in the "
        "rolling baseline and any filed regression ticket",
    )
    return ticket_sweep_async_p
