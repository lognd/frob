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

Add to the project's `.claude/settings.json` (or `settings.local.json` for
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

This appends the same `kind="tool"` shape by hand, so `frob stats
--agentic` sees shell-driven work the same way it sees harness-driven work.

## Reading the report

```bash
FROB_STATS_AGENTIC=1 frob stats            # human-readable
FROB_STATS_AGENTIC=1 frob stats --json     # machine-readable
```

See `docs/modules/stats.md#agentic-time-token-profiling---agentic-t-0178`
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
<!-- frob:describes src/frob/app/telemetry.py::timed_call -->

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
def timed_call(root, *, subcommand, args_head, fn) -> T
```
