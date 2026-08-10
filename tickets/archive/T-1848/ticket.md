---
id: T-1848
title: FEATURE-kind tickets implicitly lease all of ticket_runner/**, blocking unrelated
  agents; scope --remove cannot narrow it
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: add a repro test proving the CLI_WIRING_FILES narrowing (BUG002 needs a
    test that fails at main, passes at fix)
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets.py::TestScopeMatching::test_feature_kind_implies_cli_wiring_files_in_scope
- tests/test_tickets.py::TestScopeMatching::test_cli_wiring_files_resolve_to_real_paths_on_disk
- tests/test_tickets.py::TestScopeMatching::test_non_feature_kind_does_not_imply_cli_wiring_files
- tests/test_tickets.py::TestScopeMatching::test_cli_wiring_grant_does_not_cover_arbitrary_ticket_runner_files
designated_repro_test: tests/test_tickets.py::TestScopeMatching::test_cli_wiring_grant_does_not_cover_arbitrary_ticket_runner_files
threat: null
component: null
---
Every in-progress FEATURE-kind ticket implicitly leases the ENTIRE
`src/frob/app/ticket_runner/**` package, plus `src/frob/app/config.py`
and `src/frob/__main__.py`, regardless of what it declares in scope.

`src/frob/tickets/_models.py:324`:

    globs = (*globs, *CLI_WIRING_FILES)   # when kind == TicketKind.FEATURE

with

    CLI_WIRING_FILES = {"src/frob/__main__.py",
                        "src/frob/app/config.py",
                        "src/frob/app/ticket_runner/**"}

Because SCOPE IS THE LEASE, that union is not merely permissive -- it
CLAIMS all three for the ticket, and every other agent is refused with
CrossTicketLeakage on any file under them.

OBSERVED COST TODAY. T-1686 is a `kind=feature` epic that has been
in-progress for hours and has written NOTHING anywhere in
`ticket_runner` (verified: `git diff main --stat -- src/frob/app/
ticket_runner/` is empty on its worktree, and its working tree is
clean). It nonetheless blocked:

- T-1841's land (the post-land sweep leaving regression tickets
  untracked -- a defect that has DirtyMain-stalled the fleet five
  separate times today), across multiple attempts and two agents.
- A coordinator `frob ticket scope --remove` of the explicit entry,
  which had no effect at all, because the claim was never explicit.
  That is its own problem: the sanctioned narrowing verb cannot narrow
  an implicit claim, and reports success while changing nothing
  observable.

T-0446 added this rule for a real reason -- a feature that adds a verb
must be able to wire it up, and a ticket scoped only to its new files
blocks at land. That intent is right; the implementation is far too
broad:

1. It attaches to KIND, not to what the ticket actually does. A feature
   that never touches the CLI still claims the whole package.
2. It grants a WHOLE-PACKAGE glob (`ticket_runner/**`) when the real
   need is a handful of registration points (the `Subcommand` enum, the
   runner-name dict, the parser wiring).
3. It is invisible. Nothing in `frob ticket show` discloses it, so an
   agent reading the ticket's declared scope cannot predict what it
   holds, and the agent it blocks cannot see why.

REQUIRED:

1. Narrow the implicit grant to the specific registration sites, not
   `ticket_runner/**`.
2. Better: make it grant-on-use rather than grant-on-kind -- extend the
   effective scope only when the ticket's diff actually touches a wiring
   file, or require an explicit `frob ticket scope --add`. The T-1697
   experience shows the explicit path works fine when the agent is told
   about it up front.
3. Disclose the effective scope in `frob ticket show` and in the
   CrossTicketLeakage refusal. The refusal should say WHY the file is
   claimed -- "implicitly, via the FEATURE CLI-wiring rule" reads very
   differently from "declared in scope", and only one of them is
   actionable by narrowing.
4. `frob ticket scope --remove` must refuse, or at minimum warn, when
   the removed glob is still covered implicitly. Silently succeeding
   while the effective scope is unchanged is the worst outcome -- it
   cost a full round trip today.

WIDER RISK: the workaround is `--allow-cross-ticket`, and the more
routinely that flag is used for false positives like this one, the more
likely a REAL cross-ticket leak rides through unnoticed. A guard that
mostly cries wolf is the same failure mode as a rule waived more often
than it is obeyed.