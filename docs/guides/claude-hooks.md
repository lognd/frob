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

A Stop-event hook (playbook `docs/guides/agent-playbook.md#11b-the-diagnosis-nudge-stop-hook-t-1734`): if the
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
`raw-linters` rule's block message this repo's own agents see mid-session.
`main` reads the tool-input payload from stdin and decides whether this
exact command was already allowed once (block-once, not block-forever).

T-2164: block-once was, on its own, block-forever from the SECOND attempt
onward -- a caller who re-ran an identical raw command out of habit (not a
one-off) never got interrupted again. `_record_attempt` now tracks a real
count per marker instead of a boolean, and `main` escalates from the third
identical attempt (`_ESCALATE_AT_ATTEMPT`) onward: it denies again unless
the command is prefixed with `FROB_SUGGEST_ACK=1 ` (`_ACK_PREFIX`, stripped
before rule matching so the prefix itself never changes which rule fires).
The acknowledgement is checked every time, not consumed once -- a fourth
un-acked repeat is blocked again even if the third was acked through.

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

## `root-write-guard.py`

A PreToolUse hook (`Write`/`Edit`/`NotebookEdit`/`Bash`) that refuses a
dispatched agent's write into the SHARED ROOT (the primary git checkout)
at edit time -- before the tree is dirtied and every concurrent `frob
ticket land` starts refusing with DirtyMain. The pre-existing `_WORKTREE_
LEASE_HOOK_SCRIPT` git hook (`src/frob/scaffold/project.py`) only guards
COMMIT time, which is too late for the failure this closes (T-2396:
measured twice in one drive -- two agents edited the shared root instead
of their leased worktree, and a third agent's land was DirtyMain-blocked
as a result).

T-2481 extended coverage to `Bash`: three separate incidents in one
session dirtied the root through a heredoc/redirect or a `frob ticket`
mutating verb run with no `cd` into the worktree, none of which the
original `Write`/`Edit`/`NotebookEdit`-only guard could see. A Bash
command's write target is not a declared field the way `Write`'s
`file_path` is, so `_bash_targets_root` deliberately detects only two
narrow, high-frequency shapes and lets everything else -- including
anything it cannot confidently parse -- through: a `frob ticket
<mutating-verb>` (`_MUTATING_TICKET_VERBS`, read-only verbs like `show`/
`list`/`doable` excluded) with neither a leading `cd <dir> &&`/`cd
<dir>;` into a registered worktree in the same command nor `--path`
anywhere in it; and a `>`/`>>`/`tee`/`sed -i` whose target resolves under
the primary checkout (`_resolves_under_primary`). `_effective_cwd`
computes the directory a command's write actually lands in from its
leading `cd` segment, falling back to the PreToolUse payload's own `cwd`
when there is none. Any candidate path containing `$`/backtick/glob
characters (`_AMBIGUOUS_PATH_CHARS`) is treated as unresolvable and
allowed rather than guessed -- acceptance criterion 4's "when in doubt,
allow" rule, enforced as code, not just a docstring promise. This is a
narrower, ADDITIVE detector layered on top of the existing `Write`/
`Edit`/`NotebookEdit` path -- it reuses the same `_is_agent_context`
discriminator and the same primary-vs-worktree resolution, just against
command text instead of a declared `file_path`.

`_is_agent_context` is the discriminator, and it must fire for an agent
and never for the coordinator or a human (both directions matter): it
fires when `FROB_AGENT` is truthy OR `_worktree_fact` independently holds.
`FROB_AGENT` alone is insufficient -- `_WORKTREE_LEASE_HOOK_SCRIPT`'s own
T-2071 comment measured it UNSET in real Agent-tool shells -- so
`_worktree_fact` pairs it with a FACT check: `FROB_WORKTREE` (the sibling
var the same `frob agent env <worktree-path>` call always exports
alongside `FROB_AGENT`) must resolve to a directory that ACTUALLY appears
as a registered linked worktree per `git worktree list --porcelain`, not
just an unverified string. A coordinator or human shell carries neither
var (`frob agent env` is only ever invoked for a dispatched worktree
agent's own shell), so neither disjunct fires and the guard stays silent.

The refusal itself is scoped narrowly: `_target_path` resolves the file a
call targets (`file_path` for `Write`/`Edit`, `notebook_path` for
`NotebookEdit`), and `main` only denies when that path resolves (via
`git worktree list --porcelain`'s first `worktree ` line) to the PRIMARY
checkout -- a write inside the agent's own leased worktree, the normal
case, is never touched. `_is_ledger_path` exempts `tickets.md`/
`tickets/**` (the `frob ticket` CLI's own ledger writes), matching the
same carve-out `_WORKTREE_LEASE_HOOK_SCRIPT` already uses; `FROB_LAND_
INTERNAL=1` exempts everything, matching every other land-owned-file
guard (playbook section 4b). `REASON` is the exact refusal text, naming
`frob ticket work <id>` as the correct next step. `main` reads the JSON
payload from stdin and fails open (silent allow) on any parse or lookup
failure. Tested end-to-end via `tests/test_hook_root_write_guard.py`,
including a positive control proving the discriminator actually
discriminates: it fires under a simulated agent env and does not fire
under a plain coordinator/human env, both against the identical target
path.

## `_agent_context.py`

Shared, non-hook module (T-2487): the git-worktree + agent-context
discriminator (`_git`/`_worktree_paths`/`_worktree_fact`/`_is_agent_
context`) `root-cleanliness-detector.py` imports rather than re-deriving.
Extracted the first time a SECOND hook needed the identical logic
`root-write-guard.py` (T-2481) already carried as module-private helpers
-- `root-write-guard.py` itself was deliberately left unmigrated (a
just-landed, independently-tested PreToolUse guard is not worth touching
purely for reuse with no behavior change), so this module and `root-
write-guard.py`'s own copy currently coexist; treat this module as the
one to extend if a THIRD hook needs the same discriminator.

## `root-cleanliness-detector.py`

A PostToolUse hook, matcher `Bash` (T-2487): REPORTS -- never blocks --
when the shared root (the primary git checkout) is dirty immediately
after a Bash tool call in agent context. Complementary to `root-write-
guard.py` (T-2481), a different mechanism entirely: instead of inferring
a Bash command's write target from its TEXT (necessarily narrow, since
that target is not a declared field), this hook asks the one question
that actually matters AFTER the command has already run -- `git status
--porcelain` against the primary checkout -- sidestepping every shape a
text-based guard would have to enumerate. Motivated by a fourth root-
dirtying incident during T-2481's own dispatch window: three agents that
day were caught LATE, at land time, via a DirtyMain refusal naming files
they did not recognise; the fourth ran `git status` on its own initiative
right after the mistake, saw it within a minute, and reverted with `git
checkout --` before anything was staged. Same mistake, wildly different
blast radius -- only the TIMING of noticing differed. This hook makes
that noticing automatic.

Reuses `_agent_context.py`'s `_is_agent_context` unchanged for the same
fire-for-agent/silent-for-coordinator-or-human discriminator T-2396/T-2481
already established, verified again in both directions for this hook.
`_dirty_entries` runs `git status --porcelain` against `paths[0]` (the
PRIMARY checkout, from `_worktree_paths` -- never a linked worktree,
regardless of which directory the triggering Bash call actually ran
from); `[]` (silence) on a clean tree or any git failure. `FROB_LAND_
INTERNAL=1` exempts everything, matching `root-write-guard.py`'s own
precedent -- a land in progress legitimately dirties the primary checkout
as part of its own commit machinery.

Because `PostToolUse` cannot block a tool call that already ran (Claude
Code's hooks contract: no `decision`/`hookSpecificOutput` fields for this
event, confirmed against the official hooks reference), this hook has no
overblock failure mode at all -- the worst case is an unneeded message,
never obstructed work. `_report` names every dirtied path with its exact
one-line recovery command (`git checkout --` for a tracked change, `git
clean -fd --` for something untracked) via the universal, non-blocking
`systemMessage` field, so an agent can self-correct in the same turn
rather than diagnosing from scratch at land time. `main` reads the JSON
payload from stdin and fails open (silent exit 0) on any parse or lookup
failure. Tested end-to-end via `tests/test_hook_root_cleanliness_detector.py`,
including the same both-directions positive control T-2396/T-2481 already
established, against a fixture replicating this repo's real nested-
worktree topology AND its `.claude/worktrees/` `.gitignore` entry (omitting
the latter produces a fixture-only false positive, not a real one --
confirmed empirically against this repo's own checkout).

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
