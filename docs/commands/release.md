# frob release

Mechanical semver from the public-API graph (`docs/modules/release.md` has
the full design). Four subcommands: `stamp`, `check`, `sync` (all three
predate this page), and `publish` (T-2242).

## frob release publish

```
frob release publish [path] [--dry-run]
```

Bumps the patch version, stamps + syncs the release, commits
`pyproject.toml`/`uv.lock`/`CHANGELOG.md`/`.frob-release.json`, pushes,
builds, and publishes -- the same net effect as the old Makefile
`upload:` recipe, in pure Python (no `shell=True`, no `bash -c`,
`python-dotenv` for `.env` instead of bash sourcing).

`path` is the repo root (default: cwd).

### `--dry-run`

Reports the version this would bump to and the files it would
touch/push/publish, without mutating anything: no version write, no
`.env` load, no git commit, no push, no build, no publish. This is the
only way this command's own migration was verified -- never a real push
or a real PyPI publish.

```
$ frob release publish --dry-run
release publish --dry-run: would bump 0.477.0 -> 0.477.1
  would commit: pyproject.toml, uv.lock, CHANGELOG.md, .frob-release.json
  would push, build, and publish
```

### A real run

```
$ frob release publish
release publish: 0.477.0 -> 0.477.1, steps: bump, stamp, sync, git-add, git-commit, git-push, uv-build, uv-publish
```

Loads `.env` (via `python-dotenv`) before the first step that could need
a secret (`uv publish`'s token) -- never before, and never logged.

## Makefile

```
upload:
	uv run frob release publish
```

## Error handling

Returns `Result[PublishReport, ReleaseError]`. Every step (bump, stamp,
sync, git add/commit/push, build, publish) maps to its own `ReleaseError`
member (`GitAddFailed`, `GitCommitFailed`, `GitPushFailed`, `BuildFailed`,
`PublishFailed`, ...) -- the sequence stops at the first failure and
reports which step failed; steps that already ran (e.g. the version bump)
are not rolled back.

## Public API

See `docs/modules/release.md#frob-release-publish-t-2242`.
