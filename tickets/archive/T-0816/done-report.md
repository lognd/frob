## Done report

Root cause: `_CLEAN_MODEL` in tests/unit/test_app_runners_batch7.py declared a
flow (`evil -> api`) with no `timeout` attr and no `async`/`local` exemption.
`frob sys audit` fails it under REL200 (T-0640's reliability-timeout-
obligation rule, module docstring in src/frob/strata/_reliability.py):
"every flow with no `timeout` attr declared and no exemption" is a
deny-by-default gap. `sys_run`'s composite check
(`combined_reliability.violations`) folds this into the same exit path as
the health leg, which is why the test's failure looked like a
reliability/health/matrix composite exit rather than naming REL200
directly -- captured log confirms it explicitly: "sys audit: 1 reliability
gap(s) found ... GAP family=sys rule=REL200 node=evil detail=flow f1
(evil -> api) has no timeout obligation (no `timeout` attr, no
`async`/`local` exemption)".

Responsible land: T-0640 (REL200/REL201, the reliability-timeout family),
not one of the four candidates the ticket named (T-0606/T-0644/T-0717/
T-0769) -- T-0644 landed alongside it in the same T-0331 epic (REL210/
REL211 node-health pair) but the actual firing rule here is REL200, which
predates T-0644. The fixture was simply never updated when T-0640 added
this obligation to every flow.

Fix choice: fixture fix, not a check fix. Added `attr timeout;` to the one
flow in `_CLEAN_MODEL`. This is genuinely clean under current rules, not a
weakening: neither `evil` nor `api` declares a `code=` glob, so
`_unproven_timeout_violations` (REL201) treats the flow as UNCHECKABLE
(neither endpoint has bound code) and skips it silently by design --
module docstring's documented "honestly silent rather than a guessed-at
proof" ceiling, the same one `_selfconform.py`'s `managed` exemption and
SYS203's `store_ids` already use. Verified this discharges REL200 without
tripping REL201: full pytest run on the touched file is green.

Out-of-scope finding: `uv run --frozen frob check --ticket T-0816` (a
scoped, not full, run) shows 4 gate:WAIVE WAIVE006 errors at
design/frob.strata:307,370,418,469 -- each `waive "LINT004"` there is
bound to ticket T-0803, which is now closed, and WAIVE006 treats a
closed-ticket binding as stale. This file is outside this ticket's scope
(tests/unit/test_app_runners_batch7.py only) and pre-exists this change
(confirmed by inspecting design/frob.strata directly -- no lines from this
ticket touch it). Filed T-0819 for it. The other gate:WAIVE
WAIVE004 warnings in the scoped run are the documented "known-flaky for
diff-scoped ... trust this only from a full run" noise, not new findings.

A full-repo `uv run --frozen frob test` (touched-set base=main run) surfaced
a large number of failures entirely outside this ticket's scope (test_doctor,
test_export_golden, test_cli_check, test_frob_self_model, TestWaive006RealRepo,
etc. -- unrelated modules, pre-existing on main, not touched by this change).
These are not attributable to the one-line fixture edit in
tests/unit/test_app_runners_batch7.py and are left untouched, consistent with
"touch only files/symbols matching the ticket's scope globs."

## Done report

Changed: tests/unit/test_app_runners_batch7.py::_CLEAN_MODEL (module-level
fixture constant -- added `attr timeout;` to flow f1)

Evidence: tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes
(also verified full-file green: `uv run --frozen pytest
tests/unit/test_app_runners_batch7.py -q` -> 96 passed)

Filed: T-0819 (gate:WAIVE006 design/frob.strata waivers reference
closed ticket T-0803 -- out-of-scope pre-existing finding)

Gates: `uv run --frozen frob check --ticket T-0816` -- clean except two
pre-existing, out-of-scope findings noted above (WAIVE006 on
design/frob.strata, filed as T-0819; WAIVE004 diff-scoped noise
per its own documented caveat). No new gate violations introduced by this
change.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestSysAudit::test_clean_model_passes` (pytest node id, verified passing when recorded)
