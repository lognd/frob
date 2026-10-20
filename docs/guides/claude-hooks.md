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
