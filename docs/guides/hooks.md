# Hooks

Status: current
Owner: frob
Decisions: none
Audience: user

Hooks that keep frob in the loop: Claude Code hooks and the agent manifest, and the freshness hooks that keep the local ticket ledger current.

## Claude Code hooks

Versioned copies of the user-level hooks live in `scripts/claude-hooks/`.

### frob-suggest

Nudges toward the frob equivalent of a raw command (PreToolUse, Bash|Edit).

- First matching command is blocked once; an exact re-run is allowed; the
  third identical attempt in a session is blocked again.
- Escape hatch: prefix a command with `FROB_SUGGEST_ALLOW=<rule-id> `. It
  suppresses only that rule. For Edit, set `FROB_SUGGEST_ALLOW=<rule-id>` in
  the environment.
- The old blanket `FROB_SUGGEST_ACK=1` is retired: it is ignored and a
  one-line notice is printed.
- Every block, allow, and ignored-ack decision is appended to
  `.frob/telemetry.jsonl` as a `kind=hook` row (`hook`, `rule`, `agent`,
  `shape`, `verb`, `subverb`, `decision`, `attempt`).
- A repeated `tool_use_id` does not increment the attempt counter, so a
  double registration cannot overcount.

### frob agent hook

`frob agent hook <event>` answers Claude Code hooks natively: it reads the hook JSON on stdin and
prints the reply JSON as its only stdout line. Register it as `frob --text agent hook <event>` (the
default piped format is the verb envelope, not the reply). Events: `pre-bash`, `pre-read`,
`session-start`, `pre-compact`, `user-prompt`, `stop`.

- `pre-read` denies a whole-file Read of a file over `[agent] hook_read_max_bytes` (default 200000)
  and tells the agent to pass `offset` and `limit`.
- `pre-bash` denies commands matching `[agent] hook_heavy_commands` with the route
  `frob agent heavy -- <cmd>`, and appends `| head -n [agent] hook_bash_max_lines` to unbounded
  output commands (`cat`, `find`, `git log`, `git diff`, `grep -r`, `ls -R`) that are not piped.
- `session-start` and `pre-compact` carry the `frob agent brief` text; `user-prompt` carries a
  one-line active-ticket reminder; `stop` reminds that the lease is still live (never blocks).
- Fail open: unreadable stdin, bad JSON, a missing repo or an unreadable `frob.toml` gives the
  reply `{}` and a warning on stderr, exit 0. The agent is never blocked by the hook itself.

### Installing

`scripts/claude-hooks/frob_hook_settings.py` provides `install(settings, script)`
and `uninstall(settings)`. Entries are marked `# frob-owned:frob-suggest`;
install is idempotent and collapses duplicate registrations; uninstall removes
only marked (or legacy frob-suggest.py) entries. Writes are atomic and keep a
`.frob-bak` backup.

### frob agent (sync, status, uninstall)

`frob agent sync|status|uninstall --agent claude|all` installs the tracked,
agent-neutral manifest into an agent's home. Claude is the only emitter today.

- Manifest: `[agent]` in `frob.toml`. `items` maps `<kind>:<name>` (kind is
  instruction, hook, agent, skill or support) to a repo path; `hooks` lists
  `<name>:<Event>:<matcher>` registrations. Repo is canonical; nothing is ever
  synced home -> repo.
- Engine (`crates/frob/src/agent/engine.rs`) owns atomic temp+rename writes,
  `.frob-bak` backups, the do-not-edit banner, idempotence, drift detection,
  reversibility and the stale guard. A state file `<home>/.frob-agent.json`
  (blake3 hashes) lets uninstall remove pristine files and keep user-edited ones.
- Stale guard: a worktree source equal to the merge-base blob while base has
  moved on is refused (`E-AGENT-STALE`) unless allowed.
- `status` exits 1 on drift; `frob doctor` surfaces the same drift as a warning.
- Claude registration is in settings.json with the `# frob-owned:<name>` marker
  (same semantics as `frob_hook_settings.py`): only frob-owned entries are touched.
- `--home` overrides the target home (default `$HOME/.claude`); tests use tmp dirs.

#### Adding another agent

Add one module under `crates/frob/src/agent/` implementing `Emitter` (target
paths, render, register/unregister) and one line in `emitters()`. The engine,
verbs and manifest do not change; `engine.rs` tests prove this with a fake emitter.

## Freshness hooks

Keep the local view of the ticket ledger current without remembering to run anything
([distributed-tickets.md](../design/frob/distributed-tickets.md) section 5.4, and
[ticket-branch.md](ticket-branch.md) for the ledger branch it refreshes).

### Git hooks

`frob init` installs `post-checkout` and `post-merge` hooks in the repository's common hooks
directory. Each carries one marked block that runs `frob refresh --background --quiet` and returns at
once. The block is skipped when `CI` or `FROB_SYNC_INNER` is set (frob's own pushes) and while a rebase
is in progress, and it never fails the git operation. There is deliberately no `pre-push` hook.

- Idempotent: rerunning `frob init` leaves an up-to-date hook byte-identical.
- Your own hook lines are kept; frob only edits the block between its two marker lines.
- Reversible: `frob init --remove-hooks` strips the block and deletes a hook file frob alone wrote.
- A custom `core.hooksPath` is not followed; copy the block there by hand.

### Agent session start

`frob agent sync` registers every `hook:` item declared under `[agent]` in `frob.toml`. This repository
declares `scripts/claude-hooks/frob-refresh.sh` on `SessionStart`: it runs `frob refresh --quiet` in the
foreground under a 3 second budget and prints what it finds to the agent.

```toml
[agent]
items = ["hook:frob-refresh = scripts/claude-hooks/frob-refresh.sh"]
hooks = ["frob-refresh:SessionStart:"]
```

### Loops and cron

Run `frob refresh --quiet` and branch on its exit code. `CI` disables background sync, so the hooks do
nothing in a pipeline.

```cron
*/10 * * * * cd /path/to/repo && frob refresh --quiet
```
