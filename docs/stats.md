# frob.stats -- delivery measurement (DORA-ish)

One sentence: `frob stats` reports ticket-queue health and commit cadence
so a team can see delivery trends -- measurement only, never a gate (a
thermometer, not a thermostat).

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
Lead-time-to-close is not yet reported because tickets record a created
date but not a close timestamp -- a future ticket adds close-time capture.

## Public API

<!-- frob:describes src/frob/stats/__init__.py::TicketStats -->
<!-- frob:describes src/frob/stats/__init__.py::CommitStats -->
<!-- frob:describes src/frob/stats/__init__.py::StatsReport -->
<!-- frob:describes src/frob/stats/__init__.py::ticket_stats -->
<!-- frob:describes src/frob/stats/__init__.py::commit_stats -->
<!-- frob:describes src/frob/stats/__init__.py::collect -->

```python
class TicketStats(BaseModel)      # queue-health snapshot: state/kind counts, doable/blocked, failure entries
class CommitStats(BaseModel)      # commit cadence over a window, by conventional-commit type
class StatsReport(BaseModel)      # combined delivery snapshot rendered by `frob stats`
def ticket_stats(queue) -> TicketStats
def commit_stats(root, window_days=30) -> Result[CommitStats, GitError]
def collect(root, window_days=30) -> Result[StatsReport, GitError]
```
