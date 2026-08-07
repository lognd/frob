## Done report

Decomposed _build_jobs (201 lines, ARCH001 threshold 60) into three
functions: _build_jobs itself now only does selection/force-drift/
cache-substitution/return (~49 lines), and two new extracted builders
carry the actual dict-literal assembly this ticket's plan named:
_build_thread_jobs(st) (the thread-pool half -- drift, coverage,
invariant, test, policy, doclink, docanchor, docblocks, fuzz, release,
decisions, tickets, compliance, debt, deprecated, excludehazard, refs,
parse_failures, registry, lang_conformance, lang_project_conformance,
fmt, affect_drift) and _build_process_jobs(st) (the process-pool half --
perf, clones, sys, secrets, taint, opaque, archgate, exhaustive_handling,
ffi_boundary, pii_structural, walk_lint, cve_fingerprint_scan,
render_lint, dead_symbols, protocol_summary).

Both new functions take the same `st: _GateInputs` this ticket's plan
suggested (one builder per concern -- always-run set / process-pool set
-- rather than three-way, since the thread-pool dict genuinely is one
concern: cheap, I/O-bound gate closures over the same state; the
ticket-scoped set is already its own function, _build_ticket_scoped_jobs,
unaffected by this change).

No public API changed: `_build_jobs`'s signature and return shape are
identical; `_build_thread_jobs`/`_build_process_jobs` are private,
internal-only helpers with no external caller (verified via grep -- only
`_build_jobs` itself calls them).

git diff main --diff-filter=D --stat: empty (no unintended deletions).
Full tests/test_gates.py: 508 passed (FROB_WORKTREE/FROB_AGENT unset per
playbook 5b, same env-leak caveat as T-1077's Done report).
frob check --ticket T-1049 --only arch: 0 errors, ARCH001 no longer
fires on _build_jobs (grep-confirmed absent from output); 18 pre-existing
warnings + 232 suggestions, none new.
frob check --ticket T-1049 --only drift/--only test: 0 errors both runs;
pre-existing DRIFT001/TEST003 waived entries unrelated to this change.

### Changed
```
 src/frob/gates/__init__.py | 76 +++++++++++++++++++++++++++++-----------------
 tickets.md                 | 52 ++++++++++++++++++++++++++++++-
 2 files changed, 99 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
