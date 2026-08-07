## Done report

`frob ticket doable` is now collision-aware (scope-lease model): it excludes
queued/planned tickets whose scope overlaps any in-progress ticket's lease,
via a SOUND glob-set intersection (_globs_intersect DP, scope_overlap) --
tests/** and docs/ are NOT special-cased out (only tickets.md is, since the
merge driver owns it). The over-hiding is fixed at the SCOPE-DECLARATION
level: a LARGE-GLOB WARNING (large_glob_warnings / _over_broad_scope_entries,
tunable via frob.toml [tickets] large_glob_max_files=25) flags over-broad
scopes (tests/**, src/frob/**, or a glob matching >N files) and nudges
narrowing; a holder's over-broad entries demote to warn-only while its
precise entries still hard-block real collisions. `--show-blocked` explains
each exclusion, `--ignore-lease` returns the raw list, both wired through
__main__ argparse.

PERF (coordinator-caught before landing): the first cut's _repo_files did
root.rglob("*") -- walking .git/.venv/the ~129 .claude/worktrees/ checkouts,
re-derived per candidate x holder -- making doable take MINUTES. Fixed:
_repo_files_git uses `git ls-files` (tracked only), scope_breadth_context
computes the (threshold, files) set ONCE and threads it through, the file
count switched from a per-file fnmatch loop (624k calls) to fnmatch.filter,
and .claude/worktrees/.git/.venv are excluded unconditionally. Measured
~0.7-0.9s on the real repo (was minutes). This motivated T-0471 (WALK-lint)
so an unpruned rglob can never recur. UX: doable prints an "Active leases"
section and, when empty, "zero doable tickets (no available lease found in
repo tree; starting any ticket would conflict with a ticket in progress)".

Evidence (3 of 24 tests): breadth-context-uses-git-ls-files (perf-guard),
precise-in-progress-does-not-hide-disjoint (the corrected non-over-hide),
large-glob-silent-on-precise-test-file. Retires the coordinator's manual
collision-blocklist maintenance. Landed via 3-way + new-file copy
(test_tickets_lease.py). Note: this is why the parked T-0160/T-0187 epics
were requeued -- their broad leases would otherwise dominate the filter.
