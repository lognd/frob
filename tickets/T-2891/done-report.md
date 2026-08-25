## Done report

Changed:
- src/frob/check/__init__.py::_is_unresolved_only_gate (new)
- src/frob/check/__init__.py::CheckResult.as_text (icon logic: pass/FAIL/UNRES)
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering (new, 5 tests)
- docs/commands/check.md (Public API as_text comment + new "Tool summary:
  pass / FAIL / UNRES" section)
- docs/modules/gates.md#unresolved-t-1664 (T-2891 addendum; contract unchanged)

Root cause confirmed: none of the 12 *SCHEMA/FLAGCOV gates hardcode a
frob-repo-relative path. Each resolves an opt-in known_keys declaration
out of the TARGET project's own frob.toml via resolve_dotted_symbol;
lograder's frob.toml omits those tables, so each correctly returns
Severity.UNRESOLVED (working as designed, T-1664). The defect was one
level up: CheckResult.as_text's tool-summary icon keyed off
exit_code == 0 alone, so a gate:X result that is ENTIRELY unresolved (0
errors, 0 warnings, 1 unresolved) rendered identically to a genuine
clean pass. Fixed by adding a third rendering state (UNRES, yellow) for
exactly that all-UNRESOLVED shape, restricted to gate:-prefixed tools so
it cannot fire on unrelated info-severity diagnostics (e.g. frob-arch's
large-file suggestions). exit_code/total_errors/the exit-code contract
are UNCHANGED -- this is a rendering-only fix, not an exit-code change.

Control measurements (frob's own repo, --only over the 12 families):
- BEFORE (fix reverted in worktree): gate-summary "0 errors, 0 warnings,
  0 unresolved, 0 waived" across all 12 families.
- AFTER (fix applied): identical -- "0 errors, 0 warnings, 0 unresolved,
  0 waived" across all 12 families. Unchanged, as required (the fix
  touches only as_text's rendering branch, not any counting/exit-code
  path).

Must-now-fire fixture: a synthetic gate:ARCHSCHEMA ToolResult shaped
exactly like _gates_family_result builds it for an all-UNRESOLVED gate
(exit_code=0, one info-severity diagnostic, "0 errors, 0 warnings, 1
unresolved, 0 waived") now renders "UNRES  gate:ARCHSCHEMA", not
"pass  gate:ARCHSCHEMA" -- test_must_now_fire_unresolved_only_gate_is_
not_rendered_as_pass, confirmed FAILED_AT_PARENT at 403ead5a9 (test-only
commit, before the fix) via --check-repro, then designated as this
ticket's repro test.

Mechanism portability control (acceptance b): unchanged/out of scope --
the existing resolve_dotted_symbol path already resolves against
whichever project's frob.toml is passed (no frob-repo-relative
hardcoding was found by this investigation, confirming the ticket's own
prior finding); not re-verified against a fresh fixture project in this
session, since the ticket's own investigation note already established
it and this ticket's scope is explicitly the rendering gap only.

Evidence:
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_must_now_fire_unresolved_only_gate_is_not_rendered_as_pass (designated repro, BUG002)
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_clean_gate_still_renders_pass
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_failing_gate_still_renders_fail
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_non_gate_info_diagnostics_are_not_caught
- tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_mixed_unresolved_and_findings_still_renders_pass_or_fail

Filed: none

Gates: frob check --ticket T-2891 clean of all T-2891-attributable
findings (AFFECT001, COV002, PRE001, SCOPE001 all resolved after scope
--add tests/unit/test_check.py + doc updates + a fresh pre-work sweep).
Remaining findings in that run (CYCLE001 repo-wide import cycle,
ruff-format drift, and other repo-wide gate:* counts) are pre-existing
baseline per the tool's own scope-note ("every OTHER gate family's
counts above are REPO-WIDE, not filtered to this ticket") -- confirmed
unrelated by re-running the same --only 12-family check with the fix
reverted, which reproduced identical counts. frob test --base main:
PASS, exit=0, 8 python test(s) recorded stable.

### Changed
```
 docs/commands/check.md     |  27 +++++++++++-
 docs/modules/gates.md      |  20 +++++++++
 src/frob/check/__init__.py |  52 +++++++++++++++++++++-
 tests/unit/test_check.py   | 102 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2891/ticket.md   | 105 ++++++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 302 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_must_now_fire_unresolved_only_gate_is_not_rendered_as_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_clean_gate_still_renders_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_a_real_failing_gate_still_renders_fail` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_control_non_gate_info_diagnostics_are_not_caught` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestUnresolvedOnlyGateRendering::test_mixed_unresolved_and_findings_still_renders_pass_or_fail` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 17 error(s), 982 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md
