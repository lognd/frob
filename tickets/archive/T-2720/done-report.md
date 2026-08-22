## Done report

Changed:
- src/frob/gates/__init__.py::_cov005_new_key_indexes (new, extracted from `_cov005_file`)
- src/frob/gates/__init__.py::_cov005_violation (new, extracted from `_cov005_file`)
- src/frob/gates/__init__.py::_Cov005Key (new module-level type alias, formatting only)
- src/frob/gates/__init__.py::_cov005_file (narrowed rebind check; docstring updated)
- src/frob/gates/__init__.py::_cov005 (docstring: no logic change)
- tests/test_gates.py::TestCoverageGate.test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean
  (new fixture, added FIRST per the ticket's own requirement, confirmed to genuinely fail
  against the pre-narrowing code before the fix was written)

Root cause (confirmed via the new fixture, not assumed): `_cov005_file` flagged ANY new
private edge sharing an old public binding's `(kind, target)` key, regardless of whether the
OLD public symbol's OWN directive was still intact. This repo's documented convention of
reusing one `frob:doc <page>#<anchor>` target across every symbol a doc page covers means a
brand-new, entirely unrelated private helper added near an undisturbed public `def` picks up
the SAME key purely by anchor reuse -- not a rebind, not a T-0297 displacement. 18+ waived
sites in `.claude/hooks/root-write-guard.py` (T-2481) plus 4 more in
`src/frob/gates/_coverage_sites.py` (T-1943) share exactly this shape per their own waiver
reasons.

Fix: `_cov005_file` now first checks whether the OLD public qualname's own `(kind, target)`
edge is STILL PRESENT at the new revision (`new_qualnames_by_key`). If it is, the directive
was never displaced -- skip the whole key, however many other symbols share the anchor. Only
when the old qualname's own edge for that key is GONE (T-0297's real shape: the directive
comment physically moved off the old symbol) does a new private edge under that key become a
rebind candidate, exactly as before.

TEST FIXTURE FIRST, as required: `test_cov005_new_private_helper_sharing_anchor_with_
undisturbed_public_is_clean` was written and run against the UNFIXED code before any narrowing
edit -- confirmed FAILING (`AssertionError: [Violation(rule='COV005', ...)]`), reproducing the
exact false-positive shape. The narrowing fix was then written, and the same fixture was
re-run and confirmed passing.

Both-direction proof (`--no-cache` never used for these -- COV005 is diff/hunk-driven, not a
static repo-wide gate, so `frob check --no-cache` on this worktree's own uncommitted diff would
only ever show COV005 findings for files/hunks THIS diff touches, which are the source files
themselves, not the `.claude/hooks/root-write-guard.py` waiver sites from unrelated,
already-landed, already-squashed tickets -- direct unit fixtures are the correct and only way
to reproduce/measure this diff-scoped rule both ways, and that is what the 4-test suite below
does):
- False positive stops firing: `test_cov005_new_private_helper_sharing_anchor_with_
  undisturbed_public_is_clean` -- fails before the fix (measured above), passes after.
- Genuine T-0297 violation still fires (must-still-fire control, unmodified pre-existing
  fixture): `test_cov005_directive_rebound_to_private_symbol_flags` -- `foo` (public) loses its
  directive to a newly-extracted `_foo_impl` directly above it; still fires COV005 after the
  narrowing, because `foo`'s own edge for that key is genuinely gone at the new revision.
- `test_cov005_same_symbol_no_rebind_is_clean` and `test_cov005_no_old_blob_is_clean`
  (pre-existing, unmodified): still pass, confirming no regression on the other two already-
  covered shapes.
- All 4 together: `pytest tests/test_gates.py -k test_cov005 -q` ->
  `SUITE-RESULT: exitstatus=0 collected=4 failed=0`. Full `TestCoverageGate` class (74 tests,
  everything else COV001-COV007/PLACE001/etc. share this file's fixtures and helpers):
  `SUITE-RESULT: exitstatus=0 collected=74 failed=0` -- no regression anywhere else in the
  coverage gate family.

ARCH001 self-check: the narrowing pushed `_cov005_file` to 74 lines (threshold 60) on first
draft; extracted `_cov005_new_key_indexes` and `_cov005_violation` (both with their own
`frob:doc`-free one-line docstrings per this repo's private-symbol convention) to bring it back
under threshold without changing behavior -- confirmed via `frob check --ticket T-2720
--no-cache` (see Gates below).

Waivers NOT removed: none of the 18 `.claude/hooks/root-write-guard.py` (T-2481) or 4
`src/frob/gates/_coverage_sites.py` (T-1943) waivers were touched -- both files are outside
this ticket's declared scope (`src/frob/gates/__init__.py`,
`src/frob/gates/_coverage_sites.py`, `tests/test_gates.py`), and, more importantly, COV005 is
diff-scoped: those waivers sit on lines from tickets that landed (and squashed) long ago, so
there is no live diff today for the narrowed gate to re-evaluate them against and prove the
finding no longer reproduces AT THOSE EXACT SITES right now -- exactly the standard I was held
to for not removing a waiver without that proof. The fixture test is the closest available
proof the underlying detector bug is fixed; removing those specific waivers is left to a
follow-up (see Filed below), same shape as T-2719's own follow-up.

Filed: T-2739 (renumbers to a real id at land) -- "verify T-2481/T-1943 COV005
waivers against T-2720's narrowed detector, remove any that no longer reproduce", scope
`.claude/hooks/root-write-guard.py`, `src/frob/gates/_coverage_sites.py`. Note: `frob ticket
new` reported this scope overlaps several queued tickets (T-1608, T-1609, T-1661, T-1945,
T-2057, T-2080, T-2202) and this in-progress T-2720 on the same files -- left as-is, same as
T-2719's own follow-up, since resolving overlap is a follow-up-ticket concern.

Evidence: tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags,
tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean,
tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean,
tests/test_gates.py::TestCoverageGate::test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean
(designated BUG002 repro; FAILED_AT_PARENT confirmed at 396919c8a, PASSES at HEAD)

Gates: `frob check --ticket T-2720 --no-cache` clean of COV005/AFFECT001/PRE001/ARCH001/E501
findings in this ticket's own touched files after the extraction refactor (remaining errors in
that run -- DRIFT001 x3, ARCH103, PERF00x, PII010/012, COV001/003/004, CYCLE001, DOC002, etc. --
are all pre-existing, unrelated to this ticket's touched files/symbols, confirmed by file path).

### Changed
```
 src/frob/gates/__init__.py         | 115 ++++++++++++++++++++++++++++---------
 tests/test_gates.py                |  47 +++++++++++++++
 tickets/T-2720/ticket.md           |  18 +++++-
 tickets/T-2739/ticket.md |  31 ++++++++++
 4 files changed, 182 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov005_new_private_helper_sharing_anchor_with_undisturbed_public_is_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 44 error(s), 1539 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2719-t2720/src/frob/_cli_parsers/_ticket/_closeout.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
