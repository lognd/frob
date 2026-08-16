# frob sync-skills

Bidirectionally sync this repo's `agents/`/`skills/` directories into
`~/.claude/agents`/`~/.claude/skills` (T-2241). Replaces Makefile's old
`sync-skills:` bash recipe -- two POSIX `for` loops copying entries in, two
more removing stale ones -- with a pure `pathlib`/`shutil` implementation
that runs identically on Linux/macOS/Windows (no shelled-out loop,
`basename`, or `[ -d ]` test).

## Usage

```
frob sync-skills [path] [--claude-dir DIR]
```

`path` is the repo root to sync from (default: `.`). `--claude-dir`
overrides the target directory (default: `~/.claude`) -- mainly useful for
testing against a temp directory rather than the real `~/.claude`.

## What it does

For each of `agents/` and `skills/`:

1. Every `<kind>/<name>/` directory in the repo is copied (or, if it
   already exists under the target, updated in place) into
   `<claude-dir>/<kind>/<name>/`.
2. Every `<claude-dir>/<kind>/<name>/` directory with no repo-side
   counterpart is removed.

This is genuinely bidirectional, not a one-way copy: `~/.claude` is kept
IN SYNC with the repo on every run, not merely seeded from it once. A
repo with neither `agents/` nor `skills/` present is a clean no-op (the
two target directories are still created, matching the old recipe's
unconditional `mkdir -p`, but nothing is synced or removed).

## Makefile

```
sync-skills:
	uv run frob sync-skills
```

## Error handling

Filesystem errors (a permission failure, a target path that is a file
where a directory is expected, ...) propagate as an ordinary Python
exception -- there is no partial/rollback state to reconcile, since each
`<kind>/<name>` entry is synced or removed independently of every other.

## Public API

<!-- frob:describes src/frob/scaffold/_skills_sync.py::sync_skills -->
<!-- frob:describes src/frob/scaffold/_skills_sync.py::run -->

```python
# frob/scaffold/_skills_sync.py
class SkillsSyncReport(BaseModel)
    synced: tuple[str, ...]
    removed: tuple[str, ...]

def sync_skills(repo_root: Path, claude_dir: Path) -> dict[str, SkillsSyncReport]
    # one SkillsSyncReport per kind ("agents"/"skills")

def run(argv: list[str]) -> None
    # frob sync-skills [path] [--claude-dir DIR] CLI entry point
```
