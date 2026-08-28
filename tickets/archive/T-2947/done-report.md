## Done report

Fixed the drift-refusal path (`_verified_reset_root` / `_refuse_drift_but_unstage`,
src/frob/tickets/_land_git_ops.py) that produced the T-2947 incident: a land
refused mid-squash with GitFailed (drift detected, current tip != recorded
pre_land_tip) used to unstage the INDEX (T-1740) but leave a MODIFIED TRACKED
file's edited WORKING-TREE bytes untouched. For a ticket ledger file this
land's own squash had already written `state: done` into before the drift
was noticed, that is a false `done` legible to any on-disk reader (every
v2-mode ticket-store read is a direct filesystem read, never `git show`)
while `git show HEAD:...` correctly showed nothing of the sort -- exactly
the incident: ledger said done, code absent from main, promoted drafts
absent from main.

Fix: `_restore_modified_tracked_worktree_content` (new), called from
`_refuse_drift_but_unstage` right after the existing index unstage,
restores every TRACKED, MODIFIED-or-deleted working-tree path to
(the now-current, post-drift) HEAD via `git checkout HEAD -- <paths>`.
Deliberately HEAD, resolved fresh, never the stale pre_land_tip -- this
can never destroy the concurrent commit that caused the drift, it only
ever makes a tracked file's on-disk bytes match what HEAD already
legitimately commits. An untracked leftover (a brand-new file this land
staged) is left alone exactly as before (T-1740's own precedent) --
restoring it would delete content, not fix a false read.

Atomicity note the ticket asked me to check: the ledger's `done`
transition and the squash-merge's code content are STAGED TOGETHER in
the SAME `git merge --squash --no-commit` + one final commit
(`_land_squash_apply`/`_land_squash_apply_finish`) -- so a successful
land is already atomic (one commit, both together, or neither). The
defect was never about that commit's own atomicity; it was that a
REFUSED (never-committed) squash could still leave WORKING-TREE bytes
that read as committed to anything treating the filesystem as ground
truth. A reorder was not the right shape here -- there is nothing to
reorder, since state=done and the code change were never two separate
commits to begin with. This is the reconciliation/defense-in-depth
option the ticket named as the fallback, applied at the exact place the
false state could leak from -- not a partial approximation of it.

Proof:
- must-fire: `test_must_fire_modified_tracked_ledger_file_restored_to_head`
  reproduces the REAL failure (drift detected via GitFailed, not an
  approximation) -- a tracked ledger file staged with `state=done`,
  then a genuinely independent concurrent commit advances HEAD past the
  recorded pre_land_tip, then `_verified_reset_root` refuses. Confirmed
  FAILING at parent (--check-repro against 653975ae7, the test-committed-
  alone-first commit) before the fix, PASSING after.
- must-still-pass: `test_no_drift_no_restore_needed` -- the ordinary,
  no-drift path is unaffected, still fully hard-resets.
  `test_must_still_pass_untracked_leftover_is_not_touched` -- a brand-
  new untracked file this land staged is still left alone exactly as
  T-1740 established.
- Existing `TestVerifiedResetRoot` suite (4 tests) and the wider
  Reset/Drift/DirtyMain/Unstage/Squash subset of test_ticket_land.py
  (32 tests) run clean, confirming no regression to the existing
  unstage-only behavior for the cases this fix does not touch.
- Land wall-clock: this fix runs ONLY on the (rare) drift-refusal path
  itself -- a `git checkout HEAD -- <paths>` limited to the paths a
  status scan just found modified -- adding one or two more git spawns
  ONLY when a land is ALREADY refusing. The ordinary successful-land
  path (no drift) never reaches this code at all, so it carries zero
  added cost; the actual land measured for this series (T-2938,
  post-T-2913 profile) was 2m2s and this change touches none of that
  path.

Filed: none.

### Changed
```
 src/frob/tickets/_land_git_ops.py | 128 ++++++++++++++++++++++++++++++++++++--
 tests/test_ticket_land.py         | 113 +++++++++++++++++++++++++++++++++
 tickets/T-2947/ticket.md          |  46 +++++++++++++-
 3 files changed, 280 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestDriftRefusalRestoresModifiedTrackedContent::test_must_fire_modified_tracked_ledger_file_restored_to_head` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDriftRefusalRestoresModifiedTrackedContent::test_must_still_pass_untracked_leftover_is_not_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestDriftRefusalRestoresModifiedTrackedContent::test_no_drift_no_restore_needed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_drift_refusal_still_unstages_the_index` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestVerifiedResetRoot::test_resets_to_the_explicit_pre_land_tip_when_current_matches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 24 error(s), 820 warning(s), 855 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2947, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
