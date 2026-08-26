---
id: T-2893
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2875):
  13 new (rule, file) identit(ies), 12 finding(s) (COV004, DOC006)'
state: done
kind: bug
origin: agent
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/coordinator-scripts.md
- tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
- tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md
- tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md
- tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt
- tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md
- tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md
- tickets/T-2884/ticket.md
- tickets/T-2886/ticket.md
findings:
- - COV004
  - tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
- - COV004
  - tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- - COV004
  - tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
- - COV004
  - tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md
- - COV004
  - tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md
- - COV004
  - tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- - COV004
  - tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md
- - COV004
  - tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt
- - COV004
  - tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md
- - COV004
  - tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md
- - DOC006
  - docs/guides/coordinator-scripts.md
- - DOC006
  - tickets/T-2884/ticket.md
- - DOC006
  - tickets/T-2886/ticket.md
evidence_scope:
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: doc-fix ticket has no reproducible code defect, evidence
    is necessarily confirmatory'
  actor: logan
  at: '2026-08-26'
  old_length: 5430
  new_length: 5809
evidence:
- tests/test_docptr_gate.py::TestDoc006Waive::test_waive_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 65a1bb0dad79c9a5c2aa3d55c443685f046d5a11
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2875) at commit cab0f9fb38348bde2d2dc7e55c08b3d8edd8aa4d found 13 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (13), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 12 actual finding(s) across those 13 identit(ies).

New (rule, file) identit(ies) filed here:

- COV004  tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- COV004  tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
- COV004  tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md
- COV004  tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- COV004  tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md
- COV004  tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt
- COV004  tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md
- COV004  tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md
- DOC006  docs/guides/coordinator-scripts.md
- DOC006  tickets/T-2884/ticket.md
- DOC006  tickets/T-2886/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV004  tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2884/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2886/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="this is a ledger/doc correction filed as kind=bug (two DOC006 findings fixed via frob:waive comments on illustrative/historical references); there is no code defect to reproduce with a failing-at-parent test, so the bound evidence is confirmatory by nature -- it demonstrates the frob:waive DOC006 mechanism this fix relies on, not a behavior change"