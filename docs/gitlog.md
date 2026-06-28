# frob gitlog

Summarize git history filtered by conventional commit type and detail level.

## Usage

```bash
frob gitlog                           # user-visible changes (feat+fix), current dir
frob gitlog src/                      # same, from a specific repo root
frob gitlog --level major             # breaking changes + major version bumps only
frob gitlog --level full              # all conventional commit types
frob gitlog --level changelog         # feat+fix+breaking (release notes style)
frob gitlog --since v1.0.0            # from a tag
frob gitlog --since 2024-01-01        # from a date
frob gitlog -n 20                     # limit to 20 commits
frob gitlog --all                     # include non-conventional commits
frob gitlog --json                    # machine-readable output
```

## Detail levels

| Level | Includes |
|-------|---------|
| `major` | Breaking changes (`!`) + major version bump chores only |
| `user` (default) | `feat`, `fix`, `perf`, `revert` -- user-visible changes |
| `full` | All conventional types: feat, fix, perf, refactor, docs, test, chore, ci, build |
| `changelog` | `feat` + `fix` + breaking -- release note format |

## Conventional commit types recognized

`feat` / `fix` / `chore` / `refactor` / `perf` / `docs` / `test` / `ci` / `build` / `style` / `revert`

Commits not matching this pattern are `unknown` type and excluded by default
(include with `--all`).

## Text output

```
git log (user) since v0.0.1  --  4 commits

### Features
  91f6bdb  add frob check (C++/Rust/valgrind), frob mission, and new parsers
  b99e468  add frob check and frob ctx aggregate utilities

### Bug fixes
  2901541  always bump patch version unconditionally on upload
```

Breaking changes appear in a separate `### BREAKING CHANGES` section at the top.

## JSON output

The JSON output includes both a flat `commits` list and a `groups` dict that
maps each commit type to the commits of that type.

```json
{
  "root": ".",
  "since": "v0.0.1",
  "granularity": "user",
  "commits": [
    {
      "sha": "91f6bdb...",
      "short_sha": "91f6bdb",
      "type": "feat",
      "scope": null,
      "breaking": false,
      "description": "add frob check ...",
      "body": "",
      "tag": null
    }
  ],
  "groups": {
    "feat": [
      {
        "sha": "91f6bdb...",
        "short_sha": "91f6bdb",
        "type": "feat",
        "scope": null,
        "breaking": false,
        "description": "add frob check ...",
        "body": "",
        "tag": null
      }
    ],
    "fix": [
      {
        "sha": "2901541...",
        "short_sha": "2901541",
        "type": "fix",
        "scope": null,
        "breaking": false,
        "description": "always bump patch version unconditionally on upload",
        "body": "",
        "tag": null
      }
    ]
  }
}
```

## Agentic use

```bash
# Orient at session start
frob gitlog --level user -n 10

# Release notes
frob gitlog --level changelog --since v0.0.2

# Find what broke
frob gitlog --level full --since v0.0.1 --all
```
