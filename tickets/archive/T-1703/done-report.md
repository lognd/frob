## Done report

Two independent defects, both in the "unmeasured treated as zero" family,
closed together since they share the same parser.

DEFECT 1 (highest-integrity): `_unscoped_error_findings` spawned `frob
check --budget 300` and parsed its RENDERED TEXT. `--budget` runs
whichever stage groups fit the time budget and DEFERS the rest -- a gate
that never ran emits no diagnostic lines, so the old parser could not
tell "ran, found nothing" from "never ran"; a partial run's error set was
structurally indistinguishable from a clean full run. Confirmed
time-dependent, not just incomplete: two `--budget 300` runs on the
identical tree minutes apart select different stage groups, so the old
"error identity set" was never even a function of tree state. Live
incident: a deferred rapid-profile sweep logged `CLEAN, 0 errors` at a
commit a full unscoped `frob check` found 5 real errors in, 2 of them
TICK006 regressions the same land had just introduced.

DEFECT 2: `_GATE_ERROR_LINE_RE` scraped rendered console prose assuming
every diagnostic renders as `[tag] file:line CODE message`. `ty`'s
`file:line:col` (an extra `:col` the regex's `:\d+\s` never matches)
silently dropped every `ty` error from the identity set, independently
of the budget bug.

FIX. `frob check --json` is now consumed structurally instead of parsed
as text, closing both defects at once:

- `_shared_check_spawn_fn` (`_verify.py`, used by done-report capture and
  land re-verification) and `_unscoped_error_findings` (`_land_cmd.py`,
  the post-land/pre-commit/`--land-parity` sweep) both now spawn
  `--json`.
- `_parse_error_findings_from_json` reads `code`/`file` directly off
  each `Diagnostic`'s structured fields -- immune to how any tool
  renders itself, closing Defect 2 by construction, no regex involved.
- `_budget_deferred_stage_groups` inspects the JSON payload's `"budget"`
  `ToolResult` (present iff `--budget` deferred anything, per
  `frob.app._check_chunking._budget_deferred_result`) and returns `None`
  -- unmeasured, never a partial set -- the moment anything was
  deferred, closing Defect 1.
- `_check_gates_summary_fn`'s count-only path gets the same treatment:
  it now also returns `None` on a deferred run, and reads its
  `(errors, warnings, waived)` counts from the `"gate-summary"`
  `ToolResult`'s own structured `summary` field (via a new counts-only
  regex, `_GATE_SUMMARY_COUNTS_ONLY_RE`, scoped to that ONE already-
  located field -- not a scan over the whole stdout blob).
- `_parse_error_findings_from_stdout` stays the single shared entry
  point, JSON-first with the OLD regex as a fallback ONLY for
  `frob.app.ticket_runner._close_cmd`'s T-1399 gate-claim check, which
  still spawns plain-text `frob check --only gates` and is out of this
  ticket's declared scope -- unaffected by this change, still passes its
  own existing tests unmodified.

A separate, real bug surfaced while wiring `--budget --json` together and
was fixed in the same change (extended scope, `src/frob/app/_check_
chunking.py`, `--reason` recorded on the ticket): `_run_budgeted_check`'s
own progress `_log.info` lines ("running N stage group(s)...", "stage
group %r done...") printed unconditionally, ahead of the JSON payload
`_report_check_result` emits -- `run`'s `quiet_stdout_logs` `--json` wrap
only covers the setup calls AFTER `_handle_early_exit_modes` (which
`--budget` dispatches through) runs, so those two lines corrupted every
`--budget --json` caller's stdout in practice, including this ticket's
own new `_unscoped_error_findings` spawn. Guarded both lines behind
`if not cfg.check_json`.

Re-baselined `.frob/rapid-sweep-baseline.json` (root checkout, local
`.frob/` state, not version controlled): deleted the stale
`"findings": []` record so the next post-land sweep establishes a fresh,
correctly-measured baseline instead of diffing against the false-zero
record this ticket describes.

REGRESSION COVERAGE (shape, not count, per the ticket's own instruction):
- `test_budget_truncated_run_yields_none_not_a_partial_set` /
  `test_check_gates_summary_fn_returns_none_on_budget_truncated_run`:
  a JSON payload carrying a `"budget"` tool result (BUDGET001) parses as
  `None` on both the identity-set and count-only paths -- verified to
  fail without the fix (reverted locally, re-ran, restored).
- `test_ty_and_gate_error_both_appear_in_parsed_set`: a `ty` diagnostic
  (`file`/`code` populated structurally, the exact shape the old regex
  could never match) AND an ordinary gate error both appear in one
  parsed set -- verified to fail (returns the whole set as `None`)
  without the fix.
- `test_budget_json_stdout_is_pure_parsable_json`
  (`tests/unit/test_check_budget.py`): `--budget --json`'s full stdout
  round-trips through `json.loads` cleanly, including a deferred-group
  case -- verified to fail (`JSONDecodeError`) without the leaked-stdout
  fix.
- Existing `_check_gates_summary_fn`/`_check_gate_findings_fn` tests
  (`tests/unit/test_ticket_runner_gate_findings.py`) were converted from
  hand-typed rendered-text fixtures to real `--json` `CheckResult`
  payloads (a fixture built from well-formed complete text proves
  nothing about the failure mode this ticket closed) and all pass
  unmodified in behavior.

### Changed
```
 tickets.md | 105 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 103 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 6 error(s), 485 warning(s), 716 waived
- error-findings: ARCH001@src/frob/tickets/_evidence.py, DOC009@docs/audits/docs-completeness-2026-08-06.md, TICK006@tickets.md, WIRE001@tests/unit/test_ticket_runner_gate_findings.py, invalid-parameter-default@tests/unit/test_ticket_runner_gate_findings.py, unresolved-attribute@tests/test_ticket_work_and_land_finish.py
