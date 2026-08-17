# Coordinator scripts (`scripts/`)

T-1863. Three small, reusable scripts that replace analyses the coordinator
loop used to re-derive by hand from inline Python, dozens of times per
session -- and got wrong twice, on both counts documented below. Each
script is plain stdlib Python (no `frob` import) and is meant to be
invoked directly, not imported as a library, though every function is
written to be testable in isolation.

**Invocation (T-2236): `uv run python scripts/<name>.py`, not bare
`python3 scripts/<name>.py`.** These scripts have no `frob` import, but
that does NOT mean they run under any interpreter on PATH -- this
project's own `requires-python = ">=3.11"` (`pyproject.toml`) is not
guaranteed to be what a bare `python3` resolves to (a fresh clone, CI, or
an operator's own machine can have an older one on PATH; the exact
incident this fixes: `python3 scripts/fleet_status.py` broke with a raw
`ImportError: cannot import name 'UTC' from 'datetime'` the moment a
legal 3.11 feature landed, on a box whose `python3` was 3.10.12). `scripts/
fleet_status.py` and `scripts/frob-telemetry-hook` -- the two that use a
3.11+-only feature -- both start with a call to `scripts/_require_python.
require_python`, so running either one under an older interpreter now
prints the required version, the version found, and this exact corrected
invocation, and exits non-zero, instead of a raw traceback. `uv run
python ...` guarantees the project's own declared minimum; bare `python3`
never did.

## `scripts/_require_python.py`

T-2236. The shared interpreter-version guard `scripts/fleet_status.py`
and `scripts/frob-telemetry-hook` both call as their own first statement
(before any import that only works on the project's required version).
This module itself must run under ANY `python3` on PATH -- that is the
whole point -- so it avoids `tomllib` (itself 3.11+) and any newer
syntax, reading `requires-python` from `pyproject.toml` via a minimal
regex instead of a TOML parser.

### `require_python`

<!-- frob:doc docs/guides/coordinator-scripts.md#require_python -->

Exit(1) with the required version, the version found, and the correct
`uv run python ...` invocation if the running interpreter is older than
`pyproject.toml`'s own `requires-python`; a silent no-op on a supported
interpreter (invisible on the happy path) AND when the requirement
cannot be determined at all (fails OPEN, never blocks a script it cannot
evaluate).

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

### `_expand_scope_globs_to_paths`

<!-- frob:doc docs/guides/coordinator-scripts.md#_expand_scope_globs_to_paths -->

T-2225. Expands scope glob patterns (e.g. `src/frob/**`) against the
real filesystem, returning the resolved absolute path of every matched
file -- the mechanism that lets a scope collision be detected at the
RESOLVED-FILE level, never by comparing glob text. A pattern ending in a
bare `**` also tries `<pattern>/*`, since pathlib's own `**` semantics
match directories recursively but not the files inside the deepest one
without a further path segment.

### `scope_lease_collisions`

<!-- frob:doc docs/guides/coordinator-scripts.md#scope_lease_collisions -->

T-2225. Which OTHER held leases collide with a ticket's own effective
scope at the resolved-file level, restricted to leases `lease_
classification` (T-2222, reused not re-implemented) calls `"live"` -- a
reclaimable or root-resident lease is not actually held by anyone and
never counts as a collision. Fixes the measured incident: two tickets
were dispatched whose scope files (`src/frob/app/config.py`, `src/frob/
tickets/_land.py`) were already held by another agent's LIVE lease, and
the old readiness answered `lease: none` / `dispatchable: True` for both
because it only ever asked "does THIS ticket hold a lease", never
"does some OTHER live lease already cover the files it needs".

### `_scope_diverges_from_lease`

<!-- frob:doc docs/guides/coordinator-scripts.md#_scope_diverges_from_lease -->

T-2213 (ARCH001 split off `ticket_readiness`). `True` when a live lease's
`scope` differs from `main`'s declared scope -- the single highest-value
signal `ticket_readiness` exists to add.

### `_ticket_dispatchable`

<!-- frob:doc docs/guides/coordinator-scripts.md#_ticket_dispatchable -->

T-2213 (ARCH001 split off `ticket_readiness`). The `dispatchable` verdict
predicate: `False` whenever a live lease is held, another worktree
already carries commits for this ticket, `main` shows a
`done`/`dropped`/`in-progress` state (or does not exist on `main` at
all), an open blocker remains, the lease's scope has diverged from
`main`'s, or another live lease's scope files collide (T-2225); `True`
only when every one of those checks passes.

### `ticket_readiness`

<!-- frob:doc docs/guides/coordinator-scripts.md#ticket_readiness -->

T-2133's actual answer to "given T-####, is it dispatchable right now?" --
combines the functions above into one dict: `lease`, `main`
(state/scope on `main`), `scope_diverges` (`_scope_diverges_from_lease`),
`worktrees_with_commits`, `scope_lease_collisions` (T-2225, other live
leases whose scope files overlap this ticket's own), and `dispatchable`
(`_ticket_dispatchable`, T-2213). T-2213 split the two decision
predicates (`scope_diverges`, `dispatchable`) out of this function's own
body -- it stays the thin orchestrator that gathers the facts from the
functions above and hands them to those two predicates; see their own
entries for the exact decision logic each answers.

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
group), CPU time (MAX across the group), and (T-2249) `child_cpu_s`
(`_descendant_cpu_seconds`, summed over every live descendant of the
group's own pids) -- content alone cannot distinguish a live land from a
dead attempt's residue (a killed land's staged diff is byte-identical
across retries), but CPU time discriminates immediately.

**T-2193 fix**: an earlier version looked for a `--ticket T-####` FLAG,
which does not exist on `land`'s own argparse usage, so it matched
nothing against a real land and every row fell back to a
`ticket_id=None` singleton -- reported live as 13 rows for ONE real
land. Rows with no parseable ticket id are now DROPPED entirely, not
reported as their own invocation -- there is nothing to deduplicate an
uncorrelated row against, so it is process-table noise (e.g. a
coordinator's own wait-loop shell whose command line merely contains
the text), never evidence of a land.

**T-2249 fold-in (not separately ticketed)**: `cpu_s` alone reads a
healthy land running `frob check` as a CHILD process as a near-zero-CPU
stall -- the 4 tracked rows (bash wrapper, `timeout`, `uv run`, the
python process) accumulate almost none of their own CPU while the real
work happens one process down. `child_cpu_s` fixes this by walking the
whole process tree, chased twice before being fixed here.

### `_all_process_ppid_cpu`

<!-- frob:doc docs/guides/coordinator-scripts.md#_all_process_ppid_cpu -->

T-2249. `{pid: (ppid, cpu_seconds)}` for every live process, ONE
`ps -eo pid,ppid,time` call -- the snapshot `_descendant_cpu_seconds`
builds a child-lookup table from, so `land_invocations` costs one extra
`ps` invocation total for the whole report, never one per descendant.
Structured columns only (matching `land_process_rows`'s own contract),
never a text line-count.

### `_descendant_cpu_seconds`

<!-- frob:doc docs/guides/coordinator-scripts.md#_descendant_cpu_seconds -->

T-2249. Sum of `_all_process_ppid_cpu`'s own cpu-seconds for every LIVE
descendant of a set of root pids (never the root pids themselves) --
walks the ppid links built from ONE `ps` snapshot, so summing a land's
whole process tree costs nothing extra per pid.

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
`/proc` file is missing or unparseable. `MemAvailable` alone is not the
whole memory-pressure picture -- see `swap_pressure`.

### `swap_pressure`

<!-- frob:doc docs/guides/coordinator-scripts.md#swap_pressure -->

T-2249. `(swap_used_kb, swap_total_kb)` read from `/proc/meminfo`'s
`SwapTotal`/`SwapFree` fields -- the same file `host_load` already reads
`MemAvailable` from, no new `/proc` file and no subprocess. Measured
incident: `MemAvailable` read a healthy 11.5GB while the same host had 0
free RAM and 6GB already in swap -- `MemAvailable` counts reclaimable
page cache and says nothing about pages already pushed to swap.
`swap_total_kb == 0` (no swap configured) is a real, valid case, never
an error. Returns `None` (never a fabricated zero) when the file is
missing/unparseable.

### `_swap_guidance`

<!-- frob:doc docs/guides/coordinator-scripts.md#_swap_guidance -->

T-2249. The concurrency GUIDANCE clause text: the static `"3-4 agent
concurrent"` unless `swap_pressure`'s own reading shows
`swap_used_kb >= _SWAP_PRESSURE_FLOOR_KB` (1GB -- set well below the
measured 6GB incident and well above the few-MB of swap a healthy host
routinely carries; "any swap at all" is deliberately NOT the trigger,
per the ticket's own caution), in which case it names the pressure
directly. `swap is None` (unknown) or `swap_total_kb == 0` (no swap
configured) both fall through to the ordinary guidance -- pressure is
only ever claimed from a real reading.

### `_land_status_lines`

<!-- frob:doc docs/guides/coordinator-scripts.md#_land_status_lines -->

T-2180 (ARCH103 split, same precedent as `_ticket_readiness_lines`).
Renders the LANDS/LAND LOCK/LOAD block as plain text lines from
already-computed inputs -- the pure-compute half, no `print` call, so
`_print_land_status` stays I/O-only. T-2222: the LOAD line's own
concurrency guidance clause (`_swap_guidance`, T-2249) is computed from
the LIVE lease count (`live_lease_count`) and swap pressure together,
never the raw `len(leases())` alone -- both lease counts are shown
(`"N live lease(s) (M total)"`) so a reclaimable/root-resident lease is
never silently read as a live agent.

T-2249 fold-in (not separately ticketed): an idle `LAND LOCK` (file
exists, no live `/proc`-fd holder) now prints as the NORMAL resting
state, never 'stale' -- a flock is kernel-released the instant its
holder dies, so this wording had already contributed to one retracted
ticket claiming a stale lock deadlocked the fleet. Each land's `cpu=`
line also shows `child_cpu_s` (`land_invocations`' own field) when
nonzero.

### `_print_land_status`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_land_status -->

T-2180. Prints the LANDS section: `land_invocations` (ticket id, pids,
elapsed, cpu, child cpu), `land.lock` holder liveness, and a LOAD line
(`host_load`'s load average and available memory, `swap_pressure`
(T-2249), plus the live/total held-lease counts, T-2222) against this
host's recorded concurrency guidance (`_swap_guidance`). Printed
unconditionally inside `_print_fleet_report`, in the standing report a
coordinator already runs -- not behind a separate command (the
"automatic over commands"
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

T-2182. `{"id", "state", "priority", "tier", "created", "runs_last",
"parent"}` hand-parsed directly from a `tickets/<id>/ticket.md` file on
disk (never `git show main:...` -- the live, uncommitted ledger is what a
dispatch decision actually depends on). `None` if the file is unreadable
or any required field is missing. `tier` defaults to `ticket`, matching
`TicketTier`'s own default for a ledger row written before tiers
existed.

T-2200: `runs_last` is read as the STRUCTURED `runs_last:` ledger line
`frob ticket new --runs-last` writes, never inferred from `title` text --
T-1614's own title happens to start with the literal string 'RUNS LAST',
which is exactly the lexical shortcut that would silently miss every
OTHER `runs_last` ticket whose title does not happen to say so. Missing
defaults to `False`.

T-2229: `parent` is read the same way, as the STRUCTURED `parent:`
ledger line (`None` for a missing line or the YAML-null spellings this
repo's writer emits, never the literal string "null"), never inferred
from title text -- the field `_epics_with_active_children` compares
against.

### `_epics_with_active_children`

<!-- frob:doc docs/guides/coordinator-scripts.md#_epics_with_active_children -->

T-2229. Ticket ids that have at least one OTHER ticket under
`TICKETS_DIR` carrying `parent == <this id>` in a non-terminal state
(`_TERMINAL_STATES`, mirrors `TicketState.DONE`/`DROPPED`) -- ONE scan
over every ticket dir (not just rotting ones), shared by `rotting_
tickets` so its "already decomposed" bucket agrees with `frob.gates.
_tickets_gate._has_active_child`'s own predicate exactly (same field,
same terminal-state definition). Measured incident: T-1623 (epic,
rotting) had children T-2223/T-2224 in-progress on main, but the report
told the operator to "work it" -- an action already effectively taken.

### `rotting_tickets`

<!-- frob:doc docs/guides/coordinator-scripts.md#rotting_tickets -->

T-2182. Every QUEUED/PLANNED ticket under `TICKETS_DIR` (excluding
`tickets/archive/**`) whose priority-specific rot-day threshold has been
crossed since its own `created` date -- derived entirely from the
ledger's own structured fields compared against configured thresholds,
never by parsing `frob check`'s rendered TICK004 text. Mirrors
`_tick004_queue_rot`'s own selection exactly. Each entry carries `tier`
so a caller can distinguish a rotting leaf ticket (needs dispatch) from
a rotting epic/story (needs decomposition), plus (T-2229)
`has_active_child` (`_epics_with_active_children`) so a caller can
further distinguish a genuinely undecomposed epic/story from one that
has already been decomposed and is being worked.

### `_rotting_entry`

<!-- frob:doc docs/guides/coordinator-scripts.md#_rotting_entry -->

T-2229 (ARCH001 split off `rotting_tickets`). One `rotting_tickets`
entry for a single `ticket_dir`, or `None` if it is unreadable/malformed,
not QUEUED/PLANNED, or still under its priority's threshold -- the
per-file half of `rotting_tickets`, letting the directory-walk/sort half
stay readable on its own.

### `_print_rot_bucket`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_rot_bucket -->

T-2229 (ARCH001 split off `_print_ticket_rot`). Prints one TICKET ROT
bucket -- a `  HEADING (N):` line plus one `    id ...` line per ticket,
optional trailing `detail` text (a `{id}`-format string) -- shared by all
four buckets `_print_ticket_rot` renders, replacing what used to be four
near-identical inline loops.

### `_print_ticket_rot`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_ticket_rot -->

T-2182. Prints the TICKET ROT section: `rotting_tickets`'s count, split
under headings naming the required action -- 'NEEDS DISPATCH' for
`tier=ticket`, 'NEEDS DECOMPOSITION' for a genuinely undecomposed
`tier=epic`/`tier=story`, and (T-2229) 'DECOMPOSED, BEING WORKED' for an
epic/story that already has a non-terminal child (`has_active_child`) --
'work it'/'needs decomposition' is a lie for it, the action is already
effectively taken. Epics are NOT exempted from the report either way,
only reported under their own action heading (measured incident: 10 of
15 rotting tickets were epics, 1 a story, only 4 leaf tickets -- one
undifferentiated count told a coordinator to do something impossible for
two thirds of the set, which is why the alarm read as noise for a whole
session). Printed unconditionally inside `_print_fleet_report`; TICK004
already fires in `frob check`'s gate layer but sat as 11 lines inside a
19-error list there.

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

Usage (T-2236: `uv run python`, not bare `python3` -- see this doc's own
top-of-file note):

```
uv run python scripts/fleet_status.py [--idle-minutes N] [--ticket T-#### [--ticket T-#### ...]]
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

### `load_land_commit`

<!-- frob:doc docs/guides/coordinator-scripts.md#load_land_commit -->

Resolves a ticket id to the sha it landed at, by reading that ticket's own
persisted `land_commit` field (`frob.tickets._models.Ticket.land_commit`) --
never by grepping git history for the id. Returns the sha string when the
ticket landed, `None` when the ticket exists but was never landed (or
landed before this field existed), or a `KeyError` instance (returned, not
raised) when no such ticket exists at all -- three outcomes kept lexically
distinct in `main`'s own output, the same "never conflate unknown with
missing" discipline `resolve`/`is_ancestor` already apply to a plain sha.

This is why a ticket id resolves correctly even for a `frob ticket land
--plan` land: that land's own commit subject is `chore(tickets): land
--plan finalize ...`, with no ticket id in it at all, so nothing short of a
structured field the land itself wrote could ever resolve it (see
`docs/modules/tickets-landing.md#frob-ticket-land---plan-t-1269` for how
`--plan` writes it).

### verify_lands-main

<!-- frob:doc docs/guides/coordinator-scripts.md#verify_lands-main -->

CLI entry point: each argument may be a commit sha OR a ticket id
(`T-####`, T-2220). A ticket id argument resolves via `load_land_commit`
first (`UNKNOWN-TICKET <id>` if no such ticket exists, `NOT-LANDED <id>` if
it exists but never landed) and then falls through to the same sha check
every plain sha argument gets: prints `UNKNOWN-SHA <arg>` when it does not
resolve, `MISSING <sha> NOT an ancestor of <ref>` when it resolves but is
not landed, or `ON <ref> <sha> <subject>` when it is a genuine ancestor;
exits 1 if any argument was unknown, missing, an unrecognized ticket id, or
an unlanded ticket id.

Usage:

```
python3 scripts/verify_lands.py <sha-or-ticket-id> [...] [--ref main]
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
