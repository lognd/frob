---
id: T-2019
title: Re-verify 10 already-landed BUG002 repro designations against T-2005's PYTHONPATH
  fix
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-1546/ticket.md
- tickets/T-1670/ticket.md
- tickets/T-1749/ticket.md
- tickets/T-1838/ticket.md
- tickets/T-1841/ticket.md
- tickets/T-1848/ticket.md
- tickets/T-1853/ticket.md
- tickets/T-1861/ticket.md
- tickets/T-1882/ticket.md
- tickets/T-1907/ticket.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2005 fixed a bug where `_run_designated_test`'s PYTHONPATH override was
silently dropped (`run_argv` had no `env` parameter), so a bug/security
ticket's BUG002 repro verdict could read PASSED_AT_PARENT against the
CURRENT (already-fixed) source instead of the actual parent commit's
source, for any pure-Python-only fix.

10 already-landed tickets carry a non-null `designated_repro_test` and
are therefore suspect: T-1546, T-1670, T-1749, T-1838, T-1841, T-1848,
T-1853, T-1861, T-1882, T-1907 (denominator: `git grep -l
"designated_repro_test:" tickets/archive` filtered to non-null).

Re-verify each: `frob ticket evidence <id> --check-repro <designated
node-id> --base-ref <the ticket's own recorded parent commit>` under the
now-fixed `run_argv`, and confirm the verdict is unchanged
(FAILED_AT_PARENT, not a newly-discovered PASSED_AT_PARENT). Any ticket
whose verdict FLIPS to PASSED_AT_PARENT under the fix had confirmatory-
only evidence all along and needs its own follow-up (stronger evidence,
or an honest disclosure that the fix cannot currently be proven).

<!-- frob:no-behavior-change reason="T-2019 is a re-verification/
investigation ticket with no source-code fix of its own -- it re-runs
--check-repro against 9 already-landed tickets' own parent refs and
reports what it measures (see done-report.md). It changes no
production code, so there is no defect for a repro test to reproduce;
its bound evidence (playbook 5's docs-only CLI-dispatch precedent)
genuinely passes at the parent commit, matching this directive's own
inverted obligation. The actual finding (all 9 return NO_VERDICT
against squashed main history, a structural gap, not a confirmatory-
only-evidence trap) is recorded honestly in the Done report and filed
as T-2025." -->

## Done report

Re-verified the 10 named tickets' `designated_repro_test` bindings
against T-2005's fixed `--check-repro` (PYTHONPATH override restored in
`_run_designated_test`).

DENOMINATOR CORRECTION: T-1670's `designated_repro_test` is `null`
(kind=feature, no BUG002 claim of its own -- it is the ticket that
ADDED `--designate-repro`, not a bug ticket with a repro). It does not
belong in the non-null denominator T-2019's own description used; the
real suspect set is 9, not 10.

For each of the other 9, ran (from a merge-base worktree at main's
current tip, natives built):
  uv run frob ticket evidence <id> --check-repro --base-ref <ref> --archived
using <ref> = the parent of that ticket's own `land T-<id>` commit on
main (the commit immediately before the fix published), e.g. T-1546:
land=4b6695745, base-ref=57caecf76 (its immediate parent on main).

MEASURED RESULT: all 9 returned NO_VERDICT, exit code 1, message
"could not even COLLECT at <ref>". None returned FAILED_AT_PARENT
(confirmed) and none FLIPPED to PASSED_AT_PARENT (confirmatory-only)
either -- the check could not run at all against main's post-land
history for any of them.

ROOT CAUSE (confirmed directly, not inferred): `frob ticket land`
squashes every worktree commit into ONE commit on main -- T-1546's own
worktree commits (e.g. 086172ad8) are provably NOT ancestors of main
(`git merge-base --is-ancestor` returns false); only the single land
commit is. Verified by reading the git blob directly at two of the
nine parent refs: T-1546's designated test method
(TestRepointer::test_per_ticket_ledger_file_evidence_rewritten) and
T-1907's (TestAssertTouchedFilesTypeCheckPreLand::
test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error) are
BOTH absent from the test file at the parent ref, while the surrounding
test class IS present -- i.e. the specific new test method and its
fix land together, atomically, in the squash commit. There is
structurally no commit in main's history where the test exists without
the fix, so `--check-repro`/`bug_repro_outcome_at_ref` run post-land
against any main-history ref cannot produce a verdict for a newly-added
repro test -- this is independent of the T-2005 PYTHONPATH bug and
would reproduce identically on a perfectly correct checkout.

CONCLUSION: this ticket's designated method (post-land re-verification
via `--check-repro` against main history) cannot answer the question it
was asked to answer, for any of the 9. I am not able to report "9 of 9
hold" or name any that "do not hold" against a FAILED_AT_PARENT
baseline, because no verdict was reachable for any of them -- reporting
either would be guessing, not measuring. This is disclosed, not
silently converted into a pass.

Filed T-2025: the structural gap itself (`--check-repro`
cannot verify a squashed ticket's repro test post-land, for any
ticket, not just these 9) -- proposes either recording the pre-squash
test-added commit at land time, or documenting the permanent
limitation so this is not re-asked of a future agent.

No source code changed -- this ticket is investigation-only; the only
worktree file touched is this ticket's own ledger block (tickets/T-2019/
ticket.md) plus the new draft ticket's own file, both in the always-
in-scope ledger.

Floor before: not independently measured (contention from 6 concurrent
agents; playbook 3b/3c bar an unscoped `frob check --only gates` from a
sub-agent, and this ticket made no source change to have a "before"
value to compare a "delta" against). No source under gates was touched.

### Changed
```
 tickets/T-2019/ticket.md           |  2 +-
 tickets/T-2025/ticket.md | 72 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 73 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/unit/test_tickets_evidence_only_scope.py
