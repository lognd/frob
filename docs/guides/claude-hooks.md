# Claude Code hooks

Versioned copies of the user-level hooks live in `scripts/claude-hooks/`.

## frob-suggest

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

## Installing

`scripts/claude-hooks/frob_hook_settings.py` provides `install(settings, script)`
and `uninstall(settings)`. Entries are marked `# frob-owned:frob-suggest`;
install is idempotent and collapses duplicate registrations; uninstall removes
only marked (or legacy frob-suggest.py) entries. Writes are atomic and keep a
`.frob-bak` backup.

## frob agent (sync, status, uninstall)

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

### Adding another agent

Add one module under `crates/frob/src/agent/` implementing `Emitter` (target
paths, render, register/unregister) and one line in `emitters()`. The engine,
verbs and manifest do not change; `engine.rs` tests prove this with a fake emitter.
