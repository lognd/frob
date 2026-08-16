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
checkout directory, and the cross-worktree lease directory. `TICKETS_DIR`
(T-2182) is the fourth: the live per-ticket ledger directory
(`tickets/<id>/ticket.md`), read directly from disk for `rotting_tickets`.

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
`docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693`), and prior
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

### lease-classification-constants

<!-- frob:doc docs/guides/coordinator-scripts.md#lease-classification-constants -->

`_LEASE_TTL_SECONDS` mirrors `frob.tickets._leases.LEASE_TTL_SECONDS`
(6 hours) exactly, duplicated in plain form (this script's own no-`frob`-
import contract) rather than imported.

### `_lease_age_seconds`

<!-- frob:doc docs/guides/coordinator-scripts.md#_lease_age_seconds -->

Seconds elapsed since a lease record's own `recorded_at` field, or `None`
if unparseable -- mirrors `frob.tickets._leases.lease_age_seconds`.

### `_scan_for_live_worktree_process`

<!-- frob:doc docs/guides/coordinator-scripts.md#_scan_for_live_worktree_process -->

The first live pid whose `/proc/<pid>/cwd` resolves to a given worktree
path, or `None` -- mirrors `frob.tickets._leases.scan_for_live_worktree_
process`'s own `/proc` walk (a distinct question from `land_lock_holder_
pids` above: "is anything cwd'd here" vs "who holds `land.lock` open").

### `lease_classification`

<!-- frob:doc docs/guides/coordinator-scripts.md#lease_classification -->

T-2222: classifies one held lease record as `"live"`, `"reclaimable"`, or
`"root-resident"` -- the missing distinction that let a raw lease file
COUNT read as a live-agent count (measured: 6 leases, only 4 live
agents). Mirrors `frob.tickets._leases.lease_staleness_reason`'s own four
shapes (path-gone, ticket-gone, ticket-terminal, holder-dead) plus one
addition: a lease whose `worktree` resolves to this repo's own root
reports `"root-resident"` -- structurally unreclaimable (a live
coordinator/agent shell is routinely cwd'd into the shared root, so the
ordinary liveness scan would read it as permanently live) but also never
counted as a real dispatched agent. Derived entirely from the record's
own fields and `main`'s ticket state -- never a ticket-id allowlist.

### `live_lease_count`

<!-- frob:doc docs/guides/coordinator-scripts.md#live_lease_count -->

How many of a list of held lease records classify as `"live"` -- the
number a concurrency guidance clause must be computed from, never
`len(leases())`.

### `_matches_any_scope_glob`

<!-- frob:doc docs/guides/coordinator-scripts.md#_matches_any_scope_glob -->

`fnmatch.fnmatch`-based glob match against a list of scope patterns --
the same glob semantics `frob ticket scope`'s own globs use.

### `worktrees_touching_ticket`

<!-- frob:doc docs/guides/coordinator-scripts.md#worktrees_touching_ticket -->

Names of live worktrees whose branch has an unlanded commit that, in that
SAME commit's own diff, BOTH touches the given ticket's own
`tickets/<id>/` directory AND touches at least one file matching its
`scope_globs` argument -- the mechanical version of the hand-inspection
T-2114's incident required: discovering the ticket was already
implemented, evidenced, and Done-reported on a sibling branch only by
manually reading that branch's own commit log and running a process
check.

T-2181 (T-2179 residue): correlation was originally computed at the
WHOLE-BRANCH level -- "does any commit touch the ticket dir" and "does
the whole branch diff touch scope" as two independent questions -- which
still let two unrelated commits on the same branch (one bookkeeping edit
to `tickets/<id>/`, one real-work commit for a DIFFERENT ticket that
happens to touch a shared scope-glob file) produce a false "already
implemented" verdict; measured for real against `--ticket T-2114`
(`t-2107`, `t2049-series`, each implementing a different ticket that
shares a scope file). Correlation now runs PER COMMIT (`git show
--name-only` on each commit that itself touches `tickets/<id>/`), so a
single commit must carry both signals together.

**T-2172 follow-up (precision fix):** the original version reported ANY
worktree with a `tickets/<id>/`-touching commit as "already
implemented", with no scope check at all. Real incident: `--ticket
T-2114` printed seven unrelated branches, none of which had implemented
anything -- T-2114 had briefly collided with a different id before being
renumbered to T-2140, so every branch's hit was collision-recovery
ledger churn (`tickets/T-2114/ticket.md` edits), never real code in
T-2114's own scope. Requiring a scope-glob match as well as the ticket-
directory correlation fixes this: an empty `scope_globs` argument (no
known scope to check against) now reports empty rather than falling
back to the old, looser behavior.

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

### `effective_scope`

<!-- frob:doc docs/guides/coordinator-scripts.md#effective_scope -->

T-2180. The scope glob list a ticket is actually working under right
now: its live lease's `scope` if a lease is held, else `main`'s declared
scope, else `[]`. Shared by `scope_intersections` so a pairwise
comparison never compares a stale `main`-only scope against a sibling's
live, narrowed-in-worktree one.

### `_globs_overlap`

<!-- frob:doc docs/guides/coordinator-scripts.md#_globs_overlap -->

T-2180. Whether two scope globs can ever match the same path: exact
equality, or one side being a literal path (no wildcard character) that
the other's glob matches via `fnmatch.fnmatch`. Deliberately conservative
-- never claims an overlap it cannot demonstrate.

### `scope_intersections`

<!-- frob:doc docs/guides/coordinator-scripts.md#scope_intersections -->

T-2180. PAIRWISE scope-glob intersection across a list of ticket ids,
using each ticket's effective scope, plus a check of each requested
ticket's effective scope against every OTHER currently held lease -- so
a coordinator can vet a whole wave for contention (against itself and
against in-flight work) before dispatching it, in one call. Measured
need: a five-ticket docs series all scoped to `docs/modules/tickets.md`,
then T-1748 and T-1780 both claiming the same file -- the second
collision hard-refused T-1780 at `start`, with no override, after the
dispatch had already happened.

### `_parse_ps_cpu_time`

<!-- frob:doc docs/guides/coordinator-scripts.md#_parse_ps_cpu_time -->

T-2180. Parses `ps`'s own `TIME` column (`[[dd-]hh:]mm:ss`) into total
whole seconds; returns 0 on anything unparseable.

### `land_process_rows`

<!-- frob:doc docs/guides/coordinator-scripts.md#land_process_rows -->

T-2180. Every live process whose argv contains a `ticket land`
invocation, parsed from `ps -eo pid,etimes,time,args`'s structured
columns (pid, elapsed seconds, cumulative CPU time, argv) -- the raw
per-PROCESS table a single real land fans out across (bash wrapper,
`timeout`, `uv run`, the python process itself). `land_invocations`
collapses this to distinct invocations.

### `land_invocations`

<!-- frob:doc docs/guides/coordinator-scripts.md#land_invocations -->

T-2180. Distinct `frob ticket land` invocations, keyed on the ticket id
parsed from each process row's own argv (the id is a POSITIONAL
argument -- `frob ticket land T-#### --worktree ...` -- there is no
`--ticket` flag on this subcommand) -- the fix for `ps aux | grep -c
"frob ticket land"` overcounting by roughly 4x (the bash wrapper,
`timeout`, `uv run`, and the real python process all match the same
grep). Each entry reports pids, elapsed seconds (MAX across the row
group), and CPU time (MAX across the group) -- content alone cannot
distinguish a live land from a dead attempt's residue (a killed land's
staged diff is byte-identical across retries), but CPU time
discriminates immediately.

**T-2193 fix**: an earlier version looked for a `--ticket T-####` FLAG,
which does not exist on `land`'s own argparse usage, so it matched
nothing against a real land and every row fell back to a
`ticket_id=None` singleton -- reported live as 13 rows for ONE real
land. Rows with no parseable ticket id are now DROPPED entirely, not
reported as their own invocation -- there is nothing to deduplicate an
uncorrelated row against, so it is process-table noise (e.g. a
coordinator's own wait-loop shell whose command line merely contains
the text), never evidence of a land.

### `land_lock_holder_pids`

<!-- frob:doc docs/guides/coordinator-scripts.md#land_lock_holder_pids -->

T-2180. Live pids that currently hold `.frob/land.lock` open, found by
scanning `/proc/<pid>/fd/*` for a symlink resolving to the lock's own
absolute path -- NOT the pid recorded inside the lock file's own JSON
(pids are reused) and NOT the lock file's modification age (a legitimate
land genuinely exceeds 1500s under load). The kernel releases a `flock`
the instant its holder dies, so this is a live, race-free liveness
check, not an inference. `proc` is injectable for tests.

### `host_load`

<!-- frob:doc docs/guides/coordinator-scripts.md#host_load -->

T-2180. `(1-minute load average, MemAvailable kb)` read from
`/proc/loadavg` and `/proc/meminfo`'s own structured fields, never from
parsing `free`/`uptime`'s rendered output (format varies by version and
locale). Reads `MemAvailable`, not `MemFree` -- a busy-but-healthy Linux
host commonly shows `MemFree` near 0 with most memory held as
reclaimable page cache, so reading `MemFree` would raise a false alarm
on every busy host. Returns `None` (never a fabricated zero) when either
`/proc` file is missing or unparseable.

### `_land_status_lines`

<!-- frob:doc docs/guides/coordinator-scripts.md#_land_status_lines -->

T-2180 (ARCH103 split, same precedent as `_ticket_readiness_lines`).
Renders the LANDS/LAND LOCK/LOAD block as plain text lines from
already-computed inputs -- the pure-compute half, no `print` call, so
`_print_land_status` stays I/O-only. T-2222: the LOAD line's own
concurrency guidance clause is computed from the LIVE lease count
(`live_lease_count`), never the raw `len(leases())` -- both are shown
(`"N live lease(s) (M total)"`) so a reclaimable/root-resident lease is
never silently read as a live agent.

### `_print_land_status`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_land_status -->

T-2180. Prints the LANDS section: `land_invocations` (ticket id, pids,
elapsed, cpu), `land.lock` holder liveness, and a LOAD line
(`host_load`'s load average and available memory, plus the live/total
held-lease counts, T-2222) against this host's recorded 3-4 concurrent
agent operational guidance. Printed unconditionally inside
`_print_fleet_report`, in the standing report a coordinator already
runs -- not behind a separate command (the "automatic over commands"
rule). Six concurrent agents against the documented cap went unnoticed
on this host until someone
checked `ps`/`free` by hand; this line is where that check now lives.

### `_rot_day_thresholds`

<!-- frob:doc docs/guides/coordinator-scripts.md#_rot_day_thresholds -->

T-2182. Per-priority rot-day thresholds from `frob.toml`'s `[tickets]`
table, defaulting to `_ROT_DAYS_DEFAULT` (critical=3, high=7, medium=30,
low=90) -- mirrors `frob.gates._tickets_gate._tick004_rot_thresholds`
exactly, duplicated in plain-dict form since importing the `frob`
package would defeat this script's own "runs under any interpreter on
PATH" contract.

### `_parse_ticket_ledger_file`

<!-- frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_file -->

T-2182. `{"id", "state", "priority", "tier", "created"}` hand-parsed
directly from a `tickets/<id>/ticket.md` file on disk (never `git show
main:...` -- the live, uncommitted ledger is what a dispatch decision
actually depends on). `None` if the file is unreadable or any required
field is missing.

### `rotting_tickets`

<!-- frob:doc docs/guides/coordinator-scripts.md#rotting_tickets -->

T-2182. Every QUEUED/PLANNED ticket under `TICKETS_DIR` (excluding
`tickets/archive/**`) whose priority-specific rot-day threshold has been
crossed since its own `created` date -- derived entirely from the
ledger's own structured fields compared against configured thresholds,
never by parsing `frob check`'s rendered TICK004 text. Mirrors
`_tick004_queue_rot`'s own selection exactly. Each entry carries `tier`
so a caller can distinguish a rotting leaf ticket (needs dispatch) from
a rotting epic/story (needs decomposition).

### `_print_ticket_rot`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_ticket_rot -->

T-2182. Prints the TICKET ROT section: `rotting_tickets`'s count, split
under two headings naming the required action -- 'NEEDS DISPATCH' for
`tier=ticket`, 'NEEDS DECOMPOSITION' for `tier=epic`/`tier=story`.
Epics are NOT exempted, only reported under their own action heading
(measured incident: 10 of 15 rotting tickets were epics, 1 a story, only
4 leaf tickets -- one undifferentiated count told a coordinator to do
something impossible for two thirds of the set, which is why the alarm
read as noise for a whole session). Printed unconditionally inside
`_print_fleet_report`; TICK004 already fires in `frob check`'s gate
layer but sat as 11 lines inside a 19-error list there.

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

Prints the ROOT/LANDS/TICKET ROT/QUARANTINE/LEASES/WORKTREES sections
`main` used to print inline, taking `dirt` (already computed by `main`)
and `idle_seconds` as arguments -- the other half of `main`'s ARCH001/
ARCH103 decomposition, alongside `_print_ticket_readiness` above. T-2180
added the LANDS section (`_print_land_status`) between ROOT and
QUARANTINE; T-2182 added TICKET ROT (`_print_ticket_rot`) right after
LANDS. T-2222: the LEASES section header now shows the live count
alongside the raw total, and each row prints its own `lease_
classification` verdict (`live`/`reclaimable`/`root-resident`) next to
the ticket id and worktree name.

### `_print_all_ticket_readiness`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_all_ticket_readiness -->

T-2180 (ARCH103 split). Prints `_print_ticket_readiness` for every given
`--ticket` id in order, returning `True` only if all are dispatchable --
`main`'s own multi-ticket loop, pulled out so `main` stays a thin
sequence of calls.

### `_print_scope_intersections`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_scope_intersections -->

T-2180 (ARCH103 split). Prints `scope_intersections`'s own count and
each colliding pair -- `main`'s own 2+-`--ticket` branch, pulled out
alongside `_print_all_ticket_readiness` above.

### fleet_status-main

<!-- frob:doc docs/guides/coordinator-scripts.md#fleet_status-main -->

CLI entry point: parses `--idle-minutes`/`--ticket` (repeatable, T-2180),
then (T-draft-354a6b64) delegates the actual printing to
`_print_ticket_readiness` (once per given `--ticket` -- printed FIRST,
ahead of the general report, so "is T-#### dispatchable" is the first
thing read) and `_print_fleet_report`; exits 1 when the root is dirty OR
(T-2133) any given `--ticket` is not dispatchable. When 2+ `--ticket`
values are given, also prints `scope_intersections` across the whole
set (T-2180) -- every pairwise and lease-external scope collision, so a
coordinator can vet a wave for contention before dispatching it.
`--idle-minutes N` (default 20) sets the idle threshold. The quarantine
line does not itself change the exit code -- it is a visibility fix, not
a new dispatch-refusal gate.

Usage:

```
python3 scripts/fleet_status.py [--idle-minutes N] [--ticket T-#### [--ticket T-#### ...]]
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
