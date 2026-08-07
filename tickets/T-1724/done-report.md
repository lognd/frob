## Done report

There is now a measured answer to "what does a dispatched agent cost,
and what did it deliver" instead of a hand-tally: `frob.app.telemetry.
record_dispatch_event` writes a new `kind="dispatch"` boundary event
(one at `event="start"`, one at `event="end"`, with an explicit
`cold_start` field), and `frob.stats.dispatch_cost_report` joins it
against the existing `kind="tool"` (cost) and `kind="ticket"` (delivery)
events in the same `.frob/telemetry.jsonl` stream `agentic_report`
already reads, attributing every event whose `iso_ts` falls inside a
dispatch's window to it (neither tool nor ticket events carry a dispatch
id of their own, so the join is by timestamp).

Derived numbers `agentic_report` alone could not produce:
- `tokens_per_landed_ticket`
- `cold_start_floor_tokens` (mean cost of a zero-delivery dispatch)
- `zero_delivery_dispatch_ids` (measurably costly, delivered nothing --
  the retirement signal)
- `marginal_run_deltas` (token-cost delta between one dispatch and the
  previous one against the SAME worktree, 1-based per-worktree ordering)

Hard requirements from the ticket, each addressed directly:
- `output_tokens_delta` is explicitly per-run (named `_delta`, never a
  bare `tokens`) so a reader never infers cumulative-vs-delta by
  watching whether it goes up. `cold_start` is recorded explicitly, not
  inferred.
- Every `DispatchRecord` carries its own `start_ts`/`end_ts`; the report
  returns them sorted by `_dispatch_sort_key` (unparseable/missing
  timestamps sort last, deterministically) so a reader never has to
  reconstruct ordering.
- "Could not measure" is `None`, never `0`/`0.0`: `output_tokens_delta`
  is `None` when zero tool events fell in the window;
  `tokens_per_landed_ticket`/`cold_start_floor_tokens` are `None` when
  their inputs contain no measured dispatch. `tool_call_count` stays a
  real integer (including a genuine `0`) since it counts observed
  events rather than deriving a sum.
- Non-gated: nothing here fails a gate. Malformed telemetry lines are
  skipped, matching `_load_events`'s existing posture.

Not done, disclosed rather than silently dropped: nothing calls
`record_dispatch_event` at a real dispatch boundary yet, and nothing
calls `dispatch_cost_report` from the CLI's text renderer -- both are
`.claude/hooks/**` and `src/frob/app/stats_runner.py` changes,
deliberately outside this ticket's declared scope (schema + join, not
the wiring). Filed as T-1787 (renumbers at land), with
`frob:waive WIRE001 ... follow_up="T-1787"` on both new
public symbols so the "new symbol, no caller" gate names WHY rather
than being silenced blind. `--json` output already surfaces
`dispatch_cost_report` today via the existing `model_dump_json()` path.

Scope additions beyond the ticket's own declared list, each a direct,
mechanical consequence of the new public symbols rather than expanded
work: `src/frob/stats/__init__.py` (the package's own re-export list),
`tests/test_telemetry.py` (record_dispatch_event's unit tests, mirroring
record_cli_event/record_ticket_event's existing home),
`docs/guides/agentic-time-profiling.md` (record_dispatch_event's
frob:doc anchor), `design/frob.strata` (SELFAUDIT001/SYS104's core-node
interface= list, which must declare a symbol once another node imports
it), and the v2 per-ticket ledger files for both T-1724 and its own
filed draft.

### Changed
```
 design/frob.strata                    |   2 +-
 docs/guides/agentic-time-profiling.md |   2 +
 docs/modules/stats.md                 |  77 ++++++++
 src/frob/app/telemetry.py             |  52 ++++++
 src/frob/stats/__init__.py            |   8 +
 src/frob/stats/_agentic.py            | 328 ++++++++++++++++++++++++++++++++++
 tests/test_stats_agentic.py           | 321 ++++++++++++++++++++++++++++++++-
 tests/test_telemetry.py               |  40 +++++
 tickets/T-1724/ticket.md              |  65 ++++++-
 tickets/T-1787/ticket.md    |  59 ++++++
 10 files changed, 951 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_stats_agentic.py::TestDispatchCostReport::test_tool_events_join_by_window_and_sum_tokens` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::TestDispatchCostReport::test_zero_delivery_dispatch_flagged_only_when_measurably_costly` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::TestDispatchCostReport::test_marginal_run_deltas_ordered_and_computed_per_worktree` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::TestDispatchCostReport::test_dispatch_with_no_tool_events_has_unmeasured_not_zero_tokens` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::TestRecordDispatchEvent::test_start_and_end_events_shaped_correctly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 660 warning(s), 723 waived
- error-findings: none (measured, zero errors)
