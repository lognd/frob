# frob dispatch

Branch-per-agent git worktree isolation. Each dispatch creates a fresh git
branch + worktree so agents can make commits in parallel without conflicts.
When done, the branch is rebased onto the current HEAD and fast-forward merged.

## Usage

```bash
frob dispatch create "fix-auth-module"
# -> dispatch abc12345
#    branch:   frob/dispatch/fix-auth-module-abc12345
#    worktree: .frob/worktrees/fix-auth-module-abc12345

frob dispatch list
frob dispatch collect abc12345
frob dispatch abort abc12345
```

## When to use dispatch vs. edit --stage

| Scenario | Use |
|---------|-----|
| Multiple agents edit **different files** | `frob dispatch` (full branch isolation) |
| Multiple agents edit **different functions in the same file** | `frob edit --stage` + `--commit` |
| Single agent, sequential edits | `frob edit --immediate` |

`frob dispatch` is heavier (creates a real git worktree) but gives agents a
full working git history, the ability to commit incrementally, and clean rebase
semantics. Use it when agents will make several commits or touch many files.

`frob edit --stage` is lighter (just a patch file) and works within the main
worktree. Use it when agents only need to swap out specific functions.

## Workflow

```bash
# 1. Create dispatches for each parallel agent
D1=$(frob dispatch create "implement-feature-a" | head -1 | awk '{print $2}')
D2=$(frob dispatch create "implement-feature-b" | head -1 | awk '{print $2}')

# 2. Each agent works in their worktree path
#    (shown in dispatch create output)
#    They can git commit freely inside the worktree

# 3. Collect completed work (rebase + ff-merge)
frob dispatch collect $D1
frob dispatch collect $D2

# 4. Verify
frob check src/
```

## Collection strategy

| Flag | Behavior |
|------|---------|
| `--strategy rebase` (default) | Rebase branch onto current HEAD, then fast-forward merge -- linear history |
| `--strategy merge` | `git merge --no-ff` -- preserves branch topology |

If rebase conflicts occur, `frob dispatch collect` aborts the rebase and exits
non-zero. The worktree and branch remain intact for manual resolution.

## Composing dispatch with frob edit --stage

`frob dispatch` and `frob edit --stage` compose cleanly. Patches staged inside
a worktree are scoped to that worktree -- they cannot bleed into the main repo
or into other worktrees.

**Why it's safe:** `frob edit --stage` stores patches at
`.frob/edits/<sha1-of-absolute-file-path>/`. Inside a linked worktree,
the absolute path of a file is different from its path in the main repo,
so the sha1 slug is different. The `.git` file at the worktree root is
detected by `_find_project_root`, anchoring the `.frob/edits/` directory
inside the worktree.

**Recommended combined workflow:**

```bash
# Orchestrator creates one dispatch per logical unit of work
frob dispatch create "add-feature-x"
# -> worktree at .frob/worktrees/add-feature-x-<id>/

# Agent works inside the worktree:
#   cd .frob/worktrees/add-feature-x-<id>/
#   frob ctx src/module.py Foo
#   echo "$new_impl" | frob edit src/module.py Foo --stage
#   echo "$new_helper" | frob edit src/module.py _helper --stage
#   frob edit src/module.py --commit      # atomic within the worktree
#   git add -p && git commit -m "feat: ..."
#   frob mission done <mission-id>

# Orchestrator collects after agent is done:
frob dispatch collect <dispatch-id>
```

The staging model handles concurrent edits within a single worktree (multiple
functions in the same file). The dispatch model handles concurrent edits across
different worktrees (different files, or the same file on different branches).
They do not interfere.

## State storage

Dispatch metadata is stored in `.frob/dispatch/<id>.json` (gitignored).
`.frob/` is added to `.gitignore` automatically on first use.

## List output

```
frob/dispatch/fix-auth-module-abc12345  [fix-auth-module]  branch: frob/dispatch/...
frob/dispatch/add-tests-def67890       [add-tests]         branch: frob/dispatch/...
```
