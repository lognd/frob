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
