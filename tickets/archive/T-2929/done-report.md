## Done report

Changed:
  src/frob/app/ticket_runner/_rapid_sweep.py::_refuse_filing_for_stale_verification_queue (new)
  src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep (modified: gates the
    regression-ticket filing decision behind the new helper)
  docs/modules/tickets-verify-sweep.md (new bullet documenting the T-2929 behavior)
  tests/unit/test_rapid_sweep.py (2 new tests, both proof directions)

Evidence:
  tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt
    (DESIGNATED REPRO: FAILED_AT_PARENT verified at commit 8999970fd -- the test was committed
    alone, without the fix, confirmed to fail there, then the fix was committed on top and the
    test passes)
  tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_fresh_baseline_files_normally_no_new_noise
  full file: 158/158 pass

Part (a): drain result, with real numbers.
  Before: `frob verify status --path /home/logan/projects/frob` reported watermark age 438s,
    20 commits since watermark (warn threshold 5) -- WARNING firing, matching the coordinator's
    "stale and unread" pattern (the earlier 53-commit/7304s reading had already been partially
    drained by other agents' lands between the coordinator's message and my measurement).
  Drain attempt: `frob verify now --path /home/logan/projects/frob` (single foreground call,
    timeout 540 shell + 600000ms tool) reported "verify worker: queue empty, nothing to verify"
    / "advanced watermark: False". This is NOT a silent failure to drain -- it is the correct,
    honest answer given what this verb actually does: `frob.verify.run_coalesced_verification`
    only advances the watermark by draining the durable `VerifyQueueEntry` QUEUE (T-1687/1688),
    and that queue was genuinely empty (0 unverified depth) at measurement time. The 20-commit
    "debt" `rapid_soft_warning` reports is a SEPARATE, raw git-commit-distance metric
    (`commits_since_watermark`) that grows regardless of queue content and this verb cannot move
    when the queue itself has nothing queued -- confirmed by reading `frob.verify._backpressure.
    rapid_soft_warning`'s own docstring ("falling back to the queue's own depth only when the
    git count is unavailable") and `frob.verify._worker.run_coalesced_verification` (returns
    `WorkerOutcome(status="empty")` and does nothing else when `entries` is empty). Reporting
    this plainly rather than treating "nothing to verify" as "drained": the raw commit-distance
    metric genuinely cannot be reduced by `frob verify now` while the queue stays empty -- this
    is itself worth a follow-up (T-2310's own automatic per-land drain, `frob.verify._drain`,
    is the mechanism that's supposed to keep this bounded automatically; whether it is actually
    running/effective was not re-verified here, out of this ticket's declared scope).

Part (b): escalation option chosen -- REFUSE TO ATTRIBUTE (of the three offered: hard-error,
  auto-drain, refuse-to-attribute). Full reasoning in the ticket body and the new code
  docstring; summary: a hard error would violate rapid's explicit "never blocks" contract
  (T-1692), auto-drain from inside an already resource-contended detached sweep child has no
  special leverage over debt mostly accrued by OTHER concurrent lands, and refuse-to-attribute
  fixes the actual observed harm (3 of 4 recent sweep-filed "regression" tickets -- T-2868,
  T-2881, T-2882 -- were false positives from this exact stale-attribution-window shape,
  dropped after measurement) at the exact point it is produced, at zero extra cost, using a
  staleness signal (`frob.verify.rapid_soft_warning`) that already existed in this codebase for
  this exact purpose but was never consulted by the sweep's filing decision.

Part (c): both proof directions, plus before/after repo-wide measurement.
  Must-fire: test_stale_baseline_refuses_to_file_and_records_debt (designated repro, verified
    FAILED_AT_PARENT).
  Must-stay-quiet: test_fresh_baseline_files_normally_no_new_noise (identical to the pre-existing
    test_new_findings_file_a_ticket_and_rebaseline shape, confirms unchanged behavior when
    rapid_soft_warning returns None).
  Re-measurement (unscoped `frob check`, my 3 touched files reverted to main vs restored):
    before: 27 errors, 599 warnings, 847 waived
    after:  27 errors, 601 warnings, 858 waived
  Line-by-line diff of the full finding set confirms: 0 new unwaived errors; the +2 warnings and
  +11 waived are entirely my own new FMT001 waivers (unwrappable long test-node-id directive
  lines, same shape as the existing src/frob/app/_json_guard.py precedent) and expected
  line-count/function-length metric text changes (LARGE001/ARCH001, both pre-existing waived/
  over-threshold findings whose NUMBER changed, not new findings); everything else in the diff
  (a lock-order-cycle rename, a COV006 pair on an unrelated test file, a PERF008 hook-path
  string) is other agents' concurrent lands landing between the two measurement runs, confirmed
  by content (files I never touched).

Filed: none (this IS the filed ticket)

Gates: frob check --ticket T-2929 -- all findings in the touched-set are pre-existing/
  unrelated (frob-cycle, gate:DOC/TICK repo rot, EXHAUST003 resolution gaps) except: COV002
  (fixed: added frob:ticket T-2929 to run_deferred_post_land_sweep), DRIFT001 (fixed:
  frob ack'd the modified function), a ruff E501 (fixed), 6 FMT001 findings on unwrappable long
  test-node-id directive lines (fixed: waived, matching the existing _json_guard.py precedent),
  and ruff-format on the test file (fixed: ran ruff format).

### Changed
```
 docs/modules/tickets-verify-sweep.md       |  25 ++++
 frob.lock                                  |  20 ++-
 rapid-debt.jsonl                           |   2 +
 src/frob/app/ticket_runner/_rapid_sweep.py | 198 ++++++++++++++++++++++++-----
 tests/unit/test_rapid_sweep.py             |  93 ++++++++++++++
 tickets/T-2929/done-report.md    |  95 ++++++++++++++
 tickets/T-2929/ticket.md         | 149 ++++++++++++++++++++++
 7 files changed, 551 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_stale_baseline_refuses_to_file_and_records_debt` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_fresh_baseline_files_normally_no_new_noise` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 19 error(s), 616 warning(s), 858 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
