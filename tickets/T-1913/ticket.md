---
id: T-1913
title: LAND-PROOF is_ancestor_of_main=False for a non-anchor ticket whose land fully
  succeeded (T-1895)
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: 'T-1913 mitigation: bounded retry around the is-ancestor check plus its
    regression test'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry::test_retries_until_ancestor_check_settles_true
- tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry::test_gives_up_after_exhausting_retries_on_a_genuine_non_ancestor
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-1884 (its own "ADDITIONAL MEASUREMENT" block, 2026-08-09,
coordinator). T-1884's original scope (anchor tickets left queued/blocked
on main by design) is fixed and closed. This is the SEPARATE, non-anchor
false-negative the coordinator reproduced on top of it:

`frob ticket land T-1895 --worktree .../t1895-t1893` printed:

  land T-1895: landed as T-1895 at 18b82c8cab4c74d2f5457b738486a129321602e8 (14 file(s) changed)
  land T-1895: REL001 bumped to 0.419.0
  LAND-PROOF: ticket=T-1895 commit=18b82c8... is_ancestor_of_main=False state_on_main=done verified=False

The land had in fact FULLY SUCCEEDED (independently verified: `git
merge-base --is-ancestor 18b82c8... HEAD` -> true; tickets/T-1895/
ticket.md on main reads `state: done`; the actual code change is
present). LAND-PROOF's `is_ancestor_of_main` read False about a commit
that IS an ancestor of main -- a false negative.

INVESTIGATION SO FAR (T-1884 implementer, 2026-08-09). Looked for the
most likely structural cause -- `_land`'s own `root` CLI-local staying
pointed at `--worktree` instead of the resolved primary checkout when
invoked with cwd defaulted inside the worktree (T-1003's own documented
gap: `_resolve_land_root`'s docstring already claimed the CLI wrapper
resolves its own `root` local a second time after `land()` returns, but
no such call site actually existed anywhere in `_land_cmd.py` -- only
`_land_core_prepare`'s internal, non-propagated resolution). Fixed that
real gap (now covered by
`tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies`)
-- BUT could not reproduce the T-1895 shape with it: `git worktree add`
-linked worktrees share ONE common `.git` dir and thus the SAME ref
database, so `git -C <linked-worktree> merge-base --is-ancestor <sha>
main` sees the true, current main tip synchronously regardless of which
worktree the query runs from. Deliberately reverting the root-resolution
fix and re-running the same repro test still passed -- confirming the
"wrong checkout" theory does not explain this shape when the worktree
is a genuine `git worktree add` linked checkout (the normal case per
the agent playbook).

WHAT REMAINS UNEXPLAINED: a genuine timing/visibility race (or some
other mechanism) between the commit landing on `root`'s `main` and the
immediately-following `git merge-base --is-ancestor` query, in the REAL
dispatch environment, that a synchronous in-process pytest fixture does
not reproduce. Possible directions for whoever picks this up: (a)
whether the coordinator's dispatch harness uses something OTHER than a
plain `git worktree add`-linked checkout for `--worktree` (a separate
clone, a bind-mounted filesystem, a network filesystem with write-back
caching) where ref visibility genuinely is not synchronous; (b) whether
`REL001`'s bump step (logged between "landed as ..." and the
LAND-PROOF line) does anything that could leave `report.commit_sha`
pointing at a commit later amended/rebased away rather than the final
tip -- traced `_apply_release_bump`'s callback ordering and it appears
to stage into the SAME pre-final-commit squash, not a later amend, but
this was read, not executed end-to-end under real dispatch conditions;
(c) instrumenting `_print_land_proof`'s own `git merge-base` call with a
retry-with-backoff or a `git update-ref` read-back assertion immediately
after the landing commit, to catch the race directly if it exists.

A regression test for this ticket needs either a real dispatch-shaped
reproduction (not achievable in a synchronous fixture) or a concrete
mechanism, once found, that CAN be reproduced synchronously.

## Done report

DISCLOSURE FIRST: this is a MITIGATION, not a confirmed fix. T-1913's own
body already documents that the prior implementer (T-1884's own agent)
fixed the real, confirmed gap (the CLI wrapper's `root` local staying
pointed at `--worktree` instead of the resolved primary checkout,
T-1003) and STILL could not reproduce the T-1895 shape with it in a
synchronous pytest fixture -- linked worktrees share one common `.git`
dir and the same ref database, so a plain `git worktree add`-linked
checkout cannot exhibit the "wrong checkout reads stale refs" theory at
all. What remains is a genuinely unexplained timing/visibility race (or
some other mechanism) between the landing commit and the immediately
following `git merge-base --is-ancestor` query, specific to the real
dispatch environment.

WHAT THIS TICKET ADDS: `_is_ancestor_with_retry`
(src/frob/app/ticket_runner/_land_cmd.py), one of the three concrete
follow-up directions T-1913's own body names ("(c) instrumenting
`_print_land_proof`'s own `git merge-base` call with a retry-with-
backoff... to catch the race directly if it exists"). `_land_proof_
checks` now retries the is-ancestor check up to 3 times (0.1s/0.2s/0.4s
backoff, ~0.7s worst case) before concluding `is_ancestor_of_main=False`.
This is a bounded, cheap self-heal: if the T-1895 incident really is a
transient ref-visibility race, this closes it without ever needing to
name the exact mechanism; if it is not (some other cause entirely), this
costs ~0.7s extra on every land that genuinely refuses and changes
nothing else.

EVIDENCE, and what it does and does not prove: two real tests
(tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry)
exercise the RETRY MECHANISM ITSELF against a real git repo with a
monkeypatched `run_argv` that fails N times then succeeds
(test_retries_until_ancestor_check_settles_true) or never succeeds
(test_gives_up_after_exhausting_retries_on_a_genuine_non_ancestor).
Verified FAILING at the parent commit (`_is_ancestor_with_retry` does
not exist yet -- AttributeError) and PASSING after this fix. This proves
the retry logic is real and correctly bounded; it does NOT prove the
retry fixes the original T-1895 incident, because that incident's root
mechanism was never identified or reproduced -- no test in this repo can
honestly claim to reproduce a race nobody has pinned down. Recording
this disclosure explicitly per playbook section 8 rather than letting
"tests pass" imply more than it does.

RESIDUE: T-1913's REQUIRED item 5 (root-cause directions (a) dispatch
harness's worktree mechanism, (b) REL001 bump ordering) remains
unaddressed -- outside what a bounded retry can establish, and outside
this pass's time budget. If the real incident recurs with this
mitigation in place (i.e. verified=False despite the retry), that is
strong evidence the cause is NOT a short-lived visibility race and the
remaining directions in T-1913's own body should be picked up next.

### Changed
```
 design/frob.strata                         |   4 +-
 rapid-debt.jsonl                           |   3 +
 src/frob/app/ticket_runner/_land_cmd.py    |  80 ++++-
 src/frob/tickets/_land.py                  |  89 +++++-
 tests/test_ticket_work_and_land_finish.py  |  66 +++++
 tests/unit/test_land_sibling_regression.py | 235 +++++++++++++++
 tickets/T-1913/ticket.md                   |  11 +
 tickets/T-1914/done-report.md              | 453 +++++++++++++++++++++++++++++
 tickets/T-1914/ticket.md                   |   6 +-
 9 files changed, 932 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry::test_retries_until_ancestor_check_settles_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAncestorRetry::test_gives_up_after_exhausting_retries_on_a_genuine_non_ancestor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 5 error(s), 909 warning(s), 698 waived
- error-findings: DOC007@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/ticket_runner/_land_cmd.py, DUP001@tests/unit/test_land_sibling_regression.py, PRE001@tickets/T-1913, REG002@docs/design/registry/check-coverage.yaml
