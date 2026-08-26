## Done report

Changed:
  src/frob/tickets/_unlanded.py::_remove_scratch_file (frob:waive WIRE001 now carries
    follow_up="T-2931")

Evidence:
  tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser
  full file: 21/21 pass

Filed: T-2931 -- generalize WIRE001's dynamic-dispatch exemption
  (frob.gates._waive._WIRE001_RESCUE_EXEMPT_RULE, currently covers autouse pytest
  fixtures and pydantic validators) to also recognize atexit.register(...) callbacks,
  so a genuinely-only-atexit-called private function does not need a per-site
  frob:waive WIRE001 follow_up=... at all. Chosen over the alternative "permanent"-
  style waiver shape the ticket asked me to check: src/frob/gates/_waive.py confirms
  WIRE001/WIRE002 have NO permanent-waiver escape (unlike some other rule families) --
  every frob:waive WIRE001 must bind a real, still-open follow_up ticket, by design
  (T-1428). Filed low-priority since this is a real gap but not urgent.

Gates: frob check --ticket T-2914 -- zero gate:WIRE findings anywhere in the repo now
  (confirmed: no WIRE001/WIRE002 lines in the full check output). All FAILs in the tool
  summary (ruff-format, ty, frob-cycle) are repo-wide and pre-existing, unrelated to
  this one-line change (confirmed: none reference src/frob/tickets/_unlanded.py).

### Changed
```
 tickets/T-2914/ticket.md           |  6 +++++-
 tickets/T-2931/ticket.md | 35 +++++++++++++++++++++++++++++++++++
 2 files changed, 40 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_real_directive_anchor_still_flagged_via_real_parser` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 450 warning(s), 850 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC006@tickets/T-2923/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md
