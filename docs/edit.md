# frob edit

Symbol-level file editing with a staging layer for concurrent-agent safety.

## Usage

```bash
frob edit FILE SYMBOL                  # read-only: show source + line range
frob edit FILE SYMBOL --stage          # stage replacement from stdin
frob edit FILE --commit                # apply all staged patches atomically
frob edit FILE --status                # show pending staged patches
frob edit FILE SYMBOL --immediate      # immediate replace (single-agent only)
```

## Why staging?

When multiple agents edit different functions in the same file simultaneously,
naive read-modify-write races cause one agent to silently overwrite another's
changes. The staging model eliminates this:

- `--stage` writes only a `.frob/edits/<hash>/SYMBOL.patch` file. The source
  file is untouched.
- `--commit` acquires an exclusive lock, re-parses the file fresh, applies all
  pending patches one at a time (re-parsing between each to absorb line-number
  shifts), then writes once via `os.replace` (atomic).
- Multiple agents staging concurrently write to different patch files -- no
  contention possible.

## Concurrent-agent workflow

```bash
# Each agent (independently, in parallel):
frob ctx src/module.py MyFunc          # get context
# ... produce new_source ...
echo "$new_source" | frob edit src/module.py MyFunc --stage

# After ALL agents have staged, one commit (orchestrator or last agent):
frob edit src/module.py --commit
```

## Single-agent workflow

```bash
echo "$new_source" | frob edit src/module.py MyFunc --immediate
```

## Read-only inspection

```bash
frob edit src/module.py MyFunc
# Output:
# # MyFunc  [L42-L58]
# def MyFunc(x: int) -> Result[int, MyError]:
#     ...
```

Useful for isolating a function before deciding how to edit it, without
reading the entire file.

## Symbol notation

| Notation | Matches |
|---------|---------|
| `foo` | Top-level function or class named `foo` |
| `MyClass` | Class named `MyClass` (including all methods) |
| `MyClass.method` | Method `method` inside `MyClass` |

## Staging internals

Patch files are stored at `.frob/edits/<sha1-of-path>/<SYMBOL>.patch` in a
compact 3-line format:

```
<staged_at_unix_timestamp>
<symbol>
<new source verbatim>
```

If two agents stage the same symbol, the one with the **newest `staged_at`**
wins at commit time. The other is logged as a skipped duplicate.

## Patch commit semantics

1. Acquire exclusive `fcntl.LOCK_EX` on `FILE.froblock`.
2. Load all `.patch` files; deduplicate by symbol (newest wins).
3. For each patch: re-parse file in memory, locate symbol by name, splice.
4. Write result via `os.replace` (atomic on same filesystem).
5. Delete all `.patch` files.

A crash during step 4 leaves the original file intact; patches remain and can
be retried with `--commit`.

## Status check

```bash
frob edit src/module.py --status
# Output:
#   MyFunc
#   MyClass.helper
```

## Interaction with frob dispatch

When an agent is working inside a `frob dispatch` worktree, `frob edit --stage`
stores patches inside that worktree -- not in the main repo. This is automatic
and requires no configuration.

**How it works:** `_find_project_root` walks parent directories looking for
`.git`. In a linked worktree, `.git` is a file (not a directory) at the
worktree root. Python's `.exists()` returns `True` for files, so the worktree
root is correctly detected as the project root. Patch files land in
`<worktree>/.frob/edits/<slug>/`, isolated from all other worktrees and the
main repo.

**Consequence:** two agents in different dispatch worktrees can both stage
patches to "the same file" (same relative path) without any collision. Each
worktree gets its own patch directory keyed to its own absolute path. When the
orchestrator collects via `frob dispatch collect`, git's rebase/merge handles
combining the results.

**Recommended combined workflow:**

```bash
# Within a dispatch worktree:
frob edit src/mod.py Foo --stage     # patches go to <worktree>/.frob/edits/
frob edit src/mod.py Bar --stage     # same worktree, different patch file
frob edit src/mod.py --commit        # applies both atomically to worktree's file
git commit -m "feat: ..."            # normal git commit inside worktree
# frob mission done <id>
```

## Flags

| Flag | Description |
|------|-------------|
| `--stage` | Stage replacement from stdin (concurrent-safe) |
| `--commit` | Apply all staged patches for FILE atomically |
| `--status` | List symbols with pending staged patches |
| `--immediate` | Lock + write now; skip staging (single-agent only) |
| `--replace` | Alias for `--immediate` (legacy) |
