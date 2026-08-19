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

Returns the `git status --short --porcelain` lines for the root checkout,
CONTENT-confirmed; an empty list means the root is clean and safe to
dispatch onto.

T-2586: a bare `M`/`MM`-only status line is re-verified against
`git diff --stat HEAD -- <path>` (the same normalizing comparison
`git diff` uses) and dropped if that comes back empty -- `git status`'s
fast stat-comparison path can report a tracked file "modified" from a
byte-count mismatch alone (this repo's `core.autocrlf=true`, a Windows
setting present on this Linux/WSL clone, previously reintroduced CRLF on
checkout for any file with no pinned `eol` attribute; `.gitattributes`
now pins `eol=lf` for `rapid-debt.jsonl`/`force-overrides.jsonl`, the two
files a deferred rapid-profile sweep rewrites with LF-only content on
every land) without there being any real content difference. Untracked
(`??`) and added/deleted/renamed paths are never re-verified -- those
codes come from tree/index PRESENCE, not a stat comparison, so a
genuinely dirty root (including retry-loop untracked residue) is still
reported correctly.

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

### `_worktree_ticket_id`

<!-- frob:doc docs/guides/coordinator-scripts.md#_worktree_ticket_id -->

`"T-2599"` for a worktree directory literally named `t-2599` (this repo's
`frob ticket work`/`EnterWorktree` naming convention), else `None`. An
ad-hoc named worktree (`dev-friction`, `gate-internals`, a hand-cut series
worktree) has no resolvable ticket and always returns `None`.

### `worktree_content_classification`

<!-- frob:doc docs/guides/coordinator-scripts.md#worktree_content_classification -->

T-2599: classifies one worktree as `"STRANDED"`, `"STALE"`, or `"ACTIVE"`
against `main`, returning `(verdict, samples)` where `samples` is up to 5
example added lines backing a `STRANDED` verdict.

The obvious tests for "does this worktree hold unlanded work" are all
measured wrong:

- `git log main..HEAD` (commit count) overcounts -- `frob ticket land`
  SQUASHES, so a worktree whose content fully landed still shows every
  pre-squash commit as "unlanded".
- `git diff --stat main..HEAD` conflates ahead with behind -- a worktree
  that is merely stale (main moved on) shows an enormous diff because of
  main's own progress, not anything the worktree holds.
- Reading the insertion count alone, without checking direction, still
  misreads a line main deliberately replaced/rewrote as stranded.

T-2617: that same per-line presence check, measured against real data an
hour after T-2599 landed, itself reproduces the third wrong test's shape
in a subtler form. `t-2576`/`t-2593` both landed cleanly, but the code
that superseded them RENAMED the symbols their own diffs added (e.g.
`_write_baseline(...)` -> `_write_baseline_cas(...)`) -- no byte-identical
line survives the rename, so an exact-line-text check misreads fully
landed work as `STRANDED` 18 times over on real data. Two additional,
more precise checks now run BEFORE falling back to the line-presence
test:

1. **`land_commit` ancestry (exact, ticket-linked worktrees).** If
   `ticket_id` resolves and the ticket's state on `main` is terminal
   (`done`/`dropped`/`failed`) AND its recorded `land_commit`
   (`frob ticket land`'s own stamp) is an ancestor of `main`'s current
   tip, the verdict is `STALE` unconditionally -- the ticket's content
   (or, for a drop, its land-adjacent bookkeeping) genuinely reached
   main, regardless of what a rename does to the diff's line text. A
   terminal ticket with no recorded `land_commit` (pre-T-2220 ledger, or
   a hand-edited state) falls through to the checks below.
2. **Deletion-dominant ratio (magnitude, for worktrees with no ticket to
   consult).** `git diff --numstat` restricted to the same paths; if
   deleted lines are at least `_DELETION_DOMINANT_RATIO` (3x) the added
   lines, the verdict is `STALE` -- the `gate-internals` shape T-2617
   measured (110259 deletions against 12618 insertions, ratio ~8.7): a
   worktree so far behind main that its diff is almost entirely main's
   own subsequent growth, not anything the worktree itself holds.

Only after both of those decline does the original per-line presence
check run: diff `main..HEAD` restricted to `src`/`tests`/`docs`/
`scripts`, and for every `+` line ask whether main's CURRENT version of
that same file already contains that exact line text anywhere (not
necessarily the same location) -- content genuinely absent from main's
current file (or a whole file absent from main entirely) is stranded;
content merely reformatted, moved, or already superseded is not. This is
a same-file line-presence check, not a formal diff/patience algorithm,
and is deliberately conservative toward over-reporting `STRANDED` (a
rewrapped comment or reflowed doc paragraph can register as "not
present" even though nothing genuinely changed) rather than under-
reporting it -- safe for a report-only classifier that never deletes
anything itself, since the dangerous direction is missing real stranded
work, not flagging a false positive a human then double-checks. T-2617's
own deliberately-constructed positive control (a symbol genuinely absent
from main, in a mostly-additive diff that never trips the deletion-ratio
check) proves this fallback still fires -- the two checks above narrow
false positives without collapsing the whole classifier into "always
STALE".

`ticket_id` (resolved via `_worktree_ticket_id` for a `t-XXXX`-named
worktree) short-circuits to `"ACTIVE"` whenever that ticket's state on
`main` is not terminal (`done`/`dropped`/`failed`) -- an active ticket is
never proposed for removal regardless of what its diff looks like, and
its content is never even inspected. This is CHECKED but not yet
CONSULTED beyond terminal-vs-not (T-2617 residue, filed separately): a
`queued` ticket with no live lease held anywhere still reads `ACTIVE`
identically to a genuinely in-progress one, since ACTIVE is the
safe-direction verdict and distinguishing "queued, nobody working it" from
real activity needs a lease-based signal this function does not consult.
`fleet_status.py`'s own `WORKTREES` section prints each idle-looking
worktree's verdict next to it, and a `STRANDED: N` count in the section
header -- surfaced where the operator already looks, per this ticket's
own preference over a separate command. Nothing here deletes a worktree;
`frob worktree sweep` (playbook section 12b) remains the only removal
path, lease-aware and separately gated.

### `_print_worktrees_section`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_worktrees_section -->

`_print_fleet_report`'s own `WORKTREES (STRANDED: N)` section (ARCH001
split, pulled out to keep `_print_fleet_report` itself under the
long-function threshold): classifies every idle-looking worktree's
content ONCE via `worktree_content_classification` and reuses that same
verdict for both the header's `STRANDED` count and its own printed row,
rather than classifying twice per worktree.

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

### `verify_queue_state`

<!-- frob:doc docs/guides/coordinator-scripts.md#verify_queue_state -->

`VERIFY_QUEUE`/`VERIFY_WATERMARK` are `.frob/verify-queue.json` and
`.frob/verify-watermark.json`, the T-2126 verify-queue/watermark stores
`frob.verify._watermark` owns -- read here as raw JSON, the same
dependency-light convention `QUARANTINE`/`LEASES` above already use.

`verify_queue_state()` returns `(depth, oldest_age_s)`: queue depth and
the oldest still-pending entry's age in seconds. A MISSING file means
nothing is queued: `(0, None)`. An UNREADABLE or malformed file returns
`(-1, None)` -- never a silent `(0, None)`, mirroring `quarantine_state`'s
own "cannot verify is never verified" posture immediately above:
misreading unknown as empty would tell a coordinator it is safe to
dispatch when the real depth could not be determined at all. This feeds
`frob.verify._backpressure.block_until_watermark_advances` (the same
function `_apply_backpressure` calls right after the quarantine
override) -- the queue depth/age a coordinator sees here is the same
number that decides whether a dispatched agent's own land will block on
backpressure. Depth alone is a QUEUE-ENTRY count, not the full
commit-gap reconciliation `frob verify status` (T-2290) computes; a
coordinator wanting the reconciled commit count uses that command
instead.

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

### `_parse_ticket_frontmatter_text`

<!-- frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_frontmatter_text -->

T-2449. The pure-parse half of `ticket_frontmatter_on_main` -- `{"state":
..., "scope": [...], "blocked_by": [...], "land_commit": ...}` parsed
from a ticket.md's own YAML frontmatter TEXT, regardless of which of the
two `git show` paths (active or archived) supplied it. Split out so the
SAME parser runs both times, rather than duplicating the parse per call
site. T-2617 added `land_commit` (the flat `key: value` line `frob
ticket land` stamps via `_record_land_commit` once a ticket finalizes) --
`worktree_content_classification`'s exact-ancestry short-circuit reads
it; absent (`None`) for any ticket that never landed.

### `ticket_frontmatter_on_main`

<!-- frob:doc docs/guides/coordinator-scripts.md#ticket_frontmatter_on_main -->

`{"state": ..., "scope": [...], "blocked_by": [...], "land_commit": ...}` parsed from
`main:tickets/<id>/ticket.md`'s YAML frontmatter via `git show` plus a
narrow hand-rolled parse (no `import yaml` -- this script stays
plain-stdlib, matching its module docstring's contract), falling back to
`main:tickets/archive/<id>/ticket.md` (T-2449) when the active path
resolves to nothing. `None` only if the ticket exists in NEITHER
location.

T-2449's own measured incident: this function used to only ever check
the active ledger directory, so a ticket whose blockers had been
completed AND ARCHIVED was indistinguishable from one whose blockers
were simply missing -- both read as "cannot resolve", and the caller
(`_classify_blockers`) resolved that ambiguity as "still open". T-1696
sat blocked for 12 days this way, while `TICKET ROT` simultaneously
listed it under `NEEDS DISPATCH`. `frob.tickets.load_queue` (pinned by
`tests/test_ticket_land.py::TestArchiveV2::
test_archived_v2_ticket_still_resolves_as_blocker`) already merges both
locations for the real ledger -- this mirrors that exact two-location
order in plain form rather than `import frob`, because this script's
"no frob import" contract (module docstring) is load-bearing: it must
run correctly under ANY `python3` on PATH per `scripts/
_require_python.py`'s own guard, not only inside this project's built
venv.

This is deliberately the STATIC, main-committed half of a scope
comparison, not the live one -- `main:tickets/<id>/ticket.md`'s `scope:`
field can be stale the moment a worktree calls `frob ticket scope`
without having landed yet. T-2133's own second incident: a coordinator
read this file directly, twice, believing it WAS the ticket's live
scope -- once nearly releasing a healthy lease, once asking an agent to
redo a scope-narrowing it had already done on its own branch.
`ticket_readiness` below is what actually compares this against the
live lease.

### `_classify_blockers`

<!-- frob:doc docs/guides/coordinator-scripts.md#_classify_blockers -->

T-2449. `(open_ids, unresolved_ids)` -- replaces the old
`_open_blocker_ids`, which collapsed two distinct facts into one "still
open" bucket. A blocker id that resolves (via `ticket_frontmatter_on_
main`, archive-aware) to a real, non-terminal ticket is genuinely OPEN.
A blocker id that resolves NOWHERE is UNRESOLVED -- reported in its own
list (fail-loudly, T-2391: "cannot confirm" is never "resolved"), even
though both lists are still treated as dispatch-blocking by
`_ticket_dispatchable`; only the REPORTING is distinct (acceptance [2]).

### `_classify_blockers_local`

<!-- frob:doc docs/guides/coordinator-scripts.md#_classify_blockers_local -->

T-2449. The LOCAL-disk twin of `_classify_blockers`, used by
`_rotting_entry` so the `TICKET ROT` section's own NEEDS DISPATCH bucket
agrees with `ticket_readiness`'s dispatchability verdict (acceptance
[3]) without paying for a `git show` per blocker id on every rot pass.
`_local_ledger_state` resolves a single id (active ledger, then
`tickets/archive/`) the same way `ticket_frontmatter_on_main` does for
the `main:`-committed side.

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

### `_land_ticket_collisions`

<!-- frob:doc docs/guides/coordinator-scripts.md#_land_ticket_collisions -->

T-2281 (ARCH001 split off `scope_lease_collisions`). Which of
`land_invocations()`'s own ticket ids (a live process genuinely landing
that ticket right now) collide with a ticket's own scope files,
excluding any id already reported via a live lease. Each id's scope is
read from `main` -- see `scope_lease_collisions`'s own entry for the
full incident this closes.

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

T-2281: `land_ticket_ids` (`land_invocations()`'s own ticket ids) is a
SECOND, independent occupancy source, joined alongside `held` -- `held`
alone is blind to the window between a land's local worktree close
(which releases the shared lease immediately) and its squash reaching
the primary checkout, during which a ticket whose files are genuinely
still contended holds no lease at all. Measured: `LANDS IN FLIGHT:
T-2254 ... elapsed=454s` printed in the same run as `T-2254 -> t-2254
[reclaimable]`. Each such ticket's scope is read from `main` (no lease
exists to read it from); never inferred from ticket STATE (`in-progress`
during this window is normal and intentional). A ticket already reported
via a live lease is never double-counted.

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

T-2475: `ps -eo args`'s text is a space-JOINED rendering that cannot
tell a real invocation (`ticket`/`land` as two separate argv elements)
from a process whose command line merely CONTAINS that text glued
inside one argv element -- measured incident: a coordinator's own
wait-loop shell running `pgrep -f "frob ticket land T-2408"` read
identically to a real land in `ps -eo args` text (elapsed=306s,
cpu=0s reported as a live land) after the real land had already
finished. Every row that passes the cheap text pre-filter is now
re-verified against `/proc/<pid>/cmdline`'s own NUL-delimited argv
(`_pid_has_land_argv_tokens`, mirroring `concurrent_check_count`'s own
token-not-substring contract, T-2473) before being kept; a row whose
pid cannot be re-read (already exited, `/proc` unavailable) is kept on
the text pre-filter alone, same as before T-2475 -- 'cannot confirm' is
never 'confirmed absent'.

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

### `orphaned_forkserver_count`

<!-- frob:doc docs/guides/coordinator-scripts.md#orphaned_forkserver_count -->

T-2443. How many live `multiprocessing.forkserver` helper processes on
this host are reparented to init (`ppid == 1`, i.e. their creating
process is dead) -- the exact process-table signature of the ticket's own
incident: `frob check` killed by this fleet's routine `timeout 540 ...`
wrapper used to leave its process-pool workers, and therefore the
forkserver helper they keep alive, running forever, 94 of them measured
reparented to `/init` at once, holding 17.3GB of swap. Mirrors
`frob.process._reap`'s own cmdline+ppid detection in plain form (this
script's "no `frob` import" contract), read directly from `/proc` (no
subprocess), matching `host_load`/`swap_pressure`'s own contract exactly.
Returns `None` (never a fabricated zero) when `/proc` is unreadable. See
`docs/modules/process.md#forkserver-reaping-t-2443` for the fix this
number makes actionable -- the fix itself lives in `frob.process._reap`,
not here; this function only reports.

### `_forkserver_snapshot`

<!-- frob:doc docs/guides/coordinator-scripts.md#_forkserver_snapshot -->

T-2517. One `/proc` walk collecting every live `multiprocessing.
forkserver` helper's pid/ppid/age/VmSwap, shared by `orphaned_forkserver_
count`, `stale_forkserver_count`, and `forkserver_swap_held_kb` so
reporting all three numbers costs one scan, not three. Age is computed
from `<pid>/stat`'s starttime field against `<proc>/uptime` and
`os.sysconf("SC_CLK_TCK")`; VmSwap is read from `<pid>/status`. A
per-process file that cannot be read degrades only that process's field
to `None`/`0`; the whole scan returns `None` only when `/proc` itself is
unreadable.

### `stale_forkserver_count`

<!-- frob:doc docs/guides/coordinator-scripts.md#stale_forkserver_count -->

T-2517. Motivating incident: `ORPHANED FORKSERVERS: 0` read as "nothing
wrong" while 82 of 148 live `multiprocessing.forkserver` helpers were
older than an hour and held essentially all of the host's 12GB of
in-use swap between them -- invisible to `orphaned_forkserver_count`
because every one of them still had a LIVE parent (an agent shell that
had finished its check but had not exited). `orphaned_forkserver_count`'s
signal is ancestry (`ppid == 1`); this function's signal is idleness +
age, independent of ancestry: a forkserver older than `stale_after_s`
(default 1 hour) counts as stale ONLY when the caller's own
`concurrent_check_count` reading is exactly `0` -- passed in, not
re-measured, so both numbers come from the same instant. Any positive
count or `None` (unknown) makes this return `0`, per the ticket's own
explicit caution: a forkserver with a live parent may belong to a check
about to start, so a wrong precondition here would read a live pool as
reclaimable. This function performs no reclamation of any kind -- it
only reports the count; automated reclamation was explicitly deferred to
a future, separately-designed ticket, never bundled in here.

### `forkserver_swap_held_kb`

<!-- frob:doc docs/guides/coordinator-scripts.md#forkserver_swap_held_kb -->

T-2517. Sum of `VmSwap` (kb) across every live `multiprocessing.
forkserver` helper on the host, orphaned or not, stale or not -- the
third of the three numbers the ticket requires reported separately,
never collapsed into the orphan/stale counts. Deliberately reads
`VmSwap`, never RSS: a fully swapped-out process reports near-zero RSS
while still holding real memory, which is exactly the reading that let
the ticket's own 12GB incident hide behind a clean-looking `ORPHANED
FORKSERVERS: 0`. Returns `None` only when `/proc` itself is unreadable.

### `concurrent_check_count`

<!-- frob:doc docs/guides/coordinator-scripts.md#concurrent_check_count -->

T-2473. How many live `frob check` processes are running on this host
right now -- the number a coordinator needs to decide whether to
dispatch another agent, previously invisible short of a manual `ps`
scan (the ticket's own filed measurement: 12 concurrent checks went
unnoticed until someone checked by hand while swap climbed from 2.1GB
to 7.8GB and lands/hour fell from 9 to 6 as agent count rose). Matches
the `frob`/`check` argv token pair as SEPARATE tokens (never a
substring, which would also fire on <!-- frob:waive DOC006 reason="illustrative hypothetical false-positive example, not a real subcommand claim -- frob ticket evidence --check-repro is the real flag" -->`frob ticket check-repro` or a path
containing "check"), duplicated in plain form from `frob.process.
_reap`'s own matcher (this script's "no `frob` import" contract, same
posture `orphaned_forkserver_count` above already takes). ADVISORY
ONLY -- this script reports the count, it never limits, queues, or
refuses anything; see `docs/modules/process.md#concurrent-check-advisory-t-2473`
for `frob check`'s own companion advisory log line (a separate, self-
excluding counter used from inside a running check). Returns `None`
(never a fabricated zero) when `/proc` is unreadable.

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

T-2443: also renders an `ORPHANED FORKSERVERS: N ...` line from
`orphaned_forkserver_count`'s own reading -- `None` prints as "unknown
(/proc unreadable)", `0` prints as a real zero (never omitted), and a
positive count names the T-2443 leak signature directly so a coordinator
seeing an unexplained `_swap_guidance` '1 agent (SWAP ...)' clause knows
immediately whether this specific, fixable leak is the cause.

T-2517: also renders two MORE forkserver lines, deliberately kept
separate from `ORPHANED FORKSERVERS` rather than folded into it --
folding them together is the exact incident this ticket was filed from
(a clean-reading `ORPHANED FORKSERVERS: 0` while 82 stale, live-parented
pools held 12GB of swap the orphan-only signal structurally cannot see):
a `STALE FORKSERVERS: N ...` line from `stale_forkserver_count`'s own
reading (idle + aged, independent of parent liveness, only ever nonzero
when `concurrent_check_count` read exactly 0 at the same instant), and a
`SWAP HELD BY FORKSERVERS: N.NGB ...` line from `forkserver_swap_held_
kb`'s own reading (summed `VmSwap`, orphaned+stale+live-parented alike,
never RSS). Same "unknown"-vs-real-zero contract as every other line
here.

T-2473: also renders a `CONCURRENT CHECKS: N (T-2473, advisory)` line
from `concurrent_check_count`'s own reading -- the same "unknown"-vs-
real-zero contract as the forkserver line above, and, unlike that line,
never itself a leak signature: any positive count here is ordinary,
legitimate concurrent demand, the number this ticket exists to make
visible rather than derived by hand.

### `_print_land_status`

<!-- frob:doc docs/guides/coordinator-scripts.md#_print_land_status -->

T-2180. Prints the LANDS section: `land_invocations` (ticket id, pids,
elapsed, cpu, child cpu), `land.lock` holder liveness, and a LOAD line
(`host_load`'s load average and available memory, `swap_pressure`
(T-2249), plus the live/total held-lease counts, T-2222) against this
host's recorded concurrency guidance (`_swap_guidance`), followed by
`orphaned_forkserver_count`'s own line (T-2443) and `concurrent_check_
count`'s own line (T-2473). Printed unconditionally
inside `_print_fleet_report`, in the standing report a coordinator
already runs -- not behind a separate command (the
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

### `_parse_ticket_ledger_fields`

<!-- frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_fields -->

T-2449 (ARCH001 split off `_parse_ticket_ledger_file`). The per-line scan
half: `({flat "key: value" fields}, blocked_by list)` from raw ticket.md
TEXT -- adding `blocked_by:` block parsing to the combined function
pushed it over the 60-line threshold, so the scan loop moved here.

### `_parse_ticket_ledger_file`

<!-- frob:doc docs/guides/coordinator-scripts.md#_parse_ticket_ledger_file -->

T-2182. `{"id", "state", "priority", "tier", "created", "runs_last",
"parent", "blocked_by"}` hand-parsed directly from a `tickets/<id>/
ticket.md` file on disk (never `git show main:...` -- the live,
uncommitted ledger is what a dispatch decision actually depends on).
`None` if the file is unreadable or any required field is missing.
`tier` defaults to `ticket`, matching `TicketTier`'s own default for a
ledger row written before tiers existed. `blocked_by` (T-2449) defaults
to `[]`.

T-2200: `runs_last` is read as the STRUCTURED `runs_last:` ledger line
`frob ticket runs-last <id> on` writes, never inferred from `title` text --
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

### `_epics_with_any_children`

<!-- frob:doc docs/guides/coordinator-scripts.md#_epics_with_any_children -->

T-2468. Ticket ids that have at least one child ticket ANYWHERE --
active `TICKETS_DIR` or `tickets/archive/**` -- in ANY state, not just a
non-terminal one. Distinct from `_epics_with_active_children`, which
never looks in `archive/` at all: an epic whose every child has landed
and archived reads as zero active children under that predicate even
though it plainly has children. Measured incident: T-1135/T-1137/T-1219
each had every child done-and-archived, but read as `has_active_child:
False` and landed in NEEDS DECOMPOSITION -- indistinguishable from an
epic that had never been decomposed at all -- for three weeks. `_print_
ticket_rot` combines this with `has_active_child` to tell three states
apart: no children at all (still NEEDS DECOMPOSITION), children exist
but none active (NEEDS CLOSE), an active child exists (DECOMPOSED, BEING
WORKED).

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
has already been decomposed and is being worked, and (T-2468) `has_any_
child` (`_epics_with_any_children`) so a caller can further distinguish
"no children ever filed" from "children exist, all terminal -- needs a
close, not more decomposition".

### `_local_ledger_state`

<!-- frob:doc docs/guides/coordinator-scripts.md#_local_ledger_state -->

T-2449. `ticket_id`'s `state:` field read from the LOCAL, uncommitted
ledger -- the active `tickets/<id>/ticket.md` first, then `tickets/
archive/<id>/ticket.md`. `None` if the id resolves in neither location
(the caller must treat that as unresolved, never as "still open").

### `_rotting_entry`

<!-- frob:doc docs/guides/coordinator-scripts.md#_rotting_entry -->

T-2229 (ARCH001 split off `rotting_tickets`). One `rotting_tickets`
entry for a single `ticket_dir`, or `None` if it is unreadable/malformed,
not QUEUED/PLANNED, or still under its priority's threshold -- the
per-file half of `rotting_tickets`, letting the directory-walk/sort half
stay readable on its own. T-2449: also carries `open_blockers`/
`unresolved_blockers` (`_classify_blockers_local`) so `_print_ticket_rot`
can keep a still-blocked leaf out of NEEDS DISPATCH. T-2468: also
carries `has_any_child` (`_epics_with_any_children`) alongside `has_
active_child` so `_print_ticket_rot` can split NEEDS CLOSE out of NEEDS
DECOMPOSITION.

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
under headings naming the required action -- 'NEEDS DISPATCH' for a leaf
ticket with NO open/unresolved blocker (T-2449), 'BLOCKED (dependency
not yet resolved)' (T-2449) for a leaf ticket whose `blocked_by` still
names an open or unresolved id -- and, as of T-2475, ALSO a non-leaf
(epic/story) whose own `blocked_by` still names an open or unresolved
id, checked before any child-based classification below ever runs on
it -- 'NEEDS CLOSE' (T-2468) for an epic/story that has at least one
child ANYWHERE (active or archived), none of them non-terminal, AND no
open/unresolved `blocked_by` edge of its own (T-2475) -- the epic's own
work is done, it only needs a rollup Done report and a close -- 'NEEDS
DECOMPOSITION' for a genuinely undecomposed `tier=epic`/`tier=story` (no
child exists yet, anywhere), and (T-2229) 'DECOMPOSED, BEING WORKED' for
an epic/story that already has a non-terminal child (`has_active_
child`) -- 'work it'/'needs decomposition' is a lie for it, the action
is already effectively taken.

T-2475's own incident: T-1599's live shape (tier=story, one
archived-done child covering 2 of 5 deliverables, the other 3 genuinely
open and blocked on T-2411) satisfied NEEDS CLOSE's own
`has_any_child`-without-`has_active_child` trigger despite having live,
unfinished work behind an unresolved `blocked_by` edge -- routing it to
NEEDS CLOSE told a coordinator to write a rollup Done report for work
that was not done. `_rotting_entry` already computed `open_blockers`/
`unresolved_blockers` for every ticket, leaf or not (T-2449); `_print_
ticket_rot` now consults that data for non-leaves too, siphoning a
blocked non-leaf into the shared BLOCKED bucket BEFORE the has_active_
child/has_any_child split ever sees it, so a terminal-children-but-
blocked story cannot reach NEEDS CLOSE regardless of its children's
state. `_rot_bucket_lines`' `tier=` display, previously a single
bucket-wide flag keyed off the first ticket in a bucket, is now
per-ticket, so a blocked epic/story mixed into BLOCKED alongside blocked
leaf tickets still discloses its own tier.
Epics are NOT exempted from the report either way, only reported under
their own action heading (measured incident: 10 of 15 rotting tickets
were epics, 1 a story, only 4 leaf tickets -- one undifferentiated count
told a coordinator to do something impossible for two thirds of the
set, which is why the alarm read as noise for a whole session). Printed
unconditionally inside `_print_fleet_report`; TICK004 already fires in
`frob check`'s gate layer but sat as 11 lines inside a 19-error list
there.

T-2468's own incident: T-1135/T-1137/T-1219 (three epics, every child
done-and-archived) and T-1599 (a story genuinely blocked but never
linked via `blocked_by`) and T-1614 (`runs_last`, structurally
unreachable) all raised the identical undifferentiated NEEDS
DECOMPOSITION alarm for 13-21 days -- four different actions
(close/close/close/link-a-blocker/reshape) hiding behind one label that
named none of them. The NEEDS CLOSE split is derived purely from
`has_any_child`/`has_active_child` (never from title text or a
hand-authored epic-id allowlist), and structurally cannot go empty by
reclassification: an epic with genuinely zero children anywhere still
satisfies neither `has_active_child` nor `has_any_child` and stays under
NEEDS DECOMPOSITION.

T-2449's own incident: T-1696 (high priority, queued 12 days, blocked_by
naming two DONE-AND-ARCHIVED tickets) appeared under NEEDS DISPATCH on
every tick while `--ticket T-1696` simultaneously reported `dispatchable:
False` -- the same tool contradicting itself. The BLOCKED bucket split
(computed from the SAME `open_blockers`/`unresolved_blockers` fields
`ticket_readiness` derives its own verdict from, via `_classify_blockers`/
`_classify_blockers_local`) makes "no ticket can appear under NEEDS
DISPATCH while reporting dispatchable: False" a structural invariant of
the split itself, not an incidental fact that could silently regress.

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
then delegates the actual printing to
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
