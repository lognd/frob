# Agentic time/token profiling (T-0178)

Diagnostics ONLY. Nothing on this page is a gate, a rule id, or something
`frob check` consults -- this is for designing tooling around (spotting
where a result cache would pay off, which tool needs quieter output,
which review round is expensive), never for gating a ticket or a commit.

## What gets recorded

Two writers append newline-delimited JSON to the same local file,
`.frob/telemetry.jsonl` (already covered by the repo's `.frob/` gitignore
entry, never committed, never networked):

1. **Every `frob` CLI invocation** -- `frob.app.telemetry.timed_call`,
   wired into `App.__call__`, appends one `kind="cli"` record per
   invocation: ISO timestamp, subcommand, a redacted args head, duration
   in ms, exit code, and the repo's current short git sha (`tree_hash`).
2. **Every ticket state transition** (`created`/`started`/`done`) --
   `frob.app.telemetry.record_ticket_event`, called from
   `frob.app.ticket_runner`'s `new`/`start`/`close` handlers, appends one
   `kind="ticket"` record with an ISO timestamp. Ticket frontmatter itself
   still stores `created` as a date-only field (deliberately unchanged --
   see the ticket's Done report for why this is additive telemetry rather
   than a frontmatter schema migration); the telemetry stream is what
   makes per-ticket cycle/lead time computable.
3. **Every harness tool call**, if the hook below is wired up -- one
   `kind="tool"` record per `PostToolUse` event: tool name, a redacted
   input head, duration (when the harness provides it), and an estimated
   output-token count.

## Wiring the Claude Code hook

Add to the project's <!-- frob:waive DOC006 reason="a user-local settings file that is not itself tracked in this repo" -->`.claude/settings.json` (or `settings.local.json` for
a personal-only setup):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {"type": "command", "command": "scripts/frob-telemetry-hook"}
        ]
      }
    ]
  }
}
```

`scripts/frob-telemetry-hook` reads the hook's JSON payload on stdin and
appends the event; it prints nothing on success (a `PostToolUse` hook that
prints stdout is treated as feedback routed back to the agent, which this
is not) and always exits 0 -- telemetry must never be able to fail a real
tool call. Hooks fire for subagent tool calls too, so implementer/reviewer
dispatch rounds are covered automatically, with no per-tool shim needed in
this repo's own agent tooling.

### PATH-shim mode (outside the harness)

To profile a plain shell session (no Claude Code hook plumbing), invoke
the same script directly:

```bash
scripts/frob-telemetry-hook --tool pytest --duration-ms 4200 \
  --input "pytest -q tests/test_stats.py" --output "$(pytest -q 2>&1)"
```

This appends the same `kind="tool"` shape by hand, so `frob stats` run with
`FROB_STATS_AGENTIC=1` set (the agentic report is an env-var trigger, not
yet a `--agentic` CLI flag -- see `frob.app.stats_runner._AGENTIC_ENV`)
sees shell-driven work the same way it sees harness-driven work.

## Reading the report

```bash
FROB_STATS_AGENTIC=1 frob stats            # human-readable
FROB_STATS_AGENTIC=1 frob stats --json     # machine-readable
```

See `docs/modules/stats.md#agentic-timetoken-profiling---agentic-t-0178`
for what each section of the report means. In short: command time by
category, the slowest individual invocations, retread candidates
(identical command + unchanged tree, i.e. what a result cache would have
skipped -- the measured payoff case for T-0177's daemon), per-ticket
cycle/lead time, and estimated output tokens per tool.

## Redaction and opt-out

Every free-text field this stream stores (a command's args head, a tool
call's input head) is passed through `frob.gates._secrets`'s existing
provider-pattern scanner (T-0157) before being written -- the SAME
patterns `SEC001`/`SEC002`/`SEC003` check tracked files against, reused
rather than re-derived, so there is exactly one place secret-shaped
strings are recognized in this repo.

Set `FROB_NO_TELEMETRY=1` (any non-empty, non-`0`/`false` value) to
disable both writers entirely. `.frob/` is gitignored repo-wide, so the
stream is never accidentally committed even without the opt-out.

## Coordinator flow: recording harness usage at ticket close

The per-call token estimates above are a heuristic (`len(text) / 4`,
documented in `frob.app.telemetry.estimate_tokens`), not ground truth.
The harness's own usage block for a dispatch (subagent tokens, tool-use
count, wall-clock duration) IS ground truth for that dispatch, and is
worth attaching to the ticket it belongs to so cost history survives past
the session: `frob ticket attach <id> --caption "dispatch usage: ..."` (or
paste the block into the ticket body / Done report addendum) at close
time, alongside the normal evidence recording. Reconciling the attached
ground-truth block against this page's per-call estimates for the same
dispatch is what surfaces the discrepancy between the two (T-0178
addendum, part c) -- report both numbers, not just one.

## Footgun detection (T-1360)

Three separate incidents in one drive session (T-1293, T-1337, and a
coordinator's own 180x-speedup misread) shared the same shape: a command
completed and LOOKED like success -- or like a legitimate result -- while
actually failing or under-reporting. `timed_call` now runs a detection
pass over the trailing telemetry corpus after every invocation and prints
any findings AFTER the command (`_log.warning`, never blocking, never
changing the exit code):

- `REDUNDANT_RERUN`: this exact `(subcommand, args_head, tree_hash)` ran
  before at the current tree state -- nothing could have changed.
- `FAST_EXIT1`: this run exited nonzero in under 2 seconds -- the trap
  the coordinator hit reading a fast failure as a fast success.
- `REPEATED_FAILURE`: the identical command has now failed 3+ times in a
  row with no successful run in between -- stuck, not progressing.

(The ticket's fourth named rule, filtered-verification-before-`land`, is
deliberately NOT duplicated here -- `frob check`'s own `gate:scope-note`
line, T-1351, already covers "what a `--only`/`--ticket` run suppressed";
see `docs/guides/agent-playbook.md#6c-a---only--ticket-scoped-0-findings-is-not-a-package-clean-claim-t-1351`
for that mechanism.)

Tips are individually suppressible (`FROB_SUPPRESS_TIPS=FAST_EXIT1,...`,
comma-separated rule ids) or disabled entirely
(`FROB_NO_FOOTGUN_TIPS=1`) without also disabling recording -- a tip that
nags gets ignored, which is worse than no tip. When the triggering
invocation itself passed `--json`, tips render as a JSON array on the same
channel instead of a human-readable line, so an agent parsing stdout can
also parse the tip and self-correct (`render_tips`, `Tip.model_dump`).

`frob doctor --usage` (`--json` supported) reports the same rules
aggregated over the WHOLE local corpus: total calls/duration, failure
rate, top time sinks by subcommand, redundant-rerun count and wasted
wall-clock, fast-exit-1 count, and stuck-repeat streak count
(`usage_report`) -- the "where does the time go" question this ticket's
own corpus mining answered by hand, now a command.

## Public API

<!-- frob:describes src/frob/app/telemetry.py::TELEMETRY_REL -->
<!-- frob:describes src/frob/app/telemetry.py::T -->
<!-- frob:describes src/frob/app/telemetry.py::is_disabled -->
<!-- frob:describes src/frob/app/telemetry.py::iso_now -->
<!-- frob:describes src/frob/app/telemetry.py::redact_command -->
<!-- frob:describes src/frob/app/telemetry.py::append_event -->
<!-- frob:describes src/frob/app/telemetry.py::tree_hash -->
<!-- frob:describes src/frob/app/telemetry.py::estimate_tokens -->
<!-- frob:describes src/frob/app/telemetry.py::record_cli_event -->
<!-- frob:describes src/frob/app/telemetry.py::record_ticket_event -->
<!-- frob:describes src/frob/app/telemetry.py::record_dispatch_event -->
<!-- frob:describes src/frob/app/telemetry.py::timed_call -->
<!-- frob:describes src/frob/app/telemetry.py::Tip -->
<!-- frob:describes src/frob/app/telemetry.py::tips_disabled -->
<!-- frob:describes src/frob/app/telemetry.py::detect_footguns -->
<!-- frob:describes src/frob/app/telemetry.py::render_tips -->
<!-- frob:describes src/frob/app/telemetry.py::SubcommandTimeSink -->
<!-- frob:describes src/frob/app/telemetry.py::UsageReport -->
<!-- frob:describes src/frob/app/telemetry.py::usage_report -->

```python
TELEMETRY_REL: Path                # ".frob/telemetry.jsonl", relative to a repo root
def is_disabled() -> bool
def iso_now() -> str
def redact_command(text) -> str
def append_event(root, record) -> None
def tree_hash(root) -> str
def estimate_tokens(text) -> int
def record_cli_event(root, *, subcommand, args_head, duration_ms, exit_code) -> None
def record_ticket_event(root, *, ticket_id, event, extra=None) -> None
def record_dispatch_event(root, *, dispatch_id, event, worktree=None, branch=None, cold_start=None) -> None
def timed_call(root, *, subcommand, args_head, fn) -> T
class Tip(BaseModel): rule_id, message, suggested_command
def tips_disabled() -> bool
def detect_footguns(root, *, subcommand, args_head, duration_ms, exit_code, tree_hash_value) -> list[Tip]
def render_tips(tips, *, as_json) -> str
class SubcommandTimeSink(BaseModel): subcommand, calls, total_duration_ms, failures
class UsageReport(BaseModel): total_calls, total_duration_ms, failures, failure_rate, top_time_sinks, redundant_rerun_count, redundant_rerun_wasted_ms, fast_exit1_count, repeated_failure_streaks
def usage_report(root, *, top_n=10) -> UsageReport
```
