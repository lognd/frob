---
id: T-1724
title: 'Measure dispatch cost against tickets landed: join agent telemetry to a dispatch
  record in frob stats --agentic'
state: queued
kind: feature
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/stats/_agentic.py
- src/frob/app/telemetry.py
- tests/test_stats_agentic.py
- docs/modules/stats.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
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