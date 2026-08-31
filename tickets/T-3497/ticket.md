---
id: T-3497
title: 'macOS-only: pre-existing-violation shifted-lines attribution raises (bucket
  H, T-3488)'
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_lint_diff_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-3497: BUG002 waiver -- macOS-only defect cannot fail-then-pass on this
    Linux worktree host'
  actor: logan
  at: '2026-08-30'
  old_length: 808
  new_length: 1544
evidence:
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_genuinely_new_violation_still_refuses
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5af72856de16ad3f1c3e29fdcf3f6f2fd57a33a6
---
Found while characterizing T-3488's macOS-only CI set (bucket H, 1 test).

MEASURED (GitHub Actions run 33311990183, macos-latest):
tests/test_ticket_land_lint_diff_attribution.py::...::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
fails with SystemExit: 1. Root cause not yet measured -- the parent
ticket (T-3488) explicitly left this "unknown, measure" and scoped
characterization of buckets C-H as follow-up work, of which this is the
last unclaimed bucket.

Needs: reproduce locally or read the macOS CI log with -vv for this
node id to see what diff/lint-attribution step raised SystemExit(1) that
does not raise on Linux -- likely a line-ending (CRLF) or path-separator
difference in how the "shifted lines" diff is computed/attributed on
macOS's git/diff toolchain vs Linux's.

frob:waive BUG002 reason="T-3497 fixes a macOS-only defect (T-3488 bucket H): os.path.relpath's identity computation misaligns when base/diag.file went through different symlink resolution (macOS /tmp -> /private/tmp). This Linux host's /tmp is a real directory, not a symlink, so base and diag.file already agree without .resolve() and the designated repro test genuinely passes at main here. It can only genuinely fail-then-pass on macos-latest CI (or any host with a symlinked temp dir), which this implementer cannot dispatch from this Linux worktree. Evidence is confirmatory-only on this host by the nature of the defect, not a weak test -- same shape as this drive's other BUG002 waivers (T-3488/T-3496/T-3498/T-3499/T-3500)."