# `.claude/hooks/**` -- Claude Code dispatch-harness hooks

These scripts are invoked directly by the Claude Code harness (PreToolUse/
SessionStart/Stop events, a JSON payload on stdin) -- not by `frob`'s own
CLI dispatch table. They execute on every session in this repo, and one of
them (`dispatch-telemetry.py`) writes real telemetry, so T-1838 (see below)
made them visible to the graph like any other tracked source rather than
leaving them permanently invisible to waivers/design/coverage gates. This
page is the `frob:doc` home COV001 requires for their public symbols.

## `_shellscan.py`

Shared shell-command scanning primitives used by every hook that decides
something from a Bash command string (`frob-timeout-guard.py`, and any
future PreToolUse hook needing the same anchor). `POS` is the compiled
command-position regex (line start, after a shell connector, or after
`uv run`, optionally `timeout N`-wrapped) that both problems the module
docstring names -- command-position anchoring and quoted-text exclusion --
are built from. `strip_quoted` blanks quoted spans and heredoc bodies so a
rule only ever matches what the shell would actually execute, never prose
a command merely carries (commit messages, echoed strings). Covered by
`tests/test_hook_dispatch_telemetry.py`'s and
`tests/test_hook_diagnosis_nudge.py`'s own subprocess-level exercises of
`frob-timeout-guard.py`'s import of it (T-1838's COV001/TEST001 fallout
ticket exempted `.claude/hooks/**` from TEST001's per-file unit-test
demand the same way `_test001_002` already exempts `*.strata` files --
see `docs/modules/gates.md` for that exemption's rationale).

## `diagnosis-nudge.py`

A Stop-event hook (playbook `docs/guides/agent-playbook.md#11b`): if the
turn's own last message states a diagnosis-shaped claim with no matching
`frob ticket new` in this repo's telemetry stream recently, appends a
`systemMessage` nudge naming the gap. `main` reads the JSON payload on
stdin and always exits 0 -- a Stop hook that can fail the turn is worse
than one that misses a nudge. Never blocks; rate-limits itself per
session. Tested end-to-end via `tests/test_hook_diagnosis_nudge.py`.

## `dispatch-telemetry.py`

A SessionStart/Stop hook that records dispatch start/end events (cold
start vs resume, dispatch id shared across the session) to this repo's
own telemetry stream -- the measurement `agentic-time-profiling.md`'s
"Wiring the Claude Code hook" section documents wiring. `main` dispatches
on `hook_event_name`; unrecognized/missing event names are a silent
no-op, and it always exits 0 for the same reason `diagnosis-nudge.py`
does -- a telemetry hook must never fail a turn. Tested end-to-end via
`tests/test_hook_dispatch_telemetry.py`.

## `frob-suggest.py`

A PreToolUse hook that blocks-once on a raw linter/formatter invocation
(`ruff`, `mypy`, `ty`, ...) run directly instead of through
`frob check`, pointing the caller at the accountable path -- the
`[raw-linters]` block message this repo's own agents see mid-session.
`main` reads the tool-input payload from stdin and decides whether this
exact command was already allowed once (block-once, not block-forever).

## `frob-timeout-guard.py`

A PreToolUse hook that refuses a long-running frob verb (`ticket land`,
`ticket done-report`, `ticket work`, `ticket new`, `check`, `test`) run
without a large Bash tool-level timeout -- the recurring 120s-auto-
background stall class `docs/guides/agent-playbook.md`'s section 3b/3c
document at length. `ticket work` and `ticket new` (T-2248) were added
after both measured exceeding the 120s cap the same way: `ticket work`
creates a worktree, merges main, and builds natives; `ticket new`
contends for the ledger allocator lock behind in-flight lands and is not
safely re-runnable if backgrounded (a killed/re-run call allocates a
second ticket id). Fast verbs (`ticket show`, `ticket list`, `ticket
scope`, `verify status`, ...) are deliberately left unguarded -- guarding
every verb would train a reflexive huge timeout that defeats this guard
where it matters.
`MIN_TIMEOUT_MS` (300000) is the floor a Bash call's `timeout` parameter
must meet; `PATTERN` matches the guarded verbs at command position (via
`_shellscan.POS`); `REASON` is the exact refusal text an agent sees,
naming the re-run recipe. `main` reads the tool-input payload from stdin
and emits `REASON` (blocking) when a guarded verb appears without a
qualifying timeout.

T-2282: `main` also denies an explicit `run_in_background=true` outright,
in agent context (`FROB_AGENT` set) only, regardless of which command it
names -- `RUN_IN_BACKGROUND_REASON` is the refusal text. This closes the
class the verb-enumeration `PATTERN` check cannot: T-2248's list was
bypassed the very next stall by a non-frob command
(`python3 scripts/fleet_status.py`), so this checks the structured
`run_in_background` parameter directly instead of extending the list
again. The coordinator's own shell has no `FROB_AGENT` set and is
unaffected -- it may still background a long measurement.

## `pending-background-guard.py`

A Stop hook (T-2282) that refuses to end a turn stranding an unresolved
background Bash task -- the failure mode `frob-timeout-guard.py` cannot
close alone, since no PreToolUse hook can see the harness's own ~120s
auto-background timer, and a command-name-enumeration approach
(T-2248's `PATTERN`) was proven bypassable by the very next stall's
non-frob command. This hook instead fires on the STRANDING itself,
reconstructed from the transcript rather than a dedicated payload field
(the Stop payload's own documented fields -- `session_id`,
`transcript_path`, `cwd`, `stop_hook_active`, `reason` -- carry no
"pending background tasks" signal).

`_AUTO_BACKGROUND_ID` / `_EXPLICIT_BACKGROUND_ID` / `_AUTO_BACKGROUND_ACK`
are the three lexical start markers a background task leaves in the
transcript JSONL (the structured `toolUseResult.backgroundTaskId` field,
and two acknowledgement-text phrasings). `_tail_text` reads only the last
`_TAIL_BYTES` of `transcript_path` -- transcripts observed in this repo
exceed 40MB, and only the most recent task matters here. `_pending_task_id`
finds a start marker whose id never genuinely reappears afterward (masking
out the OTHER start pattern's mention of the very same event first, so one
real background-start is not mistaken for its own resolution); a later
completion notification (`<task-id>...<status>...</status>`) or an
explicit poll of the task's output both count as resolution -- the latter
is a known, accepted false negative (a poll showing the job still running
still reads as "resolved" here). `REASON` is the block message; `_decision`
returns `{"decision": "block", ...}` when `_pending_task_id` finds one
pending id and `stop_hook_active` is not already `True` -- the re-entrancy
check that guarantees this hook blocks AT MOST ONCE per turn, so a
genuinely stuck agent can still report-and-stop on the second attempt.
`main` reads the JSON payload on stdin, fails open (exit 0, no output) on
any read/parse error, and prints the block decision only when one fires.
Tested end-to-end via `tests/test_hook_pending_background_guard.py`.

## `sync-claude-config.py`

Materialises the git-tracked canonical `.claude/hooks/**` /
`.claude/agents/**` / `.claude/skills/**` trees into `~/.claude/` (the
directory Claude Code actually reads hooks from) so every clone's hook
behavior stays byte-identical to what is committed -- hand-editing the
`~/.claude/` copy is explicitly the anti-pattern `_shellscan.py`'s own
docstring warns against. `main(argv=None)` supports `--check` (report
drift without writing) alongside the default sync-and-write mode; `argv`
is accepted so a caller (see below) can drive it programmatically instead
of only via `sys.argv`.

This script stays the CANONICAL, dependency-free (stdlib-only)
implementation on purpose (T-1808): `.claude/settings.json`'s
`SessionStart` hook invokes it with a bare `python3` before any `frob`
venv is necessarily importable. `MANAGED` (the managed-file manifest) and
`plan()` (the pure decide-without-doing planner) are public, no leading
underscore, specifically so `frob claude sync [--check]`
(`src/frob/app/claude_runner.py`, `docs/modules/cli.md#frob-claude-sync-t-1808`)
can load this file by path and call straight into them -- one
implementation of the sync/drift logic, never two that can desync.
`claude_runner.drift_warning` additionally surfaces the same drift
automatically on every `frob` invocation (stderr, next to
`stale_install_warning`/`stale_binary_warning`); the WRITE stays this
script's/the verb's explicit call, never automatic.

T-1809 gates this drift as a `frob check` stage (`claude-config-drift`,
CLAUDE001, `src/frob/app/check_runner.py::_claude_config_drift_result`):
opt-in on this script existing, it fails `frob check` outright when a
managed file differs from its `~/.claude/` copy or a managed source is
missing -- the pre-land enforcement half of the same signal T-1808's
`drift_warning` already surfaces on every `frob` invocation. Not wired
into `frob.gates`'s pluggable job table (out of scope for that ticket's
dispatch window) -- it is one more opt-in extra stage `check_runner.run`
folds into `CheckResult`, the identical shape `_deploy_drift_result`/
`_deploy_conformance_result` already use for a repo with no `deploy/`.

## The `claude_hooks` design node

T-1838 declared a `claude_hooks : trusted` node (`code ".claude/hooks/**"`)
in `design/frob.strata` once un-pruning `.claude` from the graph walk made
these files visible to SELFAUDIT/SYS103 for the first time -- see that
node's own inline comment for the measured `may` capability list
(`env.read`/`exec`/`fs.write`/`fs.read`). This page is its COV001
`frob:doc` target; the node's trust/capability modeling itself is owned by
T-1838, not this page.
