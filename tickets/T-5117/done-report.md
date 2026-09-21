## Done report

# T-5117 done report rationale

Third bottleneck in this family (after T-5036's repo_root memoization and
T-5075's leases-snapshot threading): `_leased_by_one_holder` calls
`over_broad_literal_globs(root)` once per (candidate ticket, in-progress
lease-holder) pair despite already receiving a precomputed breadth tuple
for that same call (the T-0453 pattern). `over_broad_literal_globs` ->
`declared_source_prefixes` -> `Path.resolve()` ran real filesystem
syscalls fresh on EVERY one of those O(tickets x leases) calls.

T-4646 already memoized the two calls `declared_source_prefixes` makes
internally (`declared_project_package_name`'s underlying `_pyproject_
data` read, and `_declared_python_source_roots`'s own `lru_cache`), but
`declared_source_prefixes`'s OWN body -- a `Path.resolve()` pair per
declared source root -- still ran fresh on every call, and
`over_broad_literal_globs`'s own frozenset-union/logging work on top of
that also ran fresh every call.

Fix: memoize both functions per-root, invalidated by the same
`pyproject.toml` mtime signal `frob.lang._nodes._pyproject_data` already
uses (split into a small shared `_pyproject_mtime_signal` helper in
`_nodes.py` to avoid a second hand-rolled copy there; `_models.py` reads
the file's own mtime directly rather than importing a private
cross-module helper, since `declared_source_prefixes` is the only public
symbol this module already imports from `frob.lang`).

Measured (5000 calls to `over_broad_literal_globs(root)` against this
repo's own root, a direct microbenchmark of the per-pair cost the audit
named):
  - BEFORE (parent commit 9f8764eea5, unfixed): 0.604s (0.1209 ms/call)
  - AFTER (this fix): 0.072s (0.0144 ms/call)
  - ~8.4x per-call speedup.

Acceptance [1] (`test_real_repo_ledger_is_tick008_clean` completes well
within its Windows CI timeout "with T-5036 and T-5075 also applied") was
NOT bound to this ticket's evidence: that specific test still hangs in
this worktree today, but for an UNRELATED reason already diagnosed and
fixed by a sibling ticket this same session -- T-4641 (bounded-fixture
fix for a catastrophic `_FENCE_RE` regex scan in `frob.gates.
_empty_diff_close`, filed as T-5160) -- which has not yet
landed to `dev` as of this report. Verified directly: running that test
alone in this worktree still does not complete within 60s, with a
traceback pinned inside `repo_root`/`Path.resolve()` via the SAME full
`tickets_gate` dispatch T-4641's own investigation already traced past
this ticket's own fixed functions. Re-running that specific acceptance
criterion once T-4641 (or at minimum its `_FENCE_RE` fix) lands to `dev`
is the correct follow-up, not something this ticket's own fix can
independently satisfy standalone.

Repro test (BUG002 evidence): `tests/unit/test_pyproject_data_
memoization.py::TestPyprojectDataMemo::
test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs`
monkeypatches `Path.resolve` and asserts a constant (<=4) call count
across 10000 (candidate, lease-holder) pairs. `frob ticket evidence
--check-repro`'s default parent-commit resolution cannot get a real
verdict here for the same commit-ordering reason T-5131's own evidence
already documented (the fix commit landed before the repro test's own
commit in this branch's linear history). Verified manually instead:
`git worktree add --detach` at the ticket's pre-fix parent commit
(9f8764eea5), copied only the new test file in, ran it there against
the unfixed code -- FAILED with `KeyError: '_declared_source_prefixes_
cache'` (the cache this ticket's fix introduces does not exist pre-fix,
confirming the fix is what makes the test collectible AND passing); the
same test against the fixed code in this worktree PASSES. Designated via
`--designate-repro-force` with this reasoning recorded in the ticket's
`designated_repro_changes` audit trail.

### Changed
```
 src/frob/lang/_nodes.py                       | 88 ++++++++++++++++++++-------
 src/frob/tickets/_models.py                   | 55 +++++++++++++++--
 tests/unit/test_pyproject_data_memoization.py | 41 +++++++++++++
 tickets/T-5117/ticket.md                      | 21 ++++++-
 4 files changed, 177 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_derives_package_prefix_for_a_differently_named_project` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_this_repos_own_src_frob_globs_are_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_scales_across_many_candidates_and_leases` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs` (pytest node id, verified passing when recorded)
