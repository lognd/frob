---
id: T-1724
title: 'Measure dispatch cost against tickets landed: join agent telemetry to a dispatch
  record in frob stats --agentic'
state: done
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/stats/_agentic.py
- src/frob/app/telemetry.py
- tests/test_stats_agentic.py
- docs/modules/stats.md
- src/frob/stats/__init__.py
- tests/test_telemetry.py
- docs/guides/agentic-time-profiling.md
- design/frob.strata
- tickets/T-1724/ticket.md
- tickets/T-1724/done-report.md
- tickets/T-1787/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/stats/__init__.py
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_telemetry.py
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1724/ticket.md
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1724/done-report.md
  reason: package re-export list + record_dispatch_event's own test file + its frob:doc
    anchor + SELFAUDIT001's core-node interface= list + v2 ledger per-ticket files,
    all direct consequences of the new public symbols
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1787/ticket.md
  reason: the draft ticket filed as this ticket's own wiring follow-up is a direct
    artifact of this ticket's work, same as its own ticket.md/done-report.md
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_stats_agentic.py::TestDispatchCostReport::test_tool_events_join_by_window_and_sum_tokens
- tests/test_stats_agentic.py::TestDispatchCostReport::test_zero_delivery_dispatch_flagged_only_when_measurably_costly
- tests/test_stats_agentic.py::TestDispatchCostReport::test_marginal_run_deltas_ordered_and_computed_per_worktree
- tests/test_stats_agentic.py::TestDispatchCostReport::test_dispatch_with_no_tool_events_has_unmeasured_not_zero_tokens
- tests/test_telemetry.py::TestRecordDispatchEvent::test_start_and_end_events_shaped_correctly
designated_repro_test: null
threat: null
component: null
---
There is no measured answer to "what does a dispatched agent cost, and what
did it deliver". Coordinators size waves, batch tickets, and decide when to
retire an agent on intuition.

WHY THIS TICKET EXISTS, CONCRETELY. On 2026-08-07 a coordinator hand-tallied
twelve agent runs out of task-notification text to answer exactly that
question, and got it wrong twice:

- The runs were reconstructed in the wrong ORDER, which inverted the
  headline figure. A claimed "+263k tokens for 6 tool uses" -- offered as
  the evidence that resuming a heavy agent is expensive -- became a
  DECREASE once the sequence was corrected. The conclusion did not survive
  its own data.
- Whether the underlying counter was cumulative-per-agent or per-run could
  not be determined from the source at all. Under one reading resume is
  ruinous; under the other it is nearly free. Those are opposite operating
  policies and the number could not distinguish them.

A retirement threshold was then published and withdrawn within the hour.
That is the cost of an unmeasured process metric: not a missing number, but
a confidently wrong one.

WHAT ALREADY EXISTS. Do not build a second stream. `frob.stats._agentic`
already aggregates `.frob/telemetry.jsonl` (written by `frob.app.telemetry.
append_event`/`record_cli_event` and the PostToolUse hook), and already
models `ToolTokens` (output tokens per tool), `TicketCycleTime` (from
created/started/done transition events), `TimeSink`, and
`RetreadCandidate`. The substrate is there.

THE MISSING PIECE IS THE JOIN: cost is recorded per tool call, and delivery
is recorded per ticket, and nothing connects them to a DISPATCH.

Add a dispatch as a first-class record:

- A dispatch id, opened when an agent starts work in a worktree and closed
  when it stops, with the worktree/branch it owned.
- Cost accumulated against it: output tokens, tool calls, wall clock,
  and -- crucially -- whether the run was a COLD START or a RESUME. The
  whole open question is the relative price of those two, and a schema that
  cannot tell them apart cannot answer it.
- Delivery attributed to it: the ticket ids that reached done/dropped
  during that dispatch, via the transition events `TicketCycleTime`
  already reads.

Then report the derived numbers `frob stats --agentic` cannot currently
produce: tokens per landed ticket; cold-start floor (cost of a dispatch
that landed nothing); marginal cost of run N vs run N+1 for the same agent;
and dispatches that consumed budget while landing zero, which is the
signal that actually matters for retirement.

HARD REQUIREMENTS, each one a lesson this repo has already paid for:

- The counter's semantics must be UNAMBIGUOUS in the schema -- a field is
  either a per-run delta or a running total, named so, never inferrable
  only by watching whether it goes up. That ambiguity is the whole reason
  this ticket exists.
- Records are ordered by an explicit sequence or timestamp the reader does
  not have to reconstruct. Mis-ordering was the first error.
- "Could not measure" must be representable and must NEVER render as 0.
  A zero cost is a measurement; a missing one is not. Reporting an
  unmeasured dispatch as free would recreate the sweep-reads-zero class
  (T-1703) in the process metrics.
- Non-gated, like the rest of `_agentic`: nothing here fails a gate.
  Telemetry that can block a land will be turned off, and then measured
  nothing.
- Malformed lines skipped, never raised -- match `_load_events`'s existing
  posture; a partially-written telemetry file must not break `frob stats`.

Related: T-1344 (agentic throughput: the land path is the bottleneck) is
the same concern from the other end -- it argues about where time goes
without a way to measure where it went. This ticket is the instrument that
would settle it.

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
