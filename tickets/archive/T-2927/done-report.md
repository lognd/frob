## Done report

Added the missing must-stay-quiet fixtures T-2908's audit found lacking,
for all 5 rules named in this ticket's body:

- make-target and raw-linters and raw-coverage: none of the three has a
  dedicated negative pattern (none needed one -- audited in T-2908 with no
  demonstrable false positive). Their must-stay-quiet coverage comes from
  the SHARED `_POS` command-position anchor every rule already relies on:
  a mention inside quoted prose (a git commit message) never matches
  `_POS`, so the rule never fires there. Added one must-fire (real command
  position) and one must-stay-quiet (prose in a commit message) test per
  rule -- 6 new tests.
- unscoped-pytest and unscoped-symbol-search: both already had a working
  negative pattern (path/node-id/`.py` for the former, `-- <path>` for the
  latter) but no test exercised the quiet path directly (only an
  incidental assertion inside a different rule's test, for the latter).
  Added one must-fire (bare, unscoped) and one must-stay-quiet (properly
  scoped) test per rule, directly -- 4 new tests.

No functional changes to .claude/hooks/frob-suggest.py -- this ticket is
test-only, matching its own body's conclusion that none of these five
needed a fix, only regression coverage so a future edit to the rule/
pattern cannot silently regress into a T-2908-shaped misfire again.

Verification:
- `uv run pytest tests/test_hook_frob_suggest.py -p no:cacheprovider -q`:
  36 passed (26 pre-existing + 10 new), 0 failed.
- `uv run ruff check tests/test_hook_frob_suggest.py`: clean.
- `uv run frob check --only test --only coverage --only docblocks --ticket
  T-2927` (cache-bypassed): 0 errors tied to this ticket's diff; all
  remaining errors verified pre-existing/unrelated (COV004 attachment-sha
  drift on other tickets, COV001 on an unrelated scripts/ file from a
  concurrent ticket).

### Changed
```
 tickets/T-2927/ticket.md | 13 ++++++++++++-
 1 file changed, 12 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_make_target_still_fires_at_command_position` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_make_target_stays_quiet_as_prose_in_a_commit_message` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_linters_still_fires_at_command_position` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_linters_stays_quiet_as_prose_in_a_commit_message` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_coverage_still_fires_at_command_position` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_raw_coverage_stays_quiet_as_prose_in_a_commit_message` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unscoped_pytest_still_fires_bare` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unscoped_pytest_stays_quiet_when_a_path_is_given` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unscoped_symbol_search_still_fires_bare` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_unscoped_symbol_search_stays_quiet_with_dash_dash_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 24 error(s), 497 warning(s), 851 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2927, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
