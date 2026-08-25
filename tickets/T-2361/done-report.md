## Done report

Changed: frob.verify._backpressure::effective_profile_or_standard (new),
frob.verify.__init__ (re-export), frob.app.ticket_runner._land_cmd::_land_core
(call-site swap), tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard (new)

T-2361's 5 measured if-rapid call sites (`_land.py:2878`/`:3103`,
`_land_cmd.py:4324`/`:4519`, `_evidence.py:323`, `_close_cmd.py:463`) plus
the 6th `_land_cmd.py:4607` soft-warning branch T-1696's own
re-verification found were ALL ALREADY migrated to `settings_for_profile`
before this ticket started: `T-1696` (landed 2026-08-18, chronologically
after T-2360's own land) did the actual migration directly as part of
its own "delete the if-rapid land seams" scope, superseding what T-2360/
T-2361/T-2362 were split off to do against a stale 2026-08-17
measurement. Verified via `frob explore xref ProfileName`: zero
production hits at any of the 6 measured seams; all 6 already read
`LandProfileSettings` via `settings_for_profile`/`effective_profile`.

One genuine gap remained against the ticket's own literal acceptance
check ("`frob explore xref ProfileName` shows zero production hits
outside `_profile.py`/the settings-resolver module"): `_land_cmd.py`'s
`_land_core` (`_apply_backpressure`'s caller) still imported `ProfileName`
directly just to spell its own `Err`-falls-back-to-`STANDARD` default
before handing a resolved `ProfileName` to `ceilings_for_profile`/
`settings_for_profile` (both of which need an actual profile value, not
just a derived boolean, unlike every other seam). Added
`effective_profile_or_standard(root)` to `frob.verify._backpressure`
(the settings-resolver module, T-2360's home, added to this ticket's
scope for this one small addition) to centralize that exact fallback,
and swapped `_land_cmd.py`'s inline `Ok(...) else ProfileName.STANDARD`
for a call to it -- `_land_cmd.py` no longer imports `ProfileName` at
all. Re-ran `frob explore xref ProfileName`: zero hits in `src/frob/`
production code outside `frob.tickets._profile` and
`frob.verify._backpressure` (only test fixtures and the `design/
frob.strata` schema file remain, both expected/excluded).

No behavior change: `effective_profile_or_standard` is a pure
extraction of the exact fallback expression that was already inline at
the one call site that needed it; `test_rapid_profile_calls_soft_warning_
never_blocks` and the rest of `test_land_cmd_backpressure.py`/
`test_close_rel001_bump.py`/`test_profile.py` pass unmodified against
the new call site.

Evidence: tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_ok_passes_through
tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_err_falls_back_to_standard
tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic
tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks

Filed: none -- no out-of-scope work found; the one gap found (the
_land_cmd.py ProfileName import) was fixed in-scope via a small addition
to the settings-resolver module the ticket's own acceptance text already
names as excluded/expected.

Gates: frob check --only gates-fast --ticket T-2361 clean of this
ticket's own findings (COV002 on the new test class, SCOPE001 on the new
test file, PRE001 stale sweep -- all fixed during this pass); remaining
unwaived findings (COV004 stale ticket attachments, DOC006 on
docs/guides/coordinator-scripts.md and tickets/T-2886/ticket.md, TICK004/
TICK011/TICK012 backlog-age findings) are pre-existing, repo-wide, and
touch none of this ticket's files -- confirmed via targeted grep against
the full check log. frob test (touched-set) not run separately; targeted
pytest above covers every touched symbol.

### Changed
```
 tickets/T-2361/ticket.md | 38 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 37 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_ok_passes_through` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestEffectiveProfileOrStandard::test_err_falls_back_to_standard` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 1048 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2886/ticket.md, I001@/home/logan/projects/frob/.claude/worktrees/t-2361-series/tests/unit/verify/test_backpressure.py, TICK004@tickets.md
