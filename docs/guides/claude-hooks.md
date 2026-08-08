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

A PreToolUse hook that refuses a long-running frob verb (`land`,
`done-report`, `check`, `test`) run without a large Bash tool-level
timeout -- the recurring 120s-auto-background stall class
`docs/guides/agent-playbook.md`'s section 3b/3c document at length.
`MIN_TIMEOUT_MS` (300000) is the floor a Bash call's `timeout` parameter
must meet; `PATTERN` matches the guarded verbs at command position (via
`_shellscan.POS`); `REASON` is the exact refusal text an agent sees,
naming the re-run recipe. `main` reads the tool-input payload from stdin
and emits `REASON` (blocking) when a guarded verb appears without a
qualifying timeout.

## `sync-claude-config.py`

Materialises the git-tracked canonical `.claude/hooks/**` /
`.claude/agents/**` / `.claude/skills/**` trees into `~/.claude/` (the
directory Claude Code actually reads hooks from) so every clone's hook
behavior stays byte-identical to what is committed -- hand-editing the
`~/.claude/` copy is explicitly the anti-pattern `_shellscan.py`'s own
docstring warns against. `main` supports `--check` (report drift without
writing) alongside the default sync-and-write mode.

## The `claude_hooks` design node

T-1838 declared a `claude_hooks : trusted` node (`code ".claude/hooks/**"`)
in `design/frob.strata` once un-pruning `.claude` from the graph walk made
these files visible to SELFAUDIT/SYS103 for the first time -- see that
node's own inline comment for the measured `may` capability list
(`env.read`/`exec`/`fs.write`/`fs.read`). This page is its COV001
`frob:doc` target; the node's trust/capability modeling itself is owned by
T-1838, not this page.
