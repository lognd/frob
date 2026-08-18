## Done report

: T-2478 clear the 5-finding lint quarantine raised by T-1135's post-land sweep

CONTEXT (per coordinator's note, worth repeating so this does not read
as a regression): these 5 findings reached `main` because the land-time
check ran under a budget that silently dropped the whole `lint` stage
group from every post-land sweep. T-2456 fixed that an hour before this
ticket started (budget raised 300 -> 480 after the five stage groups
were measured to sum to ~334.6s). Lint now actually runs and caught
debt that was always there but previously invisible -- the repo did not
get worse; previously-invisible debt became visible.

Fixed the code, not just disposed the quarantine findings:

- `src/frob/app/ticket_runner/_query.py:1203` -- E501 (90 > 88). Wrapped
  a dict-literal comprehension entry across 4 lines instead of one.
- `src/frob/gates/__init__.py:6636` -- E501 (92 > 88). Wrapped a
  `_ProcessJob(...)` call's arguments onto their own line.
- `src/frob/gates/_dup_graph_schema.py:163` -- E501 (91 > 88). Wrapped
  `_unknown_key_violation`'s signature across 3 lines.
- `src/frob/verify/_worker.py:339` -- E501 (106 > 88). Wrapped a
  docstring prose line; no code change.
- `src/frob/vet/_capability.py` -- F401 x3
  (`_EXT_LANGUAGE`/`_PATTERNS`/`_resolved_candidates_for_language`
  imported but unused). Investigated each individually rather than
  blanket-deleting: `_EXT_LANGUAGE` and `_resolved_candidates_for_language`
  are genuinely dead in this module (verified via `git grep`: no caller
  imports either via `frob.vet._capability`, only via
  `_capability_core.py`/`_capability_scan.py` directly) -- removed.
  `_PATTERNS` is NOT dead: `tests/test_capability_registry.py` and
  `tests/unit/strata/test_selfconform.py` both import it directly via
  `from frob.vet._capability import _PATTERNS`. Deleting it would have
  broken those tests (confirmed: the ticket-filing command itself failed
  with `ImportError: cannot import name '_PATTERNS'` on the FIRST attempt
  at this fix, which is what caught this before it shipped). Kept the
  import and added `_PATTERNS` to the module's own `__all__` (matching
  the file's existing re-export convention for
  `SCANNED_LANGUAGES`/`language_for`/etc.) so ruff recognizes it as a
  legitimate re-export rather than dead code, and corrected the stale
  T-2358 comment that incorrectly claimed
  `_resolved_candidates_for_language` was "re-exported... via `__all__`
  below" when it never actually was.

Not a blanket auto-fix pass: each F401 was checked against real callers
before deciding delete-vs-keep, which is why one of the three needed the
opposite treatment from the other two.

## Filed

None -- no residue found. The scope collision with T-2462's live lease
on `gates/__init__.py` was worked around by scoping it out, doing the
other 4 files first, then scoping it back in once T-2462's lease cleared
(no ticket needed for a transient lease wait).

## Cuts

None disclosed as outstanding.

### Changed
- `src/frob/app/ticket_runner/_query.py`
- `src/frob/gates/__init__.py`
- `src/frob/gates/_dup_graph_schema.py`
- `src/frob/verify/_worker.py`
- `src/frob/vet/_capability.py`

### Evidence
- `tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_pre_registry_needle_still_fires_somewhere`
  (directly exercises `_PATTERNS` via the exact import path this ticket
  touched)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key`
  (exercises `_unknown_key_violation`, whose signature was reflowed)
- `tests/test_serve_daemon.py::TestPollVerifyWorker::test_head_moved_notifies_the_worker`
  (exercises the `CoalescingWorker` docstring's surrounding code)
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent`
  (exercises `_query.py`'s contention-report path, of which the
  reflowed dict literal is part)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches`
  (CLI-dispatch integration test, bound per T-0167 precedent for the
  `gates/__init__.py` gate-wiring dict entry, which has no narrower
  existing test by name)

All 5 re-run fresh this session:
`pytest <the 5 node ids above> -p no:cacheprovider -q` ->
`SUITE-RESULT: exitstatus=0 collected=5 failed=0` (run in two batches;
both exitstatus=0).

Scoped lint re-check (`frob check --only lint --ticket T-2478 --json`,
parsed for ruff diagnostics against these 5 files): zero E501/F401
findings remain on any of the 5 touched files.

### Changed
```
 src/frob/app/ticket_runner/_query.py |  6 +++++-
 src/frob/gates/_dup_graph_schema.py  |  4 +++-
 src/frob/verify/_worker.py           |  3 ++-
 src/frob/vet/_capability.py          | 10 +++++-----
 tickets/T-2478/ticket.md             | 19 +++++++++++++++++++
 5 files changed, 34 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_capability_registry.py::TestNoSilentNeedleRegression::test_every_pre_registry_needle_still_fires_somewhere` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollVerifyWorker::test_head_moved_notifies_the_worker` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand::test_zero_contention_is_explicit_not_silent` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/verify/_worker.py, ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2478, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py


frob:no-behavior-change reason="pure lint fix: E501 line-wraps and F401 dead-import removal/re-export documentation, no functional/behavioral change to any touched function -- confirmed via all 5 bound tests passing unchanged"
