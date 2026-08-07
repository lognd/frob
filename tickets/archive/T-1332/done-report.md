## Done report

Added the two verification-gap tests T-1326's review flagged, plus one
extra negative-case test to prove the rename-attribution behavior does
not open a new laundering vector:

1. Acceptance [0] (branch-merged-main deletion attribution): added
   `test_branch_merges_main_after_main_deletes_a_waiver_still_allowed`,
   which -- unlike the existing `test_merge_base_drift_deletion_on_main_
   side_not_counted` (main deletes, branch never re-syncs at all) --
   makes the landing branch run a REAL `git merge main` after main's
   deletion commit, the shape every worktree agent's warm-up actually
   performs. Passes as-is: `_true_merge_base` is computed fresh at land
   time, so after the merge the true common ancestor advances past
   main's deletion commit and it correctly drops out of `merge_base..
   HEAD`. No regression found; this locks in behavior that was
   previously only argued from git merge-base construction, never
   actually exercised.

2. Acceptance [1] (rename-aware attribution): added three tests --
   `test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path`,
   its negative mirror
   `test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses`,
   and the uncommitted-state analog
   `test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path`.
   All pass as-is, proving WHICH path `_waive_deletions_in_diff`
   attributes a rename+edit deletion to: the pre-image (OLD) path off
   the diff hunk's `--- a/<path>` header, as the docstring already
   claimed but nothing previously exercised. Declaring the OLD path in
   the ticket's scope is sufficient to allow the land; declaring
   neither old nor new path still correctly refuses (the negative test)
   -- a rename does not become a way to dodge the guard.

No production code change: both verification gaps close with new tests
only, no attribution bug was exposed by either. `_land_merge.py` (this
ticket's second scope glob) turned out to hold none of the actual
waive-guard code any more -- T-1251 (already landed) moved that whole
family to `src/frob/tickets/_land_git_ops.py`; the guard functions this
ticket exercises (`_uncommitted_waive_deletions`,
`_committed_out_of_scope_waive_deletions`, `_true_merge_base`,
`_waive_deletions_in_diff`) all live there today. No edit was needed in
either file, so this scope-staleness did not block anything, but is
worth noting for anyone reading `_land_merge.py` expecting to find this
code.

Changed: none (tests only)

Added:
  tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal.test_branch_merges_main_after_main_deletes_a_waiver_still_allowed
  tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution (new class, 3 tests)

Evidence: 4 new tests, all passing -- see evidence list below, bound to
both acceptance criteria (the CLI's `--accepts` binds an index to the
ticket's full evidence list, not a per-call subset, so both indices
show all 4 ids; each test itself is scoped to exactly the acceptance
criterion described above). Full targeted run: 15 passed
(`tests/test_ticket_land.py -k "WaiveRewrap or WaiveDeletion or
RenameAware"`, covering this ticket's new tests alongside T-1388's and
the pre-existing T-1323/T-1326/T-1468 suite in the same area, confirming
no regression).

Gates: `frob check --only test --ticket T-1332` 0 errors. `frob check
--only coverage --only scope --only prework --only fmt --ticket T-1332`:
gate:PRE/gate:FMT/gate:TODO 0 errors. gate:COV (1 error) and gate:SCOPE
(6 errors) repeat the SAME pre-land, same-worktree artifact already
disclosed in T-1368's and T-1388's Done reports -- T-1368/T-1359/T-1388
are closed tickets whose own commits are still unlanded in this shared
worktree, and their symbol/scope coverage ties against OTHER, unrelated,
currently open tickets once THIS ticket's own `--ticket` selection no
longer prefers them. None of these findings are against
`tests/test_ticket_land.py`, the only file T-1332 touched (0 SCOPE001/
COV002 against it); self-resolves once the earlier tickets land as
their own commits.

Filed: none -- both acceptance gaps close with tests alone, no
attribution bug found to fix, no new residue.

### Changed
```
 design/frob.strata                            |  16 +-
 docs/design/registry/EXHAUSTIVENESS-GATE.md   |   7 +
 docs/modules/release.md                       |  37 +-
 src/frob/app/ticket_runner/_land_cmd.py       |  26 +-
 src/frob/gates/_fmt_directives.py             |  34 +-
 src/frob/registry/_staleness.py               |  30 +-
 src/frob/release/__init__.py                  |  69 +++-
 tests/test_gates_fmt_directives.py            |  42 +++
 tests/test_registry_staleness.py              |  32 ++
 tests/test_release.py                         |  97 +++++
 tests/test_ticket_land.py                     | 222 +++++++++++
 tests/unit/test_ticket_runner_land_release.py |  46 ++-
 tickets.md                                    | 508 +++++++++++++++++++++++++-
 13 files changed, 1123 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution::test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
