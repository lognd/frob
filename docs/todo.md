# frob todo

Persistent cross-session TODO tracker. Items survive process restarts and context
resets. Stored at `.frob/todo.md` (gitignored).

## Usage

```bash
frob todo add "reviewer flagged god class in check/__init__.py"
frob todo add "add valgrind integration test for cpp check"

frob todo list          # pending items only
frob todo list --all    # include completed

frob todo done 1        # mark #1 complete
frob todo remove 2      # delete #2 permanently
frob todo clear-done    # remove all completed items
```

## Why use this

Agents start each session with no memory of prior work. `frob todo` gives
orchestrators and agents a lightweight shared notepad that persists across
sessions without reading any source files.

Typical uses:
- Tracking blockers flagged by sub-agents that need future attention
- Recording architectural decisions for the next session
- Cross-agent handoff notes ("agent A finished dispatch, agent B needs to add tests")

## Storage format

`.frob/todo.md` is a human-readable markdown file:

```markdown
# frob todo

- [ ] [#1] reviewer flagged god class in check/__init__.py
- [ ] [#2] add valgrind integration test for cpp check
- [x] [#3] fix dispatch --onto rebase ordering
```

IDs are monotonically increasing integers. Completed items are marked `[x]`
and hidden from `frob todo list` (shown with `--all`).

## Integration with sessions

At the start of an orchestrator session:

```bash
frob todo list   # see what's pending from last session
```

At the end:

```bash
frob todo add "next: write system tests for frob dispatch collect"
```
