# frob mission

Structured subagent briefing system. Creates markdown briefing files in
`.frob/missions/` with pre-assembled context. Sub-agents read the briefing,
do the work, then call `frob mission done` or `frob mission stuck`.

`.frob/` is gitignored automatically.

## Usage

```bash
# Orchestrator creates missions
frob mission new fix --file src/frob/edit/__init__.py --target replace --error "TypeError: ..."
frob mission new test --file src/frob/edit/__init__.py --target stage
frob mission new implement --file src/frob/ctx/__init__.py --target adaptive_context
frob mission new review --file src/frob/check/__init__.py

# Sub-agent completes or escalates
frob mission done <id>
frob mission stuck <id> "cannot locate symbol; tree-sitter parse fails on decorated functions"

# List pending
frob mission list
```

## Mission types

| Type | Use when |
|------|---------|
| `fix` | A specific error/traceback needs fixing. Provide `--error`. |
| `test` | A function needs tests. Provide `--target` (and optionally `--test` for a failing test name). |
| `implement` | A stub needs a body. Provide `--file` and `--target`. |
| `review` | A scope needs review. Provide `--file` or description via `--context`. |

## Mission file format

Each mission is stored at `.frob/missions/<8-char-id>.md`:

```markdown
# Mission: fix  [id: a1b2c3d4]

## Target
File: src/frob/edit/__init__.py
Symbol: replace

## Error
TypeError: 'NoneType' object is not iterable

## Context
<frob ctx output>

## Instructions
Fix exactly one error. Return a unified diff. Do not refactor.
Call `frob mission done a1b2c3d4` when complete.
Call `frob mission stuck a1b2c3d4 <reason>` if blocked.

## Escape hatch
If you cannot locate the symbol by name, use:
  frob edit src/frob/edit/__init__.py --status     # check staged patches
  frob outline src/frob/edit/__init__.py --all     # see all symbols with lines
```

The `frob ctx` output for the target symbol is embedded automatically.

## Flags for `mission new`

| Flag | Description |
|------|-------------|
| `--file FILE` | Source file the agent should work on |
| `--target SYMBOL` | Symbol (function/class) to focus on |
| `--error TEXT` | Error message to include (for `fix` missions) |
| `--test NAME` | Failing test name (for `test` missions) |
| `--context TEXT` | Additional freeform context |

## Stuck missions

`frob mission stuck <id> <reason>` moves the briefing to
`.frob/missions/stuck/<id>.md` and appends the reason. The orchestrator
can inspect these to decide whether to reassign or escalate to the user.

## Lifecycle

```
new -> .frob/missions/<id>.md
done -> file deleted
stuck -> .frob/missions/stuck/<id>.md
```

## Integration with dispatch

For parallel file-editing missions, combine with `frob dispatch`:

```bash
# Orchestrator:
frob dispatch create "fix-edit-module"
# -> gives worktree path
frob mission new fix --file src/frob/edit/__init__.py --target replace --error "..."
# -> gives mission id

# Agent works in the worktree, stages edits, marks done
# Orchestrator collects:
frob dispatch collect <dispatch-id>
```
