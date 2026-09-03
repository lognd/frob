## Done report

Changed:
- src/frob/app/check_runner.py::_apply_tier_a_and_reverify -- threads ticket_id=cfg.check_ticket into apply_tier_a_fixes; refuses (exit 1) an unscoped --fix unless --fix-all is also given; post-filters Tier-B's committed_b through the same filter_fixes_by_scope_and_lease Tier-A already uses.
- src/frob/_cli_parsers/_check.py -- new --fix-all flag.
- src/frob/app/config.py::AppConfig.check_fix_all -- new field, default False.
- docs/commands/check.md -- new "Tier-A/B/C deterministic autofix (--fix)" section.
- tests/test_check_runner.py -- three new fixtures plus check_fix_all=True added to five pre-existing repo-wide-fix tests (their own intent, now requires the explicit opt-in).

DECISIONS (per the ticket's own "decide, do not guess" instruction):

(a) --fix now honours --ticket's scope -- the narrow, obviously-correct
half. Implemented by threading ticket_id=cfg.check_ticket into
apply_tier_a_fixes, reusing the EXACT scoping mechanism (frob.gates.
_fix_engine_scope.filter_fixes_by_scope_and_lease) frob ticket land's own
pre-land Tier-A pass has trusted since T-2284 -- no new scoping logic, no
duplication. Tier-B (apply_tier_b_fixes) has NO ticket-scoping of its own
and land never calls it at all, so I post-filtered its committed_b list
through the SAME function (it returns the identical FixApplied shape,
T-1137's own "committed Tier-B is reported identically to Tier A" contract)
rather than leaving a second, unscoped door open right next to the one I
just closed.

(b) The unscoped case: I chose "refuse without an explicit opt-in flag
(--fix-all)" over "proceed but print the file list first". Reasoning: a
true preview-before-write would need apply_tier_a_fixes restructured into
a two-phase dry-run/apply split, a materially bigger change than this
ticket's declared scope covers; a refuse-by-default is a smaller, safer
change that directly closes the incident's own gap (the killed run was a
BARE --fix, no --ticket at all -- "respecting --ticket when given"
alone would not have prevented it). --fix --fix-all still runs the full
repo-wide pass, byte-identical to pre-T-3326 behavior -- Tier-A is not
crippled, only no longer the silent default of a targeted-feeling
invocation.

(c) Partial-application recoverability: NOT newly built -- already existed.
apply_tier_a_fixes (T-1348) writes an autofix manifest under .frob/
after EVERY handler completes and clears it only once the whole loop
finishes; a killed run already leaves a readable on-disk record of every
path a completed handler touched (tests: tests/test_gates.py::
TestAutofixManifest, pre-existing, unmodified by this ticket). I verified
this mechanism is real and reachable from the CLI path (not test-only) by
reading apply_tier_a_fixes's own call site and its docstring's T-1348
paragraph, and left it as-is per the ticket's own "may be out of scope --
say which you chose" allowance -- a resumable journal (actually replaying
partial progress, not just reporting it) would be new work; reporting what
was already touched was already solved.

SIBLING CASE (report, not fix, per the ticket's own instruction):
frob ticket land's pre-land Tier-A pass (_land_cmd.py, two call sites:
the wip-commit-time absorption and the post-merge-into-worktree pass) was
ALREADY scoped before this ticket -- both already pass ticket_id=cfg.
ticket_id into apply_tier_a_fixes, confirmed empirically while landing
T-3288 moments earlier in this same session (its own land output printed
SKIPPED DOC007 tests/... is outside T-3288's declared scope). So the
pre-land path is NOT a second, worse instance of this hazard -- it was
fixed earlier (T-2284/T-1348), and this ticket's CLI-side fix brings the
bare frob check --fix command up to the same standard the land pipeline
already held.

Evidence: tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope, tests/test_check_runner.py::TestApplyTierAAndReverify::test_unscoped_fix_refuses_without_fix_all, tests/test_check_runner.py::TestApplyTierAAndReverify::test_fix_all_still_runs_repo_wide_when_explicitly_requested, tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported

Filed: none

Gates: full tests/test_check_runner.py (16/16) and
tests/test_gates.py::TestFixEngineScopeLease + TestAutofixManifest
(12/12) pass. frob check --help confirms --fix-all is wired into the
CLI. Designated repro (test_ticket_scoped_fix_never_touches_files_outside_declared_scope)
genuinely fails at the pre-fix commit and passes at the fix, verified via
--check-repro/--designate-repro.

### Changed
```
 docs/commands/check.md          |  42 ++++++++++++++
 src/frob/_cli_parsers/_check.py |  16 ++++++
 src/frob/app/check_runner.py    |  41 ++++++++++++-
 src/frob/app/config.py          |  10 ++++
 tests/test_check_runner.py      | 124 ++++++++++++++++++++++++++++++++++++++--
 tickets/T-3326/ticket.md        |  74 +++++++++++++++++++++++-
 6 files changed, 299 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_unscoped_fix_refuses_without_fix_all` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_fix_all_still_runs_repo_wide_when_explicitly_requested` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineScopeLease::test_out_of_scope_fix_is_reverted_and_reported` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
