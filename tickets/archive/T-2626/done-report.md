## Done report

Fixed the write-time scope validation gap in src/frob/tickets/_models.py
and src/frob/tickets/_scope.py.

Root cause: `frob ticket new --scope` and `frob ticket scope --add`
both accepted a syntactically malformed glob entry (e.g. a semicolon-
joined string like 'src/frob/verify/**;src/frob/app/ticket_runner/**')
without any syntax check, storing it verbatim in the ledger.
`_split_scope_entries` (T-0241) only splits on commas, so a semicolon
(or any other glob-illegal join character) passed straight through.
The stored entry then matched NOTHING via `fnmatch.fnmatch` (what
`scope_matches` actually uses for day-to-day matching) -- silently
voiding the ticket's write lease and evidence coverage -- and crashed
the first `Path.glob` caller instead with
`ValueError: '**' can only be an entire path component`. Verified this
is precisely T-2450's real incident: reproduced the identical crash via
`Path("/nonexistent").glob(the_semicolon_string)`.

Fix: `_first_invalid_scope_glob` (new, src/frob/tickets/_models.py)
probes each entry through `Path.glob` (the SAME matcher whose exception
T-2450 hit) against a guaranteed-nonexistent probe root -- pattern
syntax validation happens before any real directory scan, so this never
touches the filesystem and costs nothing measurable. Catches both
ValueError (the semicolon shape, and other invalid pattern shapes) and
NotImplementedError (an absolute pattern, also never legitimate scope).

Wired into TWO write-time paths only, deliberately not the load path:
- `TicketSpec.scope`'s field validator (src/frob/tickets/_models.py):
  `frob ticket new --scope`'s construction path. Raises ValueError
  naming the bad entry -- safe to be strict here because TicketSpec is
  write-only, never the ledger LOAD path.
- `mutate_scope`'s `_validate_scope_request` (src/frob/tickets/
  _scope.py): `frob ticket scope --add`'s validation, before the ledger
  lock is even taken. Returns the new `TicketError.ScopeGlobInvalid`,
  logged with the offending entry named.
- `Ticket.scope`'s own field validator (the ledger LOAD path) is
  DELIBERATELY left unchanged -- this mirrors the T-1132 blocked_by/
  parent precedent already established in this exact file (see the
  comment directly above Ticket's own validator): validating there
  would hard-fail loading the ENTIRE shared ledger the moment a single
  historical malformed scope entry exists anywhere in it (T-2450's own
  ticket still has one on disk today). A `--remove` glob is likewise
  not validated -- a ticket cleaning up an already-malformed legacy
  entry must still be able to remove it.

Positive controls verified by test (tests/test_tickets.py, class
TestScopeGlobValidation):
- test_semicolon_joined_entry_is_invalid / test_absolute_pattern_is_
  invalid: the two concrete malformed shapes are refused.
- test_every_existing_valid_form_still_passes /
  test_mutate_scope_still_accepts_every_valid_form: the positive
  control that matters most -- every scope form this repo's existing
  tickets actually use (bare literal, trailing-slash directory,
  bare-directory-no-slash, single/double-star globs, bracket classes,
  the comma-joined T-0241 form) still writes successfully. A validator
  that rejected any of these would block the whole fleet's normal
  `scope --add`/`new --scope` usage.
- test_new_ticket_refuses_a_semicolon_joined_scope /
  test_mutate_scope_refuses_a_semicolon_joined_add: both write paths
  (new and scope --add) refuse the T-2450 repro shape.
- test_ticket_itself_still_loads_a_legacy_malformed_scope: `Ticket`
  construction (the load path) does NOT raise on an already-malformed
  entry -- confirms the T-1132-precedent leniency is preserved.

Did not touch `frob ticket new`'s own CLI wiring
(src/frob/app/ticket_runner/_new.py) or `demote_to_evidence_only` --
both out of this ticket's declared scope
(src/frob/tickets/_scope.py, src/frob/tickets/_models.py only) and
neither needed a change: `_new.py` already constructs a `TicketSpec`
first, so it inherits the new validation automatically without any
edit of its own file, and `demote_to_evidence_only` only ever moves an
entry ALREADY in `ticket.scope` (never accepts new scope text), so
there is nothing new to validate there.

Did not attempt to repair T-2450's own still-malformed on-disk scope
entry -- out of this ticket's scope and explicitly not this ticket's
job (a silent repair could widen a lease, and the malformed entry's
intent is not inferable). Confirmed T-2450's ticket still carries the
same semicolon-joined scope on main as of this write-up; leaving its
cleanup to whoever owns that ticket now that new writes of this shape
are refused going forward.

Evidence bound and repro-verified: `frob ticket evidence T-2626
--designate-repro` against commit 127704bb1 (the repro tests committed
alone, before the fix) reports FAILED_AT_PARENT for
test_mutate_scope_refuses_a_semicolon_joined_add -- confirmed 5 of the
7 new tests fail against the unfixed code (the other 2,
test_every_existing_valid_form_still_passes and
test_ticket_itself_still_loads_a_legacy_malformed_scope, are positive
controls and pass at both parent and fix by design).

Full regression run: tests/test_tickets.py, tests/test_tickets_scope_
mutation.py, tests/unit/test_t2450_scope_repair.py, tests/unit/
test_new_ticket_scope_overlap_warning.py -- 231 collected, 0 failed.

### Changed
```
 src/frob/tickets/_models.py   |  86 ++++++++++++++++++++++++++++--
 src/frob/tickets/_scope.py    |  32 ++++++++++--
 tests/test_tickets.py         | 117 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2626/done-report.md | 118 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2626/ticket.md      |  30 +++++++++--
 5 files changed, 374 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestScopeGlobValidation::test_semicolon_joined_entry_is_invalid` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_absolute_pattern_is_invalid` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_every_existing_valid_form_still_passes` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_new_ticket_refuses_a_semicolon_joined_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_ticket_itself_still_loads_a_legacy_malformed_scope` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_mutate_scope_refuses_a_semicolon_joined_add` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestScopeGlobValidation::test_mutate_scope_still_accepts_every_valid_form` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DUP001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/t2615-t2626/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
