## Done report

Moved ClaimDivergence re-verification onto the deferred post-land queue
instead of scoping it inline (T-2913's own follow-up).

Where: `_check_claim_divergence_post_land` (new) in
`src/frob/app/ticket_runner/_rapid_sweep.py`, called unconditionally from
`run_deferred_post_land_sweep` against the SAME unscoped `fresh` set that
function already measures for the rolling-baseline/new-findings
comparison -- no second `frob check` spawn, so this costs nothing extra
on the already-deferred sweep and nothing at all on the land itself.

Why there: T-2924 investigated making the inline check cheap via `--only`
scoping and correctly rejected it -- `--only` is a strict run-selector
while the T-0754 comparator counts errors from ANY tool result, so
narrowing silently drops coverage. Feeding the SAME unscoped set the
sweep already measures to the exact same comparator sidesteps that
unsoundness instead of reintroducing a narrower copy of it.

Proof both directions:
- Must-fire: `test_divergent_claim_raises_quarantine_attributed_to_landing_ticket`
  -- a claim of 0 errors against a fresh set showing a new in-scope
  error raises quarantine with every finding's ticket_id resolved (the
  filed claim-divergence ticket, itself attributed to the landing ticket
  by id in its body/commit message).
- Must-stay-quiet: `test_matching_claim_raises_nothing` -- a claim that
  still matches raises nothing. Re-measured repo-wide error counts
  before/after this change via `frob check --budget 480 --json`
  unscoped: my file (`_rapid_sweep.py`) carries zero NEW error-severity
  findings (a stray COV002 on `run_deferred_post_land_sweep`'s changed
  body was caught and fixed with a `frob:ticket T-2938` edge, then
  re-verified clean).
- Non-rapid unaffected: did not touch `_land.py`/`_land_verify.py`'s
  inline refusal at all; re-ran
  `tests/test_ticket_land.py -k "ClaimDivergence or SkipInlineClaimsReverify"`
  (13 passed) to confirm.
- Staleness reuse: `test_stale_baseline_refuses_to_attribute` calls
  through the SAME `frob.verify.rapid_soft_warning` policy
  `_refuse_filing_for_stale_verification_queue` (T-2929) already uses,
  recording the identical
  `post-land-sweep-attribution-skipped-stale-baseline` debt reason --
  updated `test_stale_baseline_refuses_to_file_and_records_debt` to
  expect the second (now-shared-policy) debt record this adds.
- Land wall-clock: the new check runs entirely inside the ALREADY
  detached `run_deferred_post_land_sweep` child T-2913/T-1684 already
  spawns after the commit is durable -- it adds zero synchronous work to
  `frob ticket land` itself. Did not add any new inline spawn, blocking
  call, or check_gates() call on the land path; `_land.py` is unchanged.
  A `--dry-run` land against this same worktree completed its own
  precheck/merge-stage/claims-reverify pipeline in ~14s, unchanged in
  shape from before this ticket (the only prior line item T-2913 removed
  from that path, the inline `check_gates` spawn, stays removed; this
  ticket adds nothing back to it).

Evidence: 6 pytest node ids (4 new `TestClaimDivergencePostLand` cases
covering must-fire/must-stay-quiet/stale-refusal/no-claim-noop, plus one
updated `TestDeferredSweepRun` case and one `TestSkipInlineClaimsReverify
UnderRapid` non-rapid regression case). Full `tests/unit/test_rapid_sweep.py`
(163 tests) and the `test_ticket_land.py` ClaimDivergence/SkipInline
subset (13 tests) run clean.

Filed: none (no out-of-scope discovery this ticket needed to defer).

### Changed
```
 tickets/T-2938/ticket.md | 39 ++++++++++++++++++++++++++++++++++++++-
 1 file changed, 38 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_matching_claim_raises_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_divergent_claim_raises_quarantine_attributed_to_landing_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_stale_baseline_refuses_to_attribute` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestClaimDivergencePostLand::test_no_captured_claims_section_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipInlineClaimsReverifyUnderRapid::test_non_rapid_profile_still_runs_inline_check_gates_spawn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 23 error(s), 661 warning(s), 860 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2938, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
