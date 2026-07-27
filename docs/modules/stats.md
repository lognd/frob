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
<!-- frob:describes src/frob/app/telemetry.py::record_cli_event -->
<!-- frob:describes src/frob/app/telemetry.py::record_ticket_event -->
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
```
