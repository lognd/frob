# Coordinator scripts (`scripts/`)

T-1863. Three small, reusable scripts that replace analyses the coordinator
loop used to re-derive by hand from inline Python, dozens of times per
session -- and got wrong twice, on both counts documented below. Each
script is plain stdlib Python (no `frob` import, so it runs under any
interpreter on `PATH`, not just the project's `uv`-managed one) and is
meant to be invoked directly, not imported as a library, though every
function is written to be testable in isolation.

## `scripts/check_summary.py`

Runs (or parses an already-captured) `frob check --json` report and prints
a severity histogram plus every error row.

WHY THIS EXISTS: `frob check --json`'s output nests severity two levels
deep -- `report["results"]` is a list of TOOL records, and severity lives
on each entry of that record's own `["diagnostics"]` list, not on the tool
record itself. Reading it one level too shallow (`record.get("severity")`)
silently returns nothing for every record, which reads as "zero errors" --
this happened twice in one session and produced two false green reports
against a red tree.

### `load_report`

<!-- frob:doc docs/guides/coordinator-scripts.md#load_report -->

Reads a `frob check --json` report from a file path argument, or from
stdin when no argument (or `-`) is given.

### `iter_diagnostics`

<!-- frob:doc docs/guides/coordinator-scripts.md#iter_diagnostics -->

Yields `(tool, diagnostic)` for every diagnostic in a parsed report. This
function IS the correct traversal
(`report["results"][i]["diagnostics"][j]`) -- every other function in this
script, and every coordinator invocation, goes through this rather than
re-deriving the nesting inline.

### `summarise`

<!-- frob:doc docs/guides/coordinator-scripts.md#summarise -->

Returns `(severity_counts, error_rows)` for a parsed report: a
`collections.Counter` keyed by severity string, and a list of
`(tool, code, file, line, message)` tuples for every `severity == "error"`
diagnostic.

### check_summary-main

<!-- frob:doc docs/guides/coordinator-scripts.md#check_summary-main -->

CLI entry point: prints `SEVERITY {...}` then `ERRORS N` then one line per
error row; exits 1 if any error diagnostic was found, 0 otherwise.

Usage:

```
uv run frob check --json > out.json && python3 scripts/check_summary.py out.json
uv run frob check --json | python3 scripts/check_summary.py
```

## `scripts/fleet_status.py`

The pre-dispatch safety check: root checkout cleanliness, every held scope
lease, and per-worktree idle age, in one shot.

WHY THIS EXISTS: dispatching onto a dirty root checkout DirtyMain-blocks
every agent that lands afterward, and a raw `git worktree remove` sweep
cannot tell a genuinely idle worktree from one a live agent is still
working in (both look "clean" to git between commits) -- both mistakes
have cost real time in this repo's history (see
`docs/guides/agent-playbook.md` section 12b). This script is the one-shot
read that answers "is it safe to dispatch, and which worktrees look idle?"
before either action.

### fleet_status-constants

<!-- frob:doc docs/guides/coordinator-scripts.md#fleet_status-constants -->

`REPO`, `WORKTREES`, and `LEASES` are the three paths every function below
resolves relative to: the repo root (derived from this script's own file
location, so it works regardless of the caller's cwd), the per-worktree
checkout directory, and the cross-worktree lease directory.

### `root_dirt`

<!-- frob:doc docs/guides/coordinator-scripts.md#root_dirt -->

Returns the `git status --short --porcelain` lines for the root checkout;
an empty list means the root is clean and safe to dispatch onto.

### `leases`

<!-- frob:doc docs/guides/coordinator-scripts.md#leases -->

Returns every held cross-worktree lease record under `.git/frob-leases/`,
parsed from its JSON file (an unreadable/malformed lease file is reported
with `worktree: "<unreadable>"` rather than raising).

### `worktrees`

<!-- frob:doc docs/guides/coordinator-scripts.md#worktrees -->

Returns `(name, seconds_since_last_commit, looks_idle)` for every
worktree under `.claude/worktrees/`. `looks_idle` is a HINT based on
commit age alone, never proof of liveness -- an agent mid-diagnosis with
nothing new to commit yet looks identical to an abandoned worktree by this
measure alone. `frob worktree sweep` (section 12b of the agent playbook)
is the authoritative, lease-aware check; this script's idle flag is for a
human/coordinator glance, not a removal decision.

### fleet_status-main

<!-- frob:doc docs/guides/coordinator-scripts.md#fleet_status-main -->

CLI entry point: prints root dirt, held leases, and worktree idle ages;
exits 1 when the root is dirty, 0 otherwise. `--idle-minutes N` (default
20) sets the idle threshold.

Usage:

```
python3 scripts/fleet_status.py [--idle-minutes N]
```

## `scripts/verify_lands.py`

Given one or more commit shas, reports whether each is a genuine ancestor
of `main` (or another `--ref`), alongside its commit subject.

WHY THIS EXISTS: a Done report's own prose claim of "landed" is not
evidence -- the only trustworthy check is `git merge-base --is-ancestor
<sha> <ref>`. Running that by hand invites the SPECIFIC failure this
script guards against: a mistyped or truncated sha that does not resolve
to any commit must never be reported the same way as a sha that resolves
but is genuinely not on `main` -- conflating "unknown" with "missing" has
reported LOST WORK for a ticket that in fact landed fine, twice in one
session. This script keeps the two outcomes lexically distinct:
`UNKNOWN-SHA` (does not resolve to any commit in this repo) versus
`MISSING` (resolves, but is not an ancestor of `--ref`).

### verify_lands-constants

<!-- frob:doc docs/guides/coordinator-scripts.md#verify_lands-constants -->

`REPO` is the repo root, derived from this script's own file location, so
every `git` call below runs against the right checkout regardless of cwd.

### `resolve`

<!-- frob:doc docs/guides/coordinator-scripts.md#resolve -->

Returns the full commit id for a sha/ref string via
`git rev-parse --verify <sha>^{commit}`, or `None` when git cannot resolve
it at all (a typo, a sha that was never fetched, garbage input).

### `is_ancestor`

<!-- frob:doc docs/guides/coordinator-scripts.md#is_ancestor -->

True when `sha` is an ancestor of `ref` per
`git merge-base --is-ancestor` -- i.e. the commit really is reachable from
`ref`, which is what "landed" means here.

### `subject`

<!-- frob:doc docs/guides/coordinator-scripts.md#subject -->

The one-line commit subject for `sha`, so a human can eyeball that the
resolved commit is the one they meant.

### verify_lands-main

<!-- frob:doc docs/guides/coordinator-scripts.md#verify_lands-main -->

CLI entry point: for every sha argument, prints `UNKNOWN-SHA <sha>` when
it does not resolve, `MISSING <sha> NOT an ancestor of <ref>` when it
resolves but is not landed, or `ON <ref> <sha> <subject>` when it is a
genuine ancestor; exits 1 if any sha was unknown or missing.

Usage:

```
python3 scripts/verify_lands.py <sha> [<sha> ...] [--ref main]
```

## Design and gate posture

Every `subprocess.run` call in these three scripts (`git`, and `frob check`
itself) is declared under a `scripts_ops` node in `design/frob.strata` with
the `exec` capability (SELFAUDIT001 -- a script that shells out with no
capability declaration is exactly the class of unaudited process-spawn
SELFAUDIT001 exists to catch).

TEST001 (unit-test coverage) is satisfied with real pytest coverage in
`tests/unit/test_coordinator_scripts.py`, not a path-class exemption:
unlike `.claude/hooks/**` (T-1838/T-1861's precedent, exempted because
those scripts run ONLY under the Claude Code dispatch harness and cannot
be meaningfully unit-tested outside it), every function here is ordinary
importable Python -- `git`/`frob` subprocess calls are monkeypatched, and
the parsing/traversal logic (`iter_diagnostics`, `summarise`, `leases`,
`worktrees`) runs against fixture data with no subprocess at all. The
hooks exemption's rationale does not transfer to this shape.
