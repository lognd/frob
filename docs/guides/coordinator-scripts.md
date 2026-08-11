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

### quarantine

<!-- frob:doc docs/guides/coordinator-scripts.md#quarantine -->

`QUARANTINE` is `.frob/quarantine.json`, the T-1693 quarantine circuit
breaker's own persisted store (`frob.verify._quarantine`), read here as
raw JSON so this script stays dependency-light (no `frob` package
import required) -- the same reasoning `LEASES` already applies.

`quarantine_state()` returns `("raised" | "clear" | "unknown",
undisposed_count)`. A missing file is `"clear"` (never raised). An
unreadable/malformed file, or one whose `findings` field is not a list,
is `"unknown"` -- NEVER `"clear"`, mirroring `frob.verify._quarantine`'s
own "cannot verify is never verified" rule: misreading an unknown store
as clear would tell a coordinator it is safe to dispatch when it might
not be. `undisposed_count` is the number of findings whose
`disposition` is still empty.

T-2049's own reason for existing: a raised quarantine forces every land
onto fully-synchronous verification (`_quarantine_override_ceilings`,
`docs/modules/tickets.md#quarantine-circuit-breaker-t-1693`), and prior
to this the ONLY signal was one ERROR line buried inside `frob ticket
land`'s own several-hundred-line output -- read past across four
separate land attempts in a real incident that cost roughly an hour of
fleet-wide land throughput over two unused imports. `fleet_status.py`
is the place a coordinator already reads before dispatching a wave, so
`main()` now prints this state unconditionally, before LEASES/
WORKTREES, rather than adding a new command nobody would know to run.

### `ticket_lease`

<!-- frob:doc docs/guides/coordinator-scripts.md#ticket_lease -->

T-2133. The single live lease record for one ticket id
(`.git/frob-leases/<id>.json`), read directly rather than filtering
`leases()`'s full enumeration -- `None` if no lease file exists,
`{"ticket_id": ..., "worktree": "<unreadable>"}` on malformed JSON
(mirroring `leases()`'s own defensive shape; a lease file is
peer-writable, T-0780).

This is the direct fix for T-2133's own first incident: a coordinator
dispatched T-2114 believing its lease "should be free now" -- a belief
formed without ever reading `.git/frob-leases/T-2114.json` directly --
while another worktree still held it, mid-implementation, with its own
Done report already written. `ticket_lease` is the one-call answer that
makes skipping this check unnecessary.

### `ticket_frontmatter_on_main`

<!-- frob:doc docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main -->

`{"state": ..., "scope": [...]}` parsed from `main:tickets/<id>/
ticket.md`'s YAML frontmatter via `git show` plus a narrow hand-rolled
parse (no `import yaml` -- this script stays plain-stdlib, matching its
module docstring's contract), or `None` if the ticket does not exist on
`main` at all.

This is deliberately the STATIC, main-committed half of a scope
comparison, not the live one -- `main:tickets/<id>/ticket.md`'s `scope:`
field can be stale the moment a worktree calls `frob ticket scope`
without having landed yet. T-2133's own second incident: a coordinator
read this file directly, twice, believing it WAS the ticket's live
scope -- once nearly releasing a healthy lease, once asking an agent to
redo a scope-narrowing it had already done on its own branch.
`ticket_readiness` below is what actually compares this against the
live lease.

### `worktrees_touching_ticket`

<!-- frob:doc docs/guides/coordinator-scripts.md#worktrees_touching_ticket -->

Names of live worktrees whose branch has an unlanded commit (`git log
main..HEAD -- tickets/<id>/`) touching a given ticket's own ticket
directory -- the mechanical version of the hand-inspection T-2114's
incident required: discovering the ticket was already implemented,
evidenced, and Done-reported on a sibling branch only by manually
reading that branch's own commit log and running a process check.

### `ticket_readiness`

<!-- frob:doc docs/guides/coordinator-scripts.md#ticket_readiness -->

T-2133's actual answer to "given T-####, is it dispatchable right now?" --
combines the three functions above into one dict: `lease`, `main`
(state/scope on `main`), `scope_diverges` (`True` when a live lease's
scope differs from `main`'s declared scope -- the single highest-value
signal this ticket exists to add), `worktrees_with_commits`, and
`dispatchable` (`False` whenever a live lease is held, another worktree
already carries commits for this ticket, or `main` shows a
`done`/`dropped`/`in-progress` state; `True` otherwise).

### `_ticket_readiness_lines`

<!-- frob:doc docs/guides/coordinator-scripts.md#_ticket_readiness_lines -->

T-2172 (ARCH001/ARCH103 split). Renders one `TICKET <id>`
readiness block (lease, main state/scope, scope divergence,
sibling-branch commits, final verdict) as plain text lines -- the
pure-compute half of what used to be a single function that mixed I/O,
string-formatting, and 4 decision points in one body. No `print` call
anywhere in this function.

### `_print_ticket_readiness`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_ticket_readiness -->

Prints `_ticket_readiness_lines`'s rendered block and returns
`readiness["dispatchable"]` -- the I/O-only half of the same split, so
neither half re-triggers the mixed-concern signal alone.

### `_print_fleet_report`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_fleet_report -->

Prints the ROOT/QUARANTINE/LEASES/WORKTREES sections `main` used to
print inline, taking `dirt` (already computed by `main`) and
`idle_seconds` as arguments -- the other half of `main`'s ARCH001/
ARCH103 decomposition, alongside `_print_ticket_readiness` above.

### fleet_status-main

<!-- frob:doc docs/guides/coordinator-scripts.md#fleet_status-main -->

CLI entry point: parses `--idle-minutes`/`--ticket`, then (T-draft-
354a6b64) delegates the actual printing to `_print_ticket_readiness`
(when `--ticket` is given -- printed FIRST, ahead of the general
report, so "is T-#### dispatchable" is the first thing read) and
`_print_fleet_report`; exits 1 when the root is dirty OR (T-2133) a
given `--ticket` is not dispatchable. `--idle-minutes N` (default 20)
sets the idle threshold. The quarantine line does not itself change the
exit code -- it is a visibility fix, not a new dispatch-refusal gate.

Usage:

```
python3 scripts/fleet_status.py [--idle-minutes N] [--ticket T-####]
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
