---
id: T-5135
title: N+1 git spawns and discarded caches on the doable, check, land, doctor and
  explore hot paths (perf audit 2026-09-20)
state: in-progress
kind: bug
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/__init__.py
- src/frob/tickets/_land.py
- src/frob/tickets/_unlanded.py
- src/frob/lang/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: true
scope_breadth_ack_reason: one audit, five independent hot-path fixes; split into child
  tickets at planning if leases collide
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/explore_runner.py
  reason: explore_runner.py locked by live T-4690 lease; drop from scope, xref/map
    fix filed separately
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 1947
  new_length: 29185
evidence:
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_absent_cache_is_none
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_corrupt_cache_is_none
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_write_then_read_round_trips
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_mismatched_tree_key_is_none
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_mismatched_pairs_is_none
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_expired_ttl_is_none
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRevalidationCache::test_unmeasurable_outcome_is_cached_sentinel
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_unticketed_diff_hunk
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_passes_with_open_ticket_edge
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_grace_covers_ticket_created_and_closed_in_same_diff
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_scope_grace_without_same_diff_close_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_grace_matches_hunk_anywhere_in_ticket_block
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_marker_touch_without_state_transition_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_done_ticket_without_grace_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_v2_done_ticket_covers_own_closing_diff
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_v2_grace_covers_ticket_created_and_closed_in_same_diff
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_v2_marker_touch_without_state_transition_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_v2_done_ticket_without_grace_still_fires
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov002_v2_stale_done_ticket_unrelated_touch_still_fires
designated_repro_test: null
acceptance:
- text: given the dev ledger, when frob ticket doable runs twice within the cache
    TTL, then the second run spawns no re-measure and completes in under 5 s
  evidence: []
- text: given the dev ledger, when frob check evaluates COV002, then the base-ledger
    read makes one git spawn
  evidence: []
- text: given the dev ledger, when frob doctor runs, then it completes in under 5
    s and spawns fewer than 50 subprocesses
  evidence: []
- text: given a land precheck with 800 open tickets, when _find_leaked_tickets runs,
    then read_all_leases is called once
  evidence: []
acceptance_amendments:
- op: remove
  index: 4
  old_text: given a warm artifact cache, when frob explore xref run_argv runs, then
    it completes in under 3 s with zero uncached parses
  new_text: null
  reason: explore_runner.py removed from T-5135's scope due to a live cross-worktree
    lease collision with T-4690 (frob ticket work refused to start with it in scope);
    the xref/map artifact-cache fix is filed separately as T-5201
  actor: logan
  at: '2026-09-21'
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5135
branch: t-5135
---
Measured 2026-09-20 on dev at 0.531.0, 691 open tickets, 11436 ledger commits. Full audit attached (perf-audit.md). Fix in this order. (H2) frob ticket doable 76s: _rapid_sweep._reproducing_identities_cached returns on the UNMEASURABLE branch (line ~3759) without calling _write_revalidation_cache (success path only, ~3768), so the 20s budget re-check (which always exceeds its budget+60s timeout at this size) is re-spawned on every call and buys nothing. Cache the negative outcome with a TTL and a known-unmeasurable sentinel that makes zero spawns; keep 'unmeasurable is never resolved'. Secondary: the child frob check --budget 20 runs past 80s, so --budget is not bounding; measure and fix separately if confirmed. (H3) frob check COV002: gates/__init__._ledger_states_at_base_v2 spawns git show <base>:<path> once per ticket file (~691 spawns per check on the land hot path); replace with one git cat-file --batch stream. (H4/H5) land precheck: _land._sibling_branch_ref re-runs read_all_leases per candidate, discarding the leases hoist T-4492 added one frame above; thread the hoisted leases through. _sibling_branch_touched_path spawns two git show per (sibling, path); batch. (M7) frob doctor 23s: _unlanded._directive_anchored_ticket_ids spawns git show per changed file per branch (719 spawns, 13 branches); one git grep -l frob:ticket <branch> -- <paths> or cat-file --batch per branch. (xref/map 11s) lang._parse_file_with_artifact_cache is a passthrough whenever PARSE_ARTIFACT_CACHE_ENV is unset, i.e. every single-process command; 1643 uncached parses per frob explore xref. Open the artifact cache read-only for explore commands. Also in the audit, lower priority: M1 git log -S per changed file in waive-audit, M2 cat-file -e per touched file in land baselines, M3 two spawns per commit in verify attribution, M4/M5 repeated load_queue in work --cluster and close (four loads), M6 BUG003 re-runs pytest per directive uncached.

# Performance audit: per-iteration spawns, repeated loads, uncached timeouts

Scope: all of `src/frob` (not just `tickets/`). Method: an AST scan of every
`.py` under `src/frob` building a name-resolved call graph, marking direct
process spawns (`frob.gitio.run_argv`, `subprocess.run/Popen/check_output/
check_call`, `guarded_subprocess_run`) and reporting every `for`/`while` whose
body reaches one of them within 3 hops WITH at least one LOOP-VARIANT argument
(the exact complement of what PERF008 fires on). Scan script kept at
`/tmp/claude-1000/-home-logan-projects-frob/66d9bcdb-8ecd-4eb1-8324-5bac70a83cd5/scratchpad/scan2.py`;
raw hits at `.../spawnloops.tsv` (553 rows, 106 after dropping generic
name collisions like `search`/`_scan`/`run`).

Scale assumptions used for the multipliers: 691 open tickets (~4200 total
incl. archive), ~11,436 commits touching the ledger, ~2000 source files.

Every finding names the loop variable, the spawn reached, the multiplier, the
batched alternative, and why no current PERF rule fires.

---

## HIGH

### H1. `frob ticket flow`: two full-history `git log` spawns per ticket (shape A + C)
**Where**: `src/frob/tickets/_flow.py:244` (`_mine_done_transitions_v2`, loop
`for ticket_id in ticket_ids:`) -> `src/frob/tickets/_store.py:1002`
(`v2_state_transitions`, loop `for path in _v2_path_lineage(root, rel_path)`)
-> `src/frob/tickets/_store.py:949` (`_v2_path_lineage`, loop
`for _ in range(64): prev = _v2_rename_source(root, current)`) ->
`src/frob/tickets/_store.py:887` `_v2_rename_source` spawns
`git log --diff-filter=R -M100% --name-status -- <rel_path>`, and
`_mine_v2_path_transitions` (`_store.py`, called at 1002) spawns
`git log --reverse -p -- <path>`.

**Loop variable / spawn / multiplier**: `ticket_id` (n = tickets in the sprint
or the whole queue, up to 691) x at least 2 git spawns per ticket
(1 rename probe + 1 `log -p` per lineage segment; a renumbered draft adds one
more of each per segment). Each of those spawns is a git revision walk that is
NOT bounded by the path: git still walks the full 11,436-commit history to
decide which commits touched the path. 691 x 2 = ~1400 full-history walks.

**Why the docstring is wrong**: `_mine_done_transitions_v2`'s docstring claims
"fast because each ticket's own file history is a small, disjoint slice of the
repo's total commit count, not the whole thing walked once per caller". The
SLICE is small; the WALK is not -- `git log -- <path>` costs O(total commits)
to find that slice, so the v2 path is O(tickets x commits) = 691 x 11436, worse
than the v1 whole-ledger walk it replaced (1 x 11436 walk + 11436 `git show`).
That is the measured 10-minute hang.

**Batched alternative (exists)**: one `git log --reverse --name-status -p
--format=... -- tickets/` walk of the whole `tickets/` subtree, parsed once into
`{ticket_id: [(sha, iso, state)]}`, plus one `--diff-filter=R -M100%
--name-status -- tickets/` pass to recover the full rename lineage of every
ticket in the same single walk. That is 2 spawns TOTAL instead of ~1400, and it
keeps the exact `-M100%`-only rename semantics T-1543 required (no `--follow`).

**Why no PERF rule fires**: PERF008 requires EVERY argument at the call site to
be loop-invariant; `ticket_id`/`path`/`current` are loop-variant at all three
levels, so PERF008 is exempt by design. PERF012 only fires on a non-loop
function reaching the same spawn via two distinct call paths. PERF007
(`_redundancy`) needs 2+ top-level symbols sharing an uncached callee, and here
there is one caller. Corpus row C7 ("N+1 query pattern") is exactly this shape
and is recorded as a GAP in `docs/design/coding-performance-corpus.md:54`.

---

### H2. `frob ticket doable`: the unmeasurable re-check result is never cached, so the 20s budget is re-burned every run (shape D)
**Where**: `src/frob/app/ticket_runner/_rapid_sweep.py:3744-3759`
(`_reproducing_identities_cached`). On the `reproducing is None` branch it logs
`"... was UNMEASURABLE after %.1fs -- leaving them dispatchable"` and
`return None` at line 3759, WITHOUT calling `_write_revalidation_cache`
(line 3768, only reached on the success path).

**Failure scenario**: 231 sweep-filed tickets are present, so
`revalidate_dispatchable_sweep_tickets` (`_rapid_sweep.py:3684` call site
`_query.py:430` -> `_query.py:434 _revalidate_doable_queue`) builds one union
identity set and calls `_identities_still_reproducing` with
`_DOABLE_REVALIDATION_BUDGET_S = 20` (`_rapid_sweep.py:233`). The re-check
cannot finish in 20s at this repo's size, returns `None`, nothing is written,
and the NEXT `frob ticket doable` -- seconds later, same tree -- repeats the
identical doomed spawn. The cost (measured 76s end to end) buys literally
nothing on every invocation, forever, because an unmeasurable result is by
construction never cacheable under the current code.

**Secondary amplifier, same function**: the cache key is
`_identity_scoped_state_key(root, all_pairs)` (`_rapid_sweep.py:2276`) AND
`_read_revalidation_cache` requires `cached_pairs == pairs` exactly
(`_rapid_sweep.py:2364`). With 231 candidates, filing or dropping ANY sweep
ticket changes `all_pairs` and invalidates the single-slot cache file, so even
a measurable run's cache is fragile under fleet load.

**Fix direction (bounded)**: cache the NEGATIVE outcome too -- write a
`{"unmeasurable": true, "timestamp": ..., "tree_key": ..., "pairs": [...]}`
entry on the `None` branch with a short TTL (e.g. the same
`_REVALIDATION_CACHE_TTL_S`), and have `_read_revalidation_cache` return a
distinct "known-unmeasurable, do not respawn" sentinel that
`_reproducing_identities_cached` maps to `None` with 0 spawns. Keep the
"never treat unmeasurable as resolved" rule intact -- this caches the
NON-RESULT, it does not turn it into a drop. Bigger, optional follow-up: make
the budget adaptive or skip the re-check entirely when `len(all_pairs)` exceeds
what 20s has ever measured successfully.

**Why no PERF rule fires**: no existing rule models "an effect whose failure
result is not memoized". PERF007 is about two symbols sharing an uncached
callee, not about one symbol whose cache write is on the success path only.

---

### H3. COV002's base-ledger read spawns one `git show` per ticket file at the merge base (shape A + C)
**Where**: `src/frob/gates/__init__.py:1677` (`_ledger_states_at_base_v2`,
loop `for line in ls.danger_ok.stdout.splitlines():`), spawning
`git show <base>:<line>` at line 1677 for every `tickets/T-####/ticket.md`
path listed by the single `git ls-tree` above it.

**Loop variable / spawn / multiplier**: `line` (one per active ticket at base,
~691) -> one `git show` spawn each = ~691 spawns per distinct `(root, base)`
pair. `_ledger_states_at_base` above it carries
`@functools.lru_cache(maxsize=32)`, which bounds it to once per base per
process -- but that is still ~691 process spawns inside every `frob check`
run that evaluates COV002 with a v2 ledger, i.e. on the land hot path.

**Batched alternative (exists)**: `git cat-file --batch` fed the blob list on
stdin (one spawn, one stream), or `git grep -h "^state:" <base> -- tickets/`
plus the path prefix, or simply `git archive <base> tickets/ | tar -xO`. Any of
these is 1 spawn instead of 691.

**Why no PERF rule fires**: the `git show` argument embeds `line`, the loop
variable, so PERF008's all-arguments-invariant precondition fails. The spawn is
DIRECT (not behind a helper), so nothing else in `frob/perf` looks at it.

---

### H4. Cross-ticket leakage precheck re-reads all leases per candidate, re-opening the exact hole T-4492 closed (shape B)
**Where**: `src/frob/tickets/_land.py:5460`
(`_drop_hits_other_branch_never_touched`) calls `_sibling_branch_ref(root,
other_id)` (`_land.py:5273`), whose body is `for lease in
read_all_leases(root):`. It takes no `leases` parameter, so it performs a FULL
lease scan per candidate -- while its own caller chain
(`_find_leaked_tickets`, `_land.py:5735` loop) already hoisted
`leases = read_all_leases(root)` at `_land.py:5723` precisely because, per the
in-code T-4492 comment, "`read_all_leases` measured minutes on this repo, and
this loop runs once per OTHER open ticket (~800 in one land precheck)".

**Failure scenario**: a land precheck with ~800 open tickets; every candidate
that survives the scope-hit filter reaches
`_drop_hits_other_branch_never_touched`, which discards the hoisted `leases`
and re-scans `.git/frob-leases/` from scratch. Under fleet load (20 worktrees,
many lease files) that is the same minutes-scale cost T-4492 measured,
reintroduced one call frame deeper.

**Fix direction**: thread the already-hoisted `leases` sequence through
`_drop_hits_other_branch_never_touched` into `_sibling_branch_ref` as an
optional parameter, exactly like `_effective_leakage_scope` and
`_leaked_hits_for_candidate` already accept it.

**Why no PERF rule fires**: `read_all_leases(root)` takes only `root`, which IS
loop-invariant -- but the call is not lexically inside the loop, it is two
frames below it, and PERF008 attributes call sites lexically to their innermost
enclosing loop within one function. A transitively-reached invariant-argument
effect is exactly the hole here.

---

### H5. `_sibling_branch_touched_path`: two `git show` spawns per (sibling, hit path) (shape A + C)
**Where**: `src/frob/tickets/_land.py:5465` (`_drop_hits_other_branch_never_
touched`, loop `for path in hits:`) -> `_sibling_branch_touched_path` which
spawns `git show <branch>:<path>` and `git show HEAD:<path>` back to back
(two `run_argv` calls in its body).

**Loop variable / spawn / multiplier**: `path` (hit paths for this sibling) x
outer loop over siblings in `_find_leaked_tickets` (`_land.py:5735`, ~800 open
tickets). A wide-scope sibling with 40 hit paths costs 80 git spawns, and this
runs per candidate: worst case thousands of spawns in one land precheck.

**Batched alternative (exists)**: one `git diff --name-only HEAD...<branch>`
per sibling branch, intersected with `hits` in memory -- 1 spawn per sibling
instead of 2 per path, and it answers the exact question the docstring poses
("does `branch` carry a real change to this path relative to root's tip").

**Why no PERF rule fires**: `path` is loop-variant -> PERF008 exempt; the spawn
is one hop below the loop -> not visible to any per-function lexical rule.

---

## MEDIUM

### M1. `_waive_touched_since`: one `git log -S` per changed file (shape A + C)
**Where**: `src/frob/app/ticket_runner/_waive_audit.py:229`
(`_waive_touched_since`, loop `for file in sorted(changed.danger_ok):`),
spawning `git log <since>..HEAD -S frob:waive --oneline -- <file>`.

**Multiplier**: `file` = every file changed since the waive-audit watermark. At
a several-hundred-commit watermark gap that is easily 300-800 files, each
costing a pickaxe walk of the `since..HEAD` range -- the pickaxe is the
expensive git operation, and it is paid once per file.

**Batched alternative (exists)**: a single `git log <since>..HEAD -S frob:waive
--name-only --format=%x00%H` and take the union of the reported file names.
1 spawn instead of n, with identical semantics.

**Why no PERF rule fires**: `file` is a loop-variant argument (PERF008 exempt);
direct `gitio.run_argv` spawn so no other rule inspects it.

### M2. `ty`/`ruff` pre-land baselines: one `git cat-file -e` per touched file (shape A)
**Where**: `src/frob/app/ticket_runner/_land_cmd.py:4988`
(`_ty_baseline_diagnostic_identities`, loop `for f in py_files:`) and
`src/frob/app/ticket_runner/_land_cmd.py:5556`
(`_ruff_baseline_diagnostic_identities`, same loop shape), both spawning
`git -C <worktree> cat-file -e <merge_base>:<f>`.

**Multiplier**: `f` = touched python files in the diff (tens, occasionally
low hundreds for a refactor ticket) x 2 (both functions run in the same land).

**Batched alternative (exists)**: one `git ls-tree -r --name-only <merge_base>
-- <dirs>` (or `git cat-file --batch-check` over the list) and an in-memory set
membership test.

**Why no PERF rule fires**: `f` is loop-variant.

### M3. `verify/_attribution.build_ad_hoc_batch`: two spawns per commit (shape A + C)
**Where**: `src/frob/verify/_attribution.py:439` (`commit_diff(root, sha)`) and
`src/frob/verify/_attribution.py:455` (`_commit_subject(root, sha)`), both
inside `for sha in shas.danger_ok:`.

**Multiplier**: `sha` = `limit` commits (default batch sizes are tens to low
hundreds) x 2 git spawns.

**Batched alternative (exists)**: one `git log --format=%H%x1f%s -p <range>`
yields both the subject and the diff for every commit in a single walk.

**Why no PERF rule fires**: `sha` is loop-variant.

### M4. `frob ticket work --cluster`: a full queue re-load per cluster member (shape B)
**Where**: `src/frob/app/ticket_runner/_lifecycle.py:631`
(`_start_cluster_members`, loop `for member in members:` -> `queue_now =
load_queue(worktree)`), plus `_start(worktree, member_cfg)` at line 649 which
loads the queue again internally.

**Multiplier**: cluster member count (3-15 typical). Each `load_queue` globs
`tickets/T-*/ticket.md` and `tickets/archive/T-*/ticket.md`
(`_store.py:553`/`_store.py:578`), stats every one to build the index-cache key
(`_v2_cache_key_paths`), and on a cache miss parses all ~4200 files.

**Note**: the reload is partly JUSTIFIED (the docstring says "Reloads the queue
fresh before each member since the PRECEDING member's own start just committed
a ledger change") -- so the fix is not "hoist it", it is "reload only the ONE
ticket whose state moved" (`_load_one`) or invalidate the index cache narrowly.

**Why no PERF rule fires**: `load_queue(worktree)` has a loop-invariant
argument, but `load_queue` reaches only filesystem reads (`open`), not a spawn
or an `rglob`/`os.walk`, and PERF008's effect table deliberately excludes plain
file read/write (see `_loop_effects.py` docstring, item 1). So it is invisible
by design.

### M5. `frob ticket close`: four independent `load_queue` calls on one command path (shape B)
**Where**: `src/frob/app/ticket_runner/_close_cmd.py:751`, `:1471`, `:1596`,
`:1887`. Same for `src/frob/app/ticket_runner/_query.py:171`, `:426`, `:484`,
`:1042`, `:1284`.

**Multiplier**: 3-5 full ledger loads per command invocation. The index cache
(`_store.py:1594`) makes a repeat load cheap-ISH, but each still re-globs and
stats ~4200 paths, and a single concurrent ledger write in between forces a
full re-parse of all of them.

**Batched alternative (exists, unused)**: `frob.tickets._archive.
load_queue_run_scope()` (`_archive.py:118`) is exactly the memoization context
for this, and its own docstring says "NOT active by default -- `load_queue`'s
other ~45 call sites (ticket commands, CLI runners, `frob serve`, ...) see
exactly the same fresh-read-every-call behavior". Wrapping each ticket-runner
command entry point (`_close`, `_doable`, `_list`) in that scope is a
one-line-per-entry-point fix. Caveat to respect: commands that WRITE the ledger
mid-run (e.g. `_revalidate_doable_queue`'s drop, `_start`'s transition) must
either stay outside the scope or exit/re-enter it around the write.

**Why no PERF rule fires**: same as M4 -- file reads are outside PERF008's
effect table, and no rule counts repeated calls to one loader across a single
command entry point.

### M6. BUG003 runs (and re-runs) a real pytest per `must-still-pass` directive, uncached (shape A + D)
**Where**: `src/frob/gates/_bug_repro.py:1184` (`_run_designated_test(root,
test_id, _BUG_REPRO_TIMEOUT_S)`) and `:1203`
(`_bug_repro_outcome_at_ref(root, test_id, base_ref)`), both inside
`for test_id in _must_still_pass_controls(ticket):`.

**Multiplier**: 1-3 directives per ticket x 2 pytest spawns each, and the
`_at_ref` variant materializes a parent checkout. The timeout outcome
(`_BugReproOutcome` unresolvable) is `continue`d at line 1188 with no record,
so a test that times out is re-run on every `frob check` -- the same
no-cache-on-failure shape as H2, with a much smaller n.

**Fix direction**: record the outcome keyed on `(test_id, tree digest,
base_ref)` in the existing gate cache (`src/frob/gates/_gate_cache.py`), the
negative/unresolvable outcome included.

**Why no PERF rule fires**: `test_id` is loop-variant (PERF008 exempt); no rule
models uncached failure outcomes.

### M7. `_ledger_states_at_base_v2`'s sibling in `_unlanded`: one `git show` per changed file, per branch (shape A + C)
**Where**: `src/frob/tickets/_unlanded.py:648`
(`_directive_anchored_ticket_ids`, loop `for path in own_changed:` ->
`_blob_text(root, branch, path)`), and the parallel loop at
`src/frob/tickets/_unlanded.py:375` (`_ticket_state_on_main`, 2 blob reads per
ticket id -- currently callerless per its own DEAD001 waiver, so cost 0 today
but a trap for the next caller).

**Multiplier**: at 648, `path` = files a branch changed (tens to hundreds) and
the enclosing analysis runs per agent branch (~20 worktrees) -> hundreds to
low thousands of `git show` spawns per <!-- frob:waive DOC006 reason="narrative shorthand for the frob doctor unlanded-worktree walk in src/frob/tickets/_unlanded.py; there is no `frob ticket unlanded` verb" -->`frob ticket unlanded`.

**Batched alternative (exists)**: `git grep -h -E "frob:(ticket|todo) T-[0-9]+"
<branch> -- <paths>` in one spawn, or `git archive <branch> | tar -xO`, instead
of one blob read per path.

**Why no PERF rule fires**: `path` is loop-variant.

---

## LOW

### L1. `doctor.py:898`: one `_probe_binary_version` spawn per external tool
`src/frob/doctor.py:898`, loop over `name`. n = number of probed tools (~10-20),
each a real `--version` spawn with `timeout=10` (`doctor.py:852`). Correct by
nature (each tool must be probed separately); listed only so the scan's hit is
not re-triaged. No batching exists. PERF008 exempt (`name` is loop-variant).

### L2. `tickets/_live_tracker.py:420`: 2 `git grep` spawns per revision
`_scan(revision)` loops over exactly 2 (pattern, pathspec) pairs and is called
twice (current + `base_ref`) -> 4 `git grep` spawns per ticket checked. Small
constant, but it is per-ticket inside citation checks. Batchable into one
`git grep -e A -e B`. PERF008 exempt (`pattern`/`pathspec` are loop-variant).

### L3. `gates/_tdd_order.py:283`: `_show_file_at_revision` per revision in a loop
Plus `:538`/`:545` calling `resolve_symbol_introduction` per symref. n = new
symbols in the diff (tens). Each resolution walks revisions with a spawn per
step. Measurable only on large refactor lands. Batchable via one
`git log --format=... -p -- <files>` walk shared across symrefs.

### L4. `gates/_pii_structural/_crosslang.py:409`: one `git ls-files` per pattern
`_tracked_files_by_pattern(pattern)` inside `for pattern in ...`. n = number of
cross-language patterns (small, <10), but each is a whole-repo `git ls-files`
spawn -- shape E inside a loop. One `git ls-files` + in-memory fnmatch would do.

### L5. Shape E generally: ~21 un-memoized `git ls-files` call sites across gates
`src/frob/gates/_tracked_files.py:24` (`tracked_files`) and
`src/frob/gates/_walk_lint.py:316` (`tracked_python_files_for_gate`) are each
plain functions with NO memoization; between them they have 21 call sites in 19
modules. A full `frob check` therefore spawns `git ls-files` roughly 20 times
over the same unchanged tree. Each is cheap individually (~50-150ms at 2000
files) but it is ~2-3s of pure duplicated work per check run. Fix: an
`@functools.lru_cache` keyed on `(root, pathspec)` on both functions -- the
tracked set cannot change mid-check.

---

## Proposed new PERF rules

### PERF015 -- "N+1 spawn": loop-VARIANT effectful call inside a loop
**Detection condition**: reuse `frob.perf._effect_summaries.EffectGraph` exactly
as PERF008 does. For each `for`/`while` loop, for each call site attributed to
its innermost enclosing loop, if the callee is directly effectful or
`reachable_effect` is non-None AND at least one argument's source text names the
loop's bound variable(s) or a name assigned in the loop body -- i.e. the exact
NEGATION of PERF008's firing condition -- emit PERF015. Restrict the effect
table to the SPAWN subset only (drop the directory-walk subset), because a
per-iteration walk is a different rule.
**Would have caught**: H1, H3, H5, M1, M2, M3, M7, L1-L4.
**False-positive risk**: HIGH by volume -- my scan found 106 plausible sites
after de-noising, and many (L1, `testing/_runners.py:517` per-language runner,
`natives/_build.py:165` per-crate build) are irreducible: the work genuinely IS
per item. Mitigations: (a) WARN tier with `frob:waive` available, exactly like
PERF008; (b) require the loop's iterable to be plausibly large -- suppress when
the iterable is a literal tuple/list of <=8 elements or a `range(<=8)`, which
kills L1/L2 and the language-runner class outright; (c) suppress when the spawn
argv contains no loop-variant PATH/REV component (i.e. the loop variable only
selects the binary or a flag).

### PERF016 -- git spawn inside a loop whose argv carries a per-iteration pathspec or revision
A narrow, low-false-positive subset of PERF015 and the one I would ship FIRST.
**Detection condition**: a call reaching a spawn whose argv literal list begins
with `"git"` (statically, the first element is the string literal `git` or a
name bound to it), attributed to an enclosing loop, where a loop-variant name
appears in an argv element positioned after a `"--"` separator, or inside an
f-string of the form `f"{rev}:{path}"`, or as the operand of `-S`/`-G`/`--`.
Batching is essentially always available for this exact shape (`git log` takes
many pathspecs; `git cat-file --batch` takes many blobs), which is what makes
the rule actionable.
**Would have caught**: H1, H3, H5, M1, M2, M3, M7.
**False-positive risk**: LOW. The real residue is `git worktree add`/`git mv`
per item (`tickets/_archive.py:566`, `tickets/_store_migrate.py:220`), where
each spawn is a distinct mutation and no batch form exists; exempt mutating
subcommands (`mv`, `worktree`, `commit`, `checkout`, `reset`, `clean`) by name
and the rule is essentially clean.

### PERF017 -- an effect result cache written only on the success path
**Detection condition**: within one function, find a call to a `*_cache`/
`cache_write`/`put_*` writer whose every reachable predecessor path requires a
prior `if <x> is None: return None`-style early exit -- concretely: a function
that (1) reads a cache (a call matching `_read_*cache`/`get_*`) near entry,
(2) reaches a spawn on the miss path, (3) has at least one `return` statement
on a branch dominated by a failure/None test that is NOT dominated by the cache
write. Emit "the failure outcome of this budgeted effect is never memoized, so
the next call repeats it".
**Would have caught**: H2 (the confirmed 76s doable incident), M6.
**False-positive risk**: MEDIUM. A deliberately-uncached failure is legitimate
when the failure is transient (a lock contention, a network blip). Mitigate by
firing ONLY when the spawn on the miss path carries an explicit `timeout=`/
`budget=` keyword -- a budgeted effect that times out at size N will time out
again at size N, which is precisely the non-transient case -- and by keeping it
WARN tier with a reason-bearing waive.

### PERF018 -- a shared, hoisted expensive value discarded by a transitive callee
**Detection condition**: a function `F` binds `v = E(...)` OUTSIDE a loop where
`E` is a known-expensive loader (participating set defined by an explicit
allowlist plus `EffectGraph` reachability: `read_all_leases`, `load_queue`,
`tracked_files`, `build_call_graph`, ...), then calls `G(...)` inside that loop
WITHOUT passing `v`, and `G` (directly or within 2 hops) calls `E` itself. That
is "the hoist exists and a callee defeats it".
**Would have caught**: H4 (the T-4492 regression), and would guard every future
hoist of the same kind.
**False-positive risk**: LOW-MEDIUM. Genuine cases where the callee must see a
FRESH read exist (M4's cluster reload is exactly one). Mitigate by requiring
that `G`'s signature have no parameter of the hoisted value's type/name already
-- if the author already provided a `leases`/`queue` parameter and the caller is
just not using it, that is an unambiguous bug -- and by accepting a
`frob:waive PERF018 reason="must re-read after the preceding write"`.

---

## Notes

**Checked and found correct (do not re-verify)**
- `_mine_done_transitions_v1` (`tickets/_flow.py:184`) and
  `_ledger_commit_history` (`_flow.py:105`): the v1 path already fetches the
  commit list ONCE and reads each blob once; its cost is O(commits), not
  O(tickets x commits). Only the v2 path (H1) is the regression.
- `_find_leaked_tickets` (`tickets/_land.py:5723`): the `read_all_leases` hoist
  itself is correct and the T-4492 comment is accurate; the defect is
  downstream in `_sibling_branch_ref` (H4), not in the hoist.
- `_identity_scoped_state_key` (`_rapid_sweep.py:2276`): no git spawn, hashes
  only the distinct files named in `pairs`; its cost claim is honest.
- `load_all`'s v2 index cache (`tickets/_store.py:1576-1622`) and
  `_store_mode`'s mtime-keyed memo (`_store.py:594` region): both real, both
  correctly invalidated; the residual cost of a repeated `load_queue` is the
  glob+stat, not a re-parse (relevant to M4/M5's sizing).
- `_read_revalidation_cache` (`_rapid_sweep.py:2350`): its exact-pairs and TTL
  checks are sound; it is the missing NEGATIVE write (H2), not the read, that
  is broken.
- `_maybe_drop_resolved_ticket` (`_rapid_sweep.py`): does NOT spawn per ticket
  in the common case; it only spawns on an actual drop (`drop_ticket` +
  commit). The 231-candidate loop at `_rapid_sweep.py:3684` is cheap; the cost
  is entirely the single budgeted re-check.
- PERF008's own exemption logic (`perf/_loop_effects.py`) is correctly
  implemented and correctly documented; it is a scope gap, not a bug.

**Deliberately skipped / only skimmed**
- Non-Python sources (TS/Rust/C++ under `natives/`, `check/_ts.py`'s toolchain
  shims): PERF001-008 are Python-first by design and the two incidents are both
  Python; not scanned.
- `src/frob/arch/`, `src/frob/vet/`, `src/frob/lang/`, `src/frob/dup/`: the
  scan produced ~150 hits in these packages, but every one I sampled resolved
  to `ast.walk`/tree-sitter `walk`/`re.search` name collisions with my spawn
  table, not a process spawn. I dropped the whole `walk`/`search`/`_scan`
  name class rather than triage 150 known-false hits; a residual real spawn in
  those packages is possible but I found none in the sample.
- `tests/` and `.claude/worktrees/`: out of scope entirely.
- Shape E beyond L4/L5: I counted `git ls-files`/`rglob`/`os.walk` call sites
  (115 repo-wide, grep-level) but did not build a per-entry-point execution
  count for `frob check`, so "how many whole-repo walks does one `frob check`
  actually perform" is UNMEASURED. L5's ~20 is a call-site count, not a
  measured spawn count -- a `FROB_TRACE`-style spawn counter on a real
  `frob check` run would settle it and is the cheapest next measurement.
- I did not run `frob ticket flow` or `frob ticket doable` to reproduce
  timings; H1/H2 wall-clock numbers are the ones supplied in the task brief,
  and my contribution is the mechanism (the specific loops and the missing
  cache write), which I did verify in source.
- Runtime/dynamic rules (`perf/_profile.py`, `_sampler.py`, `_heat.py`,
  `_ratchet.py`) were not audited; this pass is about static shapes A-E.