# frob sync-skills

Bidirectionally sync this repo's `agents/`/`skills/` directories into
`~/.claude/agents`/`~/.claude/skills` (T-2241). Replaces Makefile's old
`sync-skills:` bash recipe -- two POSIX `for` loops copying entries in, two
more removing stale ones -- with a pure `pathlib`/`shutil` implementation
that runs identically on Linux/macOS/Windows (no shelled-out loop,
`basename`, or `[ -d ]` test).

## Usage

```
frob sync-skills [path] [--claude-dir DIR] [--force]
```

`path` is the repo root to sync from (default: `.`). `--claude-dir`
overrides the target directory (default: `~/.claude`) -- mainly useful for
testing against a temp directory rather than the real `~/.claude`. `--force`
(T-2386) overwrites a collision instead of skipping it -- see "Cooperation
across repos" below.

Output routes through `frob.render.Renderer` (docs/modules/render.md#renderer)
like every other CLI entry point in this repo, rather than bare `print`
calls -- the synced/removed entry lines and the final summary line all go
through `Renderer.for_stream(sys.stdout).line(...)`.

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

## Cooperation across repos (T-2386)

`~/.claude` is commonly shared by several frob-enabled repos. Before
T-2386, step 2 above ("removed") fired for ANY `claude_dir` entry absent
from the CURRENT repo -- including another repo's own agents/skills, or
anything you maintain by hand. Two repos syncing into the same
`~/.claude` would flap each other's entries in and out; step 1 ("synced")
also silently overwrote any pre-existing same-named destination.

The fix is a provenance manifest, `<claude_dir>/.frob-sync-manifest.json`,
keyed by each repo's resolved root path, recording which `<kind>/<name>`
entries that repo installed. Two rules follow:

- **Removal** only ever fires for an entry THIS repo's own manifest
  record says it installed, and that is now missing repo-side. An entry
  another repo installed, or one no manifest ever claimed (hand-
  maintained), is never removed, no matter what today's repo-side listing
  looks like.
- **Copy-in** refuses when the destination already exists and this repo
  does not already own it (per the manifest) -- reported as a skipped
  collision, not silently applied. `--force` overwrites the collision and
  claims ownership from then on; the default posture never overwrites
  blind.

A first sync into a hand-maintained `~/.claude` therefore deletes and
overwrites nothing. Running the same repo's sync twice in a row is a
no-op the second time (same manifest state, nothing new to sync/remove).
Manifest reuses the same guarded-write posture `scaffold/project.py`'s
`render_project`/`install_worktree_lease_hook` already establish
(`exists() -> refuse without --force`) rather than a new mechanism.

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
    collisions: tuple[str, ...]  # T-2386: existed, not owned by this repo, skipped

def sync_skills(
    repo_root: Path, claude_dir: Path, *, force: bool = False
) -> dict[str, SkillsSyncReport]
    # one SkillsSyncReport per kind ("agents"/"skills"); updates
    # <claude_dir>/.frob-sync-manifest.json with this repo's ownership (T-2386)

def run(argv: list[str]) -> None
    # frob sync-skills [path] [--claude-dir DIR] [--force] CLI entry point
```
