## Done report

Changed:
- tests/test_gates.py -- added TestWire001DiffScopingMissesPreExistingDeadSymbols:
  a must-stay-quiet reproduction of the T-2900/T-2905 shape (a
  pre-existing dead symbol untouched by the current diff's own hunks)
  proving WIRE001 correctly stays silent, plus a must-still-fire
  control proving the identical symbol IS flagged the moment it is
  genuinely introduced by the diff being measured.
- tests/unit/gates/test_refs.py -- added
  TestRef002FileGranularityMissesDeadSymbols: a must-stay-quiet
  reproduction (a dead private symbol living inside an otherwise
  well-referenced file) proving REF002 correctly stays silent at file
  granularity, plus a must-still-fire control (REF001 fires when the
  dead symbol IS effectively the whole file) proving REF001/REF002 are
  not broken, only file-scoped by design.
- docs/modules/gates.md -- added a "Structural limitation, confirmed by
  measurement (T-2928)" paragraph to both the WIRE001/WIRE002 section
  and the anti-orphan file-reference gate section, naming the exact
  root cause and cross-referencing DEAD001 as the detector that
  actually owns this shape.

Per-detector root cause (both confirmed by direct reproduction in this
worktree, not inferred from the T-2900/T-2905 done reports alone):

- WIRE001 case 1 (`_wire001_unwired_symbol_violations`) only evaluates
  `_new_callable_records` -- symbols whose ENTIRE span sits inside the
  CURRENT diff's own added-line hunks. `_parse_bash`/`_parse_csharp`
  were added under T-1604/T-1600 (long before T-2900/T-2905); the
  measuring diffs touched only a `frob:waive` comment, never the dead
  symbol's own body lines, so WIRE001 had structurally nothing to
  evaluate. Confirmed with a synthetic fixture: a dead symbol whose
  span is NOT covered by the diff's hunk produces zero WIRE001
  findings; the identical symbol, this time covered by the diff's own
  hunk, produces exactly one WIRE001 ERROR.
- REF001/REF002 (`_ref001_or_002`) count inbound references to a whole
  FILE (`inbound: set[str]` is a set of consumer FILES), never to a
  symbol defined inside it. `_walk_bash.py`/`_walk_csharp.py` both have
  real, independent file-level consumers, so the FILE clears REF002's
  2+ pass bar even though one particular symbol inside it (the dead
  helper) has zero callers anywhere -- REF002 has no finer granularity
  to report a symbol-level miss at. Confirmed with a synthetic
  fixture: a file with a dead private helper plus a real, exported
  symbol two other files import produces zero REF001/REF002 findings
  for that file; the same dead helper, as the WHOLE content of its own
  file with no other symbol giving the file a second consumer, DOES
  fire REF001.

Both are structural scope limitations, not fixable bugs, without
duplicating DEAD001 (`frob.gates._dead_symbols`, unconditional,
symbol-granularity, WARN) at ERROR severity inside WIRE001/REF002 --
that is a distinct feature decision (a new symbol-level ERROR-severity
dead-code gate), not a bug fix, and is explicitly out of this ticket's
scope. No such gate change was made.

Miss set (restated from T-2900/T-2905's own measurement, now backed by
a synthetic reproduction of the exact mechanism rather than only the
one-off live observation): WIRE001 MISS, REF002 MISS, DEAD001 HIT
(unaffected by this ticket, not touched).

Repro note: this is an investigation/documentation ticket -- no
detector code was changed (both misses are structural, by design, and
are not incorrect behavior to fix). There is consequently no code
change that flips a test from failing to passing at any commit, so a
conventional BUG002 fail-at-parent repro does not apply the way it
would to a code fix; `--check-repro` against every new test in this
change correctly reports TEST_ABSENT_AT_PARENT (the test is new, and
the code it exercises is unchanged), not FAILED_AT_PARENT. No repro is
designated for this reason. The regression value here is the SAME
class of proof this playbook otherwise asks for (must-still-fire +
must-stay-quiet against a real, reproduced shape), just without an
accompanying code diff to gate a designation against.

Evidence:
- tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_pre_existing_dead_symbol_untouched_by_this_diff_is_not_flagged
- tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_the_same_dead_symbol_newly_added_by_this_diff_is_flagged
- tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_dead_private_symbol_in_a_well_referenced_file_is_not_flagged
- tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_file_containing_only_the_dead_symbol_still_fires_ref001

Gates: full `tests/test_gates.py -k "TestWireGate or TestWire001..."`
(34 collected) and `tests/unit/gates/test_refs.py tests/test_refs_gate.py`
(35 collected) runs: only one pre-existing, unrelated failure
(TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged,
confirmed failing identically on main before this ticket touched
anything -- an environment-shaped mismatch against
src/frob/app/_config_external.py's real current content, untouched by
this ticket).

Filed: none -- the fixable/not-fixable determination for both
detectors is recorded in this Done report and in docs/modules/gates.md
directly; there is no further action to track as a ticket (extending
WIRE001/REF002 to symbol-level dead-code detection would duplicate
DEAD001 and is a feature proposal, not a defect, so it is documented
as a limitation rather than filed as a "fix later").

### Changed
```
 docs/modules/gates.md         | 45 ++++++++++++++++++++
 tests/test_gates.py           | 99 +++++++++++++++++++++++++++++++++++++++++++
 tests/unit/gates/test_refs.py | 80 ++++++++++++++++++++++++++++++++++
 tickets/T-2928/ticket.md      | 49 ++++++++++++++++++++-
 4 files changed, 272 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_pre_existing_dead_symbol_untouched_by_this_diff_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_the_same_dead_symbol_newly_added_by_this_diff_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_dead_private_symbol_in_a_well_referenced_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_file_containing_only_the_dead_symbol_still_fires_ref001` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 19 error(s), 1555 warning(s), 851 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2928, TICK004@tickets.md, TICK006@tickets.md
