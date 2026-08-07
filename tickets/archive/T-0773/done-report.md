## Done report

Fixed the 2026-07-22 rev-parse incident: `frob.tickets._leases` now
memoizes `git_common_dir` per resolved root for the process's lifetime
(`_common_dir_cache`) and splits `read_all_leases` into a memoized
parse step (`_leases_parse_cache`, globbing + JSON-parsing every lease
file) plus a FRESH per-call liveness re-check (`Path(record.worktree).
exists()` is never cached, since a lease's worktree can vanish
out-of-band via `git worktree remove` with no write to the leases
directory to invalidate on -- caching liveness would have kept
offering a dead worktree's lease for the rest of the process; this is
what made `tests/test_ticket_leases_cross_worktree.py::
TestCrossWorktreeLeaseVisibility::test_stale_lease_for_a_removed_worktree_is_skipped`
fail under a first, naive full-snapshot-cache design -- fixed by the
parse/liveness split). The stale-lease INFO diagnostic is still logged
only once per (leases directory, ticket id) per process
(`_stale_lease_logged`), even though liveness reruns every call.
`record_lease`/`release_lease` clear the parse cache on write so a
write followed by a read in the same process still observes it.

`frob.tickets.leased_by`/`doable`/`doable_blocked` additionally thread
one precomputed `_all_leases(queue, root)` snapshot through the
per-candidate loop, mirroring the existing `breadth` parameter
(`scope_breadth_context`) -- belt-and-suspenders on top of the
`_leases.py`-level memoization, matching the ticket's explicit ask.

## Measured spawn counts (3-ticket fixture, tests/system/test_spawn_budget.py)

Before (checked out the pre-fix `_leases.py`/`__init__.py` from commit
89820713 into the working tree, ran the un-xfailed assertion, then
restored the fix -- no `git stash` used):
- `frob ticket list`: `git rev-parse --git-common-dir` spawned 3 times
  (identical argv) -- one per ticket row via `display_state` ->
  `read_all_leases` -> `leases_dir` -> `git_common_dir`.
- `frob ticket doable`: same argv spawned 3 times -- one per candidate
  via `leased_by` -> `_all_leases` -> `_cross_worktree_leases` ->
  `read_all_leases`.

After (this fix):
- `frob ticket list`: 0 duplicate spawns (spawned at most once).
- `frob ticket doable`: 0 duplicate spawns (spawned at most once).

(The real-repo incident report was "dozens" of spawns per invocation
against this repo's actual hundreds of tickets; the 3-ticket test
fixture demonstrates the same per-row/per-candidate multiplier at a
scale small enough to assert exactly, and the fix removes the
multiplier entirely regardless of ticket count.)

## Evidence

- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once`
  (xfail marker REMOVED, now plain-passing, accepts acceptance[0])
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once`
  (xfail marker REMOVED, now plain-passing, accepts acceptance[0])
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once`
  (pre-existing, still passing)
- `tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree`
- `tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease`

`uv run --frozen pytest tests/system/test_spawn_budget.py -q` -> 4 passed
in 2.47s, 0 xfailed (confirmed by `-v`, all four tests listed PASSED,
no XFAIL line).

`uv run --frozen pytest tests/test_tickets_leases.py -v` -> 4 passed.

`uv run --frozen pytest tests/test_tickets_leases.py
tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
tests/test_tickets_brief.py -q` -> 65 passed (all lease-adjacent
suites clean, including the T-0766 `resolve_lease` tests and the
worktree-liveness test that exposed the naive-cache design flaw during
development).

`uv run --frozen frob test --base main` -> python exit=0 (touched-set
selection covered both spawn-budget tests, all cross-worktree lease
tests, `tests/test_tickets.py::TestDoable`/queue-workflow integration,
and the T-0453 lease tests).

`uv run --frozen frob check --ticket T-0773 --only <stage>` for each
of lint/static/gates-fast/gates-native/gates-security -> all PASS, 0
errors (gates-fast/REL001 required `FROB_AGENT=1` in the invoking
shell -- it was not already set for this dispatch, unlike the
playbook's stated default; exporting it inline is the documented T-0574
escape hatch, not a config change, and is the only way REL001's
public-API-surface-changed-since-0.101.0 finding (from `leased_by`'s
new `all_leases` kwarg) suppresses correctly, per playbook section 4b:
version bump/changelog is land-owned, never a worktree concern).

## Deviations from the dispatch

- `FROB_AGENT` was not set in this dispatch's shell environment (the
  playbook says it is "true for every dispatched worktree agent,
  T-0574"); had to export it inline per gates-fast invocation to get
  REL001's open-debt/expired-deprecation halves scoped correctly
  without touching `pyproject.toml`. Not a ticket-scope concern, noted
  for visibility only.
- The coordinator's mid-task message correctly called out that I had
  drifted into an idle wait-on-monitor pattern; killed the stray
  background `frob check` process and re-ran everything foreground
  with explicit `timeout` values per this report.

Filed: none (no out-of-scope work discovered).
Gates: `frob check --ticket T-0773` clean across all five stage groups
(lint, static, gates-fast, gates-native, gates-security), no waivers
added.
## Round 2 (reviewer REJECT addressed)

Reviewer found the round-1 design cached the whole `read_all_leases`
result until this PROCESS's own `record_lease`/`release_lease` call
(CRITICAL: `frob.serve`'s `poll_rebase_bot` daemon loop calls
`read_all_leases` forever and never calls either, so it would go blind
to sibling-process lease writes/removals after its first poll cycle)
and mutated the module-level caches with no lock despite the daemon
thread and gate worker pools being able to call in concurrently
(MAJOR).

### Invalidation design (revised)

`_leases.py` now keys `read_all_leases`'s cache per FILE, not per
directory-snapshot: `_lease_file_cache: dict[leases_root, dict[path,
(stat_key, parsed_record_or_None)]]`. Every call:

1. Re-globs the leases directory for the CURRENT file listing (cheap
   `Path.glob`, no subprocess).
2. Drops any cached entry whose file is no longer in that listing
   (handles a sibling process's `release_lease`/direct unlink).
3. For each current file, `stat()`s it (mtime_ns, size). If the stat
   matches the cached entry, reuses the already-parsed `LeaseRecord`
   (or `None` for a known-bad file) without touching the file's bytes.
   If the stat differs (new file, or a sibling process's
   `record_lease`/direct write changed it), re-reads and re-parses,
   then updates the cache entry.

This makes the EXPENSIVE step (JSON parse) cache-hit as long as a file
is untouched, while the directory's current membership and every
file's current content are always re-observed -- a sibling process's
write or removal is visible on the very next call, from ANY process,
with no explicit invalidation hook required (so `record_lease`/
`release_lease` no longer need to clear anything).

Liveness (`Path(record.worktree).exists()`) is unchanged from round 1:
still re-checked every call, never cached, for the same reason now
extended one level -- a lease's worktree can vanish with no leases-
directory write to key a stat off of at all.

### Locking

Added `_cache_lock = threading.Lock()` (T-0125 `quiet_stdout_logs`
precedent) guarding all three caches (`_common_dir_cache`,
`_lease_file_cache`, `_stale_lease_logged`). `git_common_dir` takes the
lock only around the dict read/write, not around the `git` subprocess
itself (a benign double-spawn race between two threads missing the
cache simultaneously is possible but harmless and does not reintroduce
duplicate spawns in steady state, since the cache is warm after the
first call in a given process). `read_all_leases` takes the lock for
the whole file-cache read/update/stat-comparison sequence per call
(CPython's GIL makes one dict op atomic, but "check stat, maybe
re-parse, write back" is not one op and must not interleave across
threads).

### New tests (`tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility`)

- `test_new_lease_file_written_by_a_sibling_process_is_seen_next_call`
  -- writes a lease file directly (bypassing `record_lease`, simulating
  a sibling process), asserts the very next `read_all_leases` call sees
  it.
- `test_lease_file_removed_by_a_sibling_process_is_seen_next_call` --
  the reverse: direct `unlink` (bypassing `release_lease`), asserts the
  next call no longer returns it.
- `test_unchanged_lease_file_content_is_reused_from_cache` -- proves
  the cache-hit path is real (not accidentally always-re-reading) by
  corrupting a file's on-disk bytes while preserving its exact
  mtime/size signature (`os.utime` restore) and asserting the SECOND
  `read_all_leases` call still returns the original, previously-parsed
  record rather than failing to parse the corrupted bytes.

### Test results (foreground, `uv run --frozen`)

- `pytest tests/system/test_spawn_budget.py -v` -> 4 passed, 0 xfailed
  (re-stat adds filesystem `stat()`/`glob()` calls only, zero
  additional subprocess spawns -- the budget lock still holds).
- `pytest tests/test_tickets_leases.py -v` -> 7 passed (4 existing +
  3 new).
- `pytest tests/system/test_spawn_budget.py tests/test_tickets_leases.py
  tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
  tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
  tests/test_tickets_brief.py -q` -> 70 passed.
- `frob check --ticket T-0773 --only lint` -> PASS after `ruff format`
  (one line-length wrap in the new module-level comment block).
- `frob check --ticket T-0773 --only static` -> PASS.
- `frob check --ticket T-0773 --only gates-fast` (FROB_AGENT=1) -> PRE001
  cleared by re-sweeping; remaining `gate:COV` COV003 findings are
  against T-0795/T-0799 (unrelated in-flight tickets whose evidence
  references test classes not present in THIS worktree's checkout --
  confirmed by grepping `tests/test_ticket_land.py` for
  `TestLandRetryAfterFinalizeThenFail`, which does not exist here; not
  caused by this ticket's change, not in T-0773's scope, pre-existing
  cross-worktree ledger churn in a highly concurrent session).

Evidence added this round:
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call`
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call`
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache`
## Round 3 (lock-scope re-review)

Re-review finding: `read_all_leases` held `_cache_lock` across the
ENTIRE per-file loop, including `path.stat()`, `read_text()`,
`json.loads()`, and `LeaseRecord.model_validate()` -- serializing every
concurrent caller (daemon thread, gate worker pools) behind one file's
IO/parse for the whole directory scan.

### Lock structure (final)

`read_all_leases` now takes `_cache_lock` twice, both briefly, with all
file IO/parsing OUTSIDE it:

1. Glob the leases directory and `stat()` every current file -- no lock.
2. Lock #1 (brief): prune cache entries for files no longer present,
   read each remaining file's cached `(stat_key, record)` against the
   just-taken stat, and partition into `hits` (stat unchanged, reuse
   the cached record) vs. `to_parse` (new file or changed stat).
3. Parse every `to_parse` file (`read_text` + `json.loads` +
   `model_validate`) -- no lock.
4. Lock #2 (brief): write the freshly-parsed `(stat_key, record)`
   entries back into the cache.
5. Recombine `hits` + freshly-parsed results in the ORIGINAL sorted
   (id-ordered) file order -- `hits`/`freshly_parsed` are separate
   dicts, so a naive concatenation would have reordered a listing with
   a mix of hits and misses; this is fixed by iterating `current_paths`
   once and looking each path up in whichever dict has it.

`git_common_dir`'s lock shape is unchanged from round 2 (already
correct: lock only around the dict get/set, `git` subprocess runs
outside it). A benign race where two threads both miss the cache for
the same file and both parse it independently is possible under this
design (last write to the dict wins) -- harmless and idempotent, same
reasoning as `git_common_dir`'s already-accepted double-spawn race.

### Test results (foreground, `uv run --frozen`)

- `pytest tests/test_tickets_leases.py -v` -> 7 passed.
- `pytest tests/system/test_spawn_budget.py -rx -v` -> 4 passed, 0
  xfailed (the extra glob/stat pass and the two brief locks add no
  subprocess spawns; the budget lock still holds).
- `pytest tests/system/test_spawn_budget.py tests/test_tickets_leases.py
  tests/test_ticket_leases_cross_worktree.py tests/test_tickets_lease.py
  tests/test_tickets_lease_overlay.py tests/test_ticket_reconcile.py
  tests/test_tickets_brief.py -q` -> 70 passed.
- `ruff check`/`ruff format` on `src/frob/tickets/_leases.py` -> clean.

`git diff main -- tickets.md` at finish shows only T-0773's own block
(state/scope/scope_changes/evidence/acceptance/Done-report lines) --
confirmed no other ticket id appears in the diff.

### Changed
```
 src/frob/tickets/__init__.py      |  34 +-
 src/frob/tickets/_leases.py       | 201 +++++++++--
 tests/system/test_spawn_budget.py |  40 +--
 tests/test_tickets_leases.py      |  92 ++++-
 tickets.md                        | 713 +++++++++++++++++++++++++++++++++++++-
 5 files changed, 1008 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_resolves_own_ticket_own_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestResolveLease::test_never_returns_a_sibling_tickets_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_new_lease_file_written_by_a_sibling_process_is_seen_next_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_lease_file_removed_by_a_sibling_process_is_seen_next_call` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestReadAllLeasesSiblingProcessVisibility::test_unchanged_lease_file_content_is_reused_from_cache` (pytest node id, verified passing when recorded)
