# frob patch

Apply a unified diff produced by a subagent, with pre-flight validation.

## Usage

```
frob patch <diff_file> [--dry-run] [--check]
```

Reads from stdin if `<diff_file>` is `-`.

`--dry-run` prints what would change without writing anything.
`--check` exits non-zero if the patch does not apply cleanly (useful in CI).

## Why it exists

Subagents return code changes as unified diffs. Applying them manually is
error-prone. `patch` validates the diff parses correctly, checks that all
target files exist, and applies atomically (all-or-nothing).

## Workflow

```
# Subagent produces a diff on stdout
frob bundle src/foo.py bar > /tmp/prompt.md
claude-haiku < /tmp/prompt.md > /tmp/fix.diff

# Validate before applying
frob patch --check /tmp/fix.diff

# Apply
frob patch /tmp/fix.diff
```

## Output

```
applying 3 hunks across 2 files:
  src/frob/stub/__init__.py  +12 -4
  tests/test_stub.py          +8 -0
done
```

## Error handling

Returns `Result[PatchResult, PatchError]`:

- `PatchError.ParseFailed` -- diff is malformed
- `PatchError.FileMissing` -- a target file referenced in the diff does not exist
- `PatchError.HunkFailed` -- context lines do not match (patch is stale)
