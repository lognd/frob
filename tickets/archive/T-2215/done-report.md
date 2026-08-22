## Done report

Wired `must_still_pass_violations` (BUG003, T-2193) into the same two
call sites BUG002/TEST016 already use: `frob.tickets._land`'s land-time
precheck (`_mutation_evidence_deferred`/`_mutation_evidence_synchronous`,
via the new `_must_still_pass_land_violations`) and
`frob.app.ticket_runner._close_cmd`'s direct `frob ticket close` path
(`_close_mutation_evidence_for_ticket`). Same ERROR-always severity
posture as BUG002, same escape-hatch shape: `frob:waive BUG003
reason="..."` in ticket body (`_must_still_pass_waiver_reason`, new
`_BUG003_WAIVER_RE` in `_land.py`) mirrors `_BUG002_WAIVER_RE` exactly.
BUG003 is not kind-restricted (per T-2193's own docstring), so it runs
for every ticket regardless of kind -- but is a no-op unless the ticket
body declares a `frob:must-still-pass NODE-ID` directive, which is the
opt-in this ticket's brief required staying explicit.

Real defect found and fixed along the way: `must_still_pass_violations`
was never re-exported from `frob.gates`'s package `__init__` (an
omission in T-2193's own land -- `bug_repro_violations`/
`mutation_evidence_violations` both are re-exported, this one wasn't).
`from frob.gates import must_still_pass_violations` raised ImportError.
Fixed by importing directly from the owning submodule
(`frob.gates._mutation_evidence.must_still_pass_violations`) rather than
widening this ticket's scope into `frob/gates/__init__.py` -- filed
T-2228 (later renumbered/superseded by the coordinator's own filing of
the SAME id for the waiver-regex/prose-quoting defect below; see
"Filed" section) is NOT the ticket for the __init__ gap specifically --
see note below, the __init__ re-export gap itself has NOT been separately
ticketed and should be before it bites another caller (disclosed here
per playbook 8, not silently worked around).

**Waiver-regex false-positive risk (found mid-ticket, escalated to the
coordinator, who filed T-2228 to fix it -- correctly outside this
ticket's declared scope, since the fix lives in
`_mutation_evidence.py`).** `_BUG003_WAIVER_RE`/`_bug002_waiver_reason`
both do a raw regex scan of `ticket.body` with no way to distinguish a
genuine directive from a directive-syntax example quoted in prose. This
ticket's OWN body (`tickets/T-2215/ticket.md`) contains such a quoted
example (`` `frob:waive BUG003 reason="..."` ``) and the regex matches
it, capturing `...` as a reason. This is NOT a live risk for landing
T-2215 itself: `must_still_pass_violations` only runs the check (and
thus only calls the waiver-reason lookup) when `_must_still_pass_
controls(ticket)` finds a `frob:must-still-pass NODE-ID` directive in
the body first -- T-2215's own body has no such directive, so
`_must_still_pass_land_violations` short-circuits to `()` before ever
reaching the waiver-reason scan, regardless of the quoted example
elsewhere in the body. Verified directly: `_must_still_pass_controls`
against this ticket's real body returns `()`.

Dogfooded per the brief's explicit requirement: a ticket with no
`frob:must-still-pass` directive lands unaffected, and empirically --
T-2215's own body has none, verified directly (`_must_still_pass_
controls` against this ticket's real body returns `()`); a ticket whose
declared control passes at both fix and parent lands unaffected. Both
proven in one parametrized test,
`test_land_succeeds_when_gate_reports_clean[no_directive]` /
`[control_passes_both]` (merged from two originally near-identical test
bodies after `frob check` caught DUP002 on them -- see Gate findings
fixed below). Proven at the wiring-function level (monkeypatching the
one real external boundary, `must_still_pass_violations` itself, which
spawns pytest subprocesses) -- the same "stub the process seam, exercise
the real wiring" shape `test_ticket_close_bug002_t1427.py` already uses
for BUG002.

Acceptance criterion 0 (a test that FAILS against current main):
`test_land_refuses_when_control_broke_at_fix` -- `_must_still_pass_land_
violations` does not exist on main at all (every test in the new file
fails to import at collection there), so the ImportError itself is the
"currently cannot produce this refusal" proof; the test's body then
positively demonstrates the refusal shape once the wiring exists.

Changed:
- `src/frob/tickets/_land.py`: `_BUG003_WAIVER_RE`,
  `_must_still_pass_waiver_reason`, `_must_still_pass_land_violations`
  (new); `_mutation_evidence_deferred`/`_mutation_evidence_synchronous`
  now include BUG003 in their combined violations tuple;
  `_check_mutation_evidence`'s docstring updated; `TYPE_CHECKING` import
  of `Violation` added for the new function's type hint.
- `src/frob/app/ticket_runner/_close_cmd.py`:
  `_close_mutation_evidence_for_ticket` now also runs
  `_must_still_pass_land_violations`; docstring updated.
- `src/frob/gates/_waive.py`: no change needed -- T-2193 already
  registered `"BUG003"` in `_KNOWN_GATE_RULES` (verified present at
  `src/frob/gates/_waive.py:277` before starting; confirmed by reading
  the file, not assumed from the done report).
- `tests/unit/test_ticket_land_bug003_t2215.py` (new): 7 tests (2
  parametrize cases under one test method) -- `TestMustStillPassWaiver`
  (3: reason present / bare directive / no directive) and
  `TestMustStillPassWiring` (4: parametrized no-directive/passes-both,
  broke-at-fix, waived).

Verification (all commands run from the T-2215 worktree,
`.claude/worktrees/t-2215`):
- `uv run pytest tests/unit/test_ticket_land_bug003_t2215.py -o addopts="" -q`
  -> `SUITE-RESULT: exitstatus=0 collected=10 failed=0` (10 passed, after
  adding `TestMustStillPassCombinesWithBug002`'s 3 tests per the
  close-time TEST016/TEST018 finding above).
- `uv run pytest tests/unit/test_ticket_close_bug002_t1427.py -o addopts="" -q`
  -> `SUITE-RESULT: exitstatus=0 collected=2 failed=0` (2 passed, no
  regression from the `_close_cmd.py` change).
- `uv run pytest tests/test_ticket_land.py -o addopts="" -q -k "mutation or bug002 or Bug002"`
  -> `SUITE-RESULT: exitstatus=0 collected=27 failed=0` (27 passed).
- `uv run pytest tests/test_ticket_land.py -o addopts="" -q` (full file,
  the one containing the code paths I touched) -> `4 failed, 273 passed
  in 202.94s`; the 4 failures are exactly the playbook's documented
  pre-existing set (`test_refuses_on_dirty_main`,
  `test_same_ticket_conflict_surfaces_loudly_no_splice`,
  `test_dirty_lock_with_other_change_still_refuses`,
  `test_dirty_lock_version_plus_other_line_still_refuses`) -- confirmed
  by name match against playbook section "VERIFICATION" text, not
  assumed.
- `uv run frob check --only lint --ticket T-2215 --json`: initially
  caught a real `I001` (unsorted import block) in my own
  `_land.py` edit, from a `TYPE_CHECKING` import ordering mistake; fixed
  and re-ran clean for every file this ticket touches (`_land.py`,
  `_close_cmd.py`, the new test file all absent from the diagnostics
  list on the second run).
- `uv run frob check --ticket T-2215 --json` (full, not `--only`
  narrowed): first run found 3 REAL findings on my own new test file
  (not pre-existing repo debt -- confirmed by file/symbol match): 2x
  COV002 (new test symbols with no `frob:ticket` edge -- fixed by adding
  `# frob:ticket T-2215` above every new class/function, matching
  `tests/test_gates_mutation_evidence.py`'s own per-symbol convention),
  1x SCOPE001 (the new test file itself was outside T-2215's declared
  `scope` -- fixed via `frob ticket scope T-2215 --add
  tests/unit/test_ticket_land_bug003_t2215.py --reason "..."`), 1x
  DUP002 (`test_land_succeeds_when_no_directive` and
  `test_land_succeeds_when_control_passes_both` were 100% structurally
  identical -- fixed by merging into one `@pytest.mark.parametrize`d
  test rather than waiving, since they genuinely were the same test with
  different fixture data), 1x WIRE001 (`_sample_violation` is a new
  test-fixture helper with no caller outside its own file's tests --
  fixed with `frob:waive WIRE001 ... permanent="true"`, the documented
  `_wire002_is_permanent_test_helper_waiver` exemption for a private
  (`_`-prefixed) symbol under `tests/`). A stale gate-result cache
  (`FROB_NO_GATE_CACHE=1`, playbook section 6) initially made the WIRE001
  waiver look unrecognized after being added -- re-ran cache-bypassed and
  confirmed clean. Final `FROB_NO_GATE_CACHE=1 frob check --ticket
  T-2215 --json`, grepped for every error-severity finding: zero touch
  `_land.py`, `_close_cmd.py`, `_waive.py`, or the new test file. Every
  OTHER family's repo-wide FAIL count (`gate:COV`/`DOC`/`DRIFT`/`PRE`/
  `SCOPE`/`TEST`/`TICK`/`ARCH`/`PERF`/`SELFAUDIT`/`WIRE`) is pre-existing
  debt confirmed by grep to touch none of my files; per playbook 6c this
  is NOT a package-clean claim for the whole repo, only for my own
  touched set.
- `uv run frob check --land-parity`: did NOT complete -- deferred 2
  stage groups (lint, static) inside its own internal `--budget 300`
  call and returned "could not evaluate", not a real pass or fail.
  Disclosing this rather than treating a deferred/unmeasured result as
  clean (playbook 8): re-run by a coordinator with more budget before
  trusting this specific check, though the scoped `--only lint
  --ticket T-2215` and `--only gates-fast --ticket T-2215` runs above
  already cover the same "does this diff introduce anything" question
  for the families that actually loaded.

`frob ticket close T-2215`'s own mutation-evidence sweep (TEST016/
TEST018) caught something the unit tests above did not: my first close
attempt was refused (`EvidenceConfirmatoryOnly`) because the bound
evidence, while it genuinely exercised `_must_still_pass_land_
violations` in isolation, never exercised the actual `bug002_violations
+ bug003_violations`-style concatenation LINES this ticket added inside
`_mutation_evidence_deferred`/`_mutation_evidence_synchronous`/
`_close_mutation_evidence_for_ticket` themselves -- 0/2 and 0/3 mutants
killed on those exact lines, both "binop Add swapped". Added a fourth
test class, `TestMustStillPassCombinesWithBug002` (3 more tests), that
calls those three real functions directly with BUG002/TEST016 stubbed
clean and ONLY `must_still_pass_violations` (BUG003) returning a
finding -- a passing assertion is only possible if the wiring genuinely
ADDS BUG003's contribution rather than silently dropping it. Re-ran
close after adding these; TEST016/TEST018 both clean on the second
attempt (see Verification below). This is exactly the mutation-evidence
mechanism working as designed -- disclosed here rather than treated as
routine, since it caught a real evidence-strength gap the earlier unit
tests alone would have let through a close.

Filed: T-2228 (by the coordinator, not me -- the waiver-regex/
directive-in-prose false-positive risk described above; scope
`src/frob/gates/_mutation_evidence.py`, outside T-2215's own declared
scope). The `frob.gates.__init__` missing re-export for
`must_still_pass_violations` (worked around above by importing from the
private submodule directly) has NOT been separately ticketed -- also
outside T-2215's declared scope (`frob/gates/__init__.py` is not in
`scope`), disclosed here rather than silently left unfiled.

Gates: `frob check --only lint --ticket T-2215` clean for every file
this ticket touches (measured, see above). `frob check --only gates-fast
--ticket T-2215` repo-wide FAIL but zero findings on any file this
ticket touched (measured by grep against the full output, see above).
`frob check --land-parity` unmeasured (deferred, see above) -- disclosed
as an open gap, not waived silently.

### Changed
```
 tickets/T-2215/done-report.md | 187 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2215/ticket.md      |  35 +++++++-
 2 files changed, 220 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_refuses_when_control_broke_at_fix` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_gate_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_waived_finding_is_suppressed_but_logged` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver::test_reason_present_suppresses` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver::test_bare_directive_without_reason_does_not_suppress` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_land_deferred_refuses_on_bug003_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_land_synchronous_refuses_on_bug003_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002::test_close_refuses_on_bug003_alone` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2215/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2215, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, TICK006@tickets.md
