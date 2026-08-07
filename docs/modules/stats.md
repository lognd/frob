# frob.stats -- delivery measurement (DORA-ish)

One sentence: `frob stats` reports ticket-queue health and commit cadence
so a team can see delivery trends -- measurement only, never a gate (a
thermometer, not a thermostat).

<!-- frob:describes src/frob/stats/__init__.py::collect -->
```bash
frob stats               # queue health + commits over the last 30 days
frob stats --days 90     # wider commit window
frob stats --json        # machine-readable
```

Output covers:

- **Tickets**: total, doable, blocked, counts by state and kind, and the
  number of failure-log entries across the queue (a rework/recurrence
  signal).
- **Commits**: total in the window, an approximate per-week rate, and a
  breakdown by conventional-commit type (feat/fix/chore/...), a
  deployment-frequency proxy.

Deliberately not a gate: DORA-style metrics diagnose, they do not enforce.

## Agentic time/token profiling (`--agentic`, T-0178)

`FROB_STATS_AGENTIC=1 frob stats` (`--json` for machine-readable) renders a
SEPARATE, also non-gated report over `.frob/telemetry.jsonl` -- the local
stream `frob`'s own CLI-entry timing hook (`frob.app.telemetry`) and the
Claude Code PostToolUse hook script (`scripts/frob-telemetry-hook`) append
to. See `docs/guides/agentic-time-profiling.md` for the full setup
(hook wiring, redaction, opt-out) and `frob.stats._agentic.agentic_report`
for the aggregation this renders:

- command time broken down by category (frob-check / test-suite /
  native-build / vcs / other)
- the top wall-clock sinks (slowest individual invocations)
- retread candidates: identical command + tree-hash re-runs, a direct,
  measured signal for what a result cache (T-0177) would save
- per-ticket cycle/lead time, reconstructed from `created`/`started`/
  `done` telemetry events (tickets' own frontmatter is still date-only;
  this is intentionally additive, not a frontmatter schema change)
- estimated output tokens per harness tool, from PostToolUse hook events

Trigger note: this is an env var, not a <!-- frob:waive DOC006 reason="proposal syntax for a flag that does not exist, the same sentence explains it is not real" -->`frob stats --agentic` argparse
flag, because T-0178's declared scope excluded `src/frob/__main__.py`
(where every subcommand's flags are registered) -- wiring the real CLI
flag is a small follow-up (see the ticket's Done report for the filed id).

Set `FROB_NO_TELEMETRY=1` to disable telemetry writes entirely, at either
hook site; the stream is local-only (`.frob/` is gitignored) and never
networked. Free-text fields (command args, tool inputs) are redacted
through `frob.gates._secrets`'s existing provider patterns before being
written, never through a second hand-rolled scanner.

<!-- frob:invariant INV-022 -->

## Dispatch cost vs delivery (T-1724)

`frob.stats.dispatch_cost_report` answers the question the 2026-08-07
hand-tally incident got wrong twice over: what does a dispatched agent
cost, and what did it deliver. It joins a NEW `kind="dispatch"` telemetry
event (`frob.app.telemetry.record_dispatch_event`, one at
`event="start"` and one at `event="end"` per dispatch, opened when an
agent begins work in a worktree and closed when it stops) against the
existing `kind="tool"` (cost) and `kind="ticket"` (delivery) events in the
SAME `.frob/telemetry.jsonl` stream `agentic_report` reads -- every event
whose `iso_ts` falls inside a dispatch's `[start, end]` window is
attributed to it, by timestamp, since neither existing event kind carries
a dispatch id of its own.

No caller wires `record_dispatch_event` or renders `dispatch_cost_report`
yet -- that is a `.claude/hooks/**` (SessionStart/Stop) and
`src/frob/app/stats_runner.py` change respectively, filed as a follow-up
(see T-1724's Done report for the id) and deliberately out of this
ticket's own scope, which is the schema and the join, not the wiring.
`dispatch_cost_report(root)` is reachable today via
`frob stats --agentic --json` (the pydantic model dumps automatically
through the existing `--json` path) even with no dispatch events recorded
yet -- an empty/absent stream produces an all-empty report, same posture
as `agentic_report`.

Schema decisions this ticket exists to enforce, each one a direct fix for
how the 2026-08-07 incident went wrong:

- **`output_tokens_delta` is explicitly a per-run figure**, named `_delta`
  rather than a bare `tokens`, so nothing downstream has to infer whether
  a number is a running total or one run's own cost by watching whether
  it goes up. `cold_start` is likewise recorded explicitly at
  `event="start"` time (`True`/`False`/`None` for "not recorded") rather
  than inferred from any other field.
- **Ordering is explicit.** Every event already carries an `iso_ts`;
  `DispatchRecord`s are returned sorted by it (`_dispatch_sort_key`,
  unparseable/missing timestamps sort last, deterministically by
  `dispatch_id`) so a reader never has to reconstruct sequence itself --
  the exact class of error (runs reconstructed in the wrong order) that
  inverted the incident's headline figure.
- **"Could not measure" is representable and never renders as `0`.**
  `output_tokens_delta`, `tokens_per_landed_ticket`, and
  `cold_start_floor_tokens` are all `None` (not `0`/`0.0`) whenever their
  inputs contain no measured data -- a dispatch with zero attributed tool
  events is unmeasured, not free (mirroring T-1703's sweep-reads-zero
  fix, applied here to cost instead of coverage).
- **Non-gated.** Like the rest of `frob.stats`, nothing here fails a gate
  and malformed telemetry lines are skipped, never raised.

The derived numbers `agentic_report` alone could not produce:

- `tokens_per_landed_ticket`: total measured tokens across every dispatch
  divided by the total count of tickets delivered.
- `cold_start_floor_tokens`: mean measured token cost among dispatches
  that delivered zero tickets -- "the cost of a dispatch that landed
  nothing."
- `zero_delivery_dispatch_ids`: dispatches that measurably spent tokens
  (a real, positive `output_tokens_delta`) but delivered nothing -- the
  retirement signal the ticket asks for; a dispatch whose cost could not
  be measured is excluded rather than assumed wasteful.
- `marginal_run_deltas`: the token-cost delta between one dispatch and the
  previous one against the SAME worktree (the stable identity a resumed
  agent keeps across runs, unlike `dispatch_id`, which is fresh every
  time), ordered 1-based per worktree -- the exact cold-start-vs-resume
  comparison the incident could not settle.

## Public API

<!-- frob:describes src/frob/stats/__init__.py::TicketStats -->
<!-- frob:describes src/frob/stats/__init__.py::CommitStats -->
<!-- frob:describes src/frob/stats/__init__.py::StatsReport -->
<!-- frob:describes src/frob/stats/__init__.py::ticket_stats -->
<!-- frob:describes src/frob/stats/__init__.py::commit_stats -->
<!-- frob:describes src/frob/stats/__init__.py::collect -->
<!-- frob:describes src/frob/stats/_agentic.py::AgenticReport -->
<!-- frob:describes src/frob/stats/_agentic.py::CategoryTime -->
<!-- frob:describes src/frob/stats/_agentic.py::TimeSink -->
<!-- frob:describes src/frob/stats/_agentic.py::RetreadCandidate -->
<!-- frob:describes src/frob/stats/_agentic.py::TicketCycleTime -->
<!-- frob:describes src/frob/stats/_agentic.py::ToolTokens -->
<!-- frob:describes src/frob/stats/_agentic.py::agentic_report -->
<!-- frob:describes src/frob/stats/_agentic.py::DispatchRecord -->
<!-- frob:describes src/frob/stats/_agentic.py::MarginalRunDelta -->
<!-- frob:describes src/frob/stats/_agentic.py::DispatchCostReport -->
<!-- frob:describes src/frob/stats/_agentic.py::dispatch_cost_report -->
<!-- frob:describes src/frob/app/telemetry.py::record_cli_event -->
<!-- frob:describes src/frob/app/telemetry.py::record_ticket_event -->
<!-- frob:describes src/frob/app/telemetry.py::record_dispatch_event -->
<!-- frob:describes src/frob/app/telemetry.py::timed_call -->

```python
class TicketStats(BaseModel)      # queue-health snapshot: state/kind counts, doable/blocked, failure entries
class CommitStats(BaseModel)      # commit cadence over a window, by conventional-commit type
class StatsReport(BaseModel)      # combined delivery snapshot rendered by `frob stats`
def ticket_stats(queue) -> TicketStats
def commit_stats(root, window_days=30) -> Result[CommitStats, GitError]
def collect(root, window_days=30) -> Result[StatsReport, GitError]

class AgenticReport(BaseModel)    # non-gated time/token snapshot over .frob/telemetry.jsonl
def agentic_report(root, top_n=10) -> AgenticReport

class DispatchRecord(BaseModel)   # one dispatch's cost joined against delivery, by iso_ts window
class MarginalRunDelta(BaseModel) # token-cost delta between one dispatch and the previous one in the same worktree
class DispatchCostReport(BaseModel)  # dispatches + tokens_per_landed_ticket/cold_start_floor_tokens/zero_delivery_dispatch_ids/marginal_run_deltas
def dispatch_cost_report(root) -> DispatchCostReport
def record_dispatch_event(root, *, dispatch_id, event, worktree=None, branch=None, cold_start=None) -> None
```
