## Done report

## Correction to the ticket as filed (my own measurement, done FIRST)

T-2018 was filed believing this was a SURFACING problem -- that
`attribute_batch`/the reference-graph engine worked and merely was not
advertised where a finding is reported. Measured directly, this is
wrong: the real defect is REACHABILITY, not discoverability.

Exact measurement, taken before any fix:
```
$ frob verify status
watermark:        (none yet)
unverified depth: 0
quarantine:       clear

$ frob verify explain COV003:tickets/T-0907
ERROR: verify explain: verify queue is empty, nothing to attribute against
```
`frob verify explain` (`src/frob/app/verify_runner.py::_run_explain`)
refuses UNCONDITIONALLY whenever `frob.verify.queue_status(root)` (the
persisted `.frob/verify-queue.json`) is empty -- it never falls back to
real git history, never attempts a build against candidate commits
outside that one durable-but-often-empty queue. The queue is empty
whenever no rapid-sweep cycle has enqueued the specific commit that
caused a finding, OR whenever the watermark has already advanced past
it (`compact_queue` drops entries the watermark covers). In THIS repo,
right now, it is empty because nothing has enqueued anything yet. The
engine (`attribute_batch`) was never broken; the ONLY caller that could
reach it for an ad-hoc, already-in-hand finding refused before ever
calling it.

## Fix

`frob.verify._attribution.build_ad_hoc_batch(root, snapshot=..., since=None,
limit=50)` (new): walks candidate commits via `frob.gitio.recent_commits`
(every commit since a watermark sha when one exists, else a bounded
recent window for a cold start), computes each candidate's own diff via
the new `frob.gitio.commit_diff` (the commit-relative sibling of
`working_diff`), and resolves the symbols each commit touched -- the
same span-overlap join `frob.tickets._land._touched_symrefs_for_intent`
performs at land time, duplicated locally per that function's own
documented DUP001 precedent (a cross-package private import back into
`frob.tickets` from `frob.verify` is worse coupling than one small,
stable function living in each of its two natural homes). The result
feeds `attribute_batch` UNCHANGED -- `build_ad_hoc_batch` only widens
WHERE the candidate batch comes from, never how reachability or
ambiguity is decided. `frob.verify.load_attribution_context(root)` is
the public seam a caller builds ONCE and threads through both
`build_ad_hoc_batch` and `attribute_batch`'s own `graph_and_calls=`, so
one `frob verify explain` invocation pays for exactly one graph
load/build, never two.

`src/frob/app/verify_runner.py::_run_explain`/`_explain_batch`: no new
verb. `frob verify explain` now merges the persisted queue (real
recorded land intents, priority on a duplicate sha) with the ad-hoc
batch, and only refuses if BOTH are empty. Constraints from the
original ticket body, honored:
- Attribution still never runs as part of `frob check --only gates` --
  confirmed by grep: zero references to `build_ad_hoc_batch`/`load_
  attribution_context` anywhere under `src/frob/gates/` or `src/frob/
  app/check_runner.py`. Only the opt-in `frob verify explain` path pays
  the cost.
- Ambiguity is NEVER resolved by a guess: `attribute_batch` itself is
  untouched, so two candidate commits reaching the same symbol still
  report `unattributed` with both shas named
  (`test_ambiguous_two_commits_reach_the_same_symbol_is_unattributed`).
- `attribute_batch` is not duplicated anywhere -- only its `batch`
  argument now has a second real data source.

## Worked example: T-0907, live

```
$ frob verify explain COV003:tickets/T-0907
...
WARNING: attribution: COV003 at tickets/T-0907 UNATTRIBUTED (no batch
commit's touched symbols reach this finding); candidates=()
UNATTRIBUTED
candidate commits: []
```
No longer refuses -- runs 50 real candidate commits against the real
call graph and reaches an honest verdict. This specific finding remains
UNATTRIBUTED because `tickets/T-0907` is a ticket-ledger path, not a
source file the symbol graph indexes at all (`_resolve_symbol`/
`_symbols_in_file` find nothing there by construction) -- a genuine,
structural limit of SYMBOLIC attribution for a finding whose site is a
non-code file, not a defect this ticket introduces or could fix without
teaching the graph to index ticket prose (out of scope). Demonstrated
the POSITIVE path against a real source finding from this same session
(`COV002:src/frob/app/_config_external.py:693`, T-2004's own new
function): two real candidate commits both reach it, correctly reported
`unattributed` with BOTH shas named -- never a guess -- exactly the
"do not guess" constraint working as designed on real, live data.

## Do-not-fix-it-this-way constraints, honored
- Not a playbook/dispatch-brief entry -- a function plus a wired code
  path, exercised by 13 new tests that run in CI.
- No `frob check`-path cost: measured `frob verify explain` itself at
  ~36s wall-clock (mostly graph build on a cold cache + ~50 `git diff`
  subprocess spawns for the ad-hoc candidate range) -- entirely inside
  the opt-in explain path; `frob check --only gates` is untouched by
  this diff (verified by the grep above, not merely reasoned).
- No newest-commit tiebreak anywhere in the new code -- `attribute_batch`
  itself is the only place ambiguity is decided, and it is unmodified.
- No duplication of `attribute_batch` -- only a new batch SOURCE.

Evidence: 13 pytest node ids across tests/test_gitio.py (commit_diff/
recent_commits), tests/unit/verify/test_attribution.py (build_ad_hoc_batch/
load_attribution_context, including a real end-to-end git-repo
integration test and the ambiguous-case regression guard), and
tests/unit/verify/test_verify_runner.py (the `_run_explain` ad-hoc
fallback, reproducing the exact measured "queue is empty" precondition
and asserting it no longer refuses).

Filed: none.

Gates: `frob check --ticket T-2018` -- gate:SCOPE/COV(diff)/AFFECT/FMT/DUP
all clean (0 errors) after fixing genuine COV001 (missing frob:doc on
two new public functions -- added a new docs/modules/testing.md section,
since docs/modules/tickets.md, this package's usual doc home, was under
a live cross-worktree lease from T-1696 for this ticket's whole
duration), DUP001 (a well-established repo-wide `_init_repo`-shaped test
helper, waived with the same reasoning a dozen+ other test files
already carry), TEST001 (added direct unit coverage for `load_
attribution_context`), and SELFAUDIT001/SYS111 (two new declared
capability sites in the new test file -- registered in `design/frob.
strata`'s testsuite node exec/fs.write via-lists, ratchet ceiling bumped
by exactly 1 each in `docs/design/registry/capability-via-ratchet.
lock.json` with a T-2018 reason) this ticket's own diff surfaced.
Remaining repo-wide FAILs in the same run (gate:ARCH 2 errors at
`_rapid_sweep.py`, gate:COV 1 error at tickets/T-0907) are the same
pre-existing baseline already disclosed in this series' earlier reports
(T-1925/T-1927/T-2004/T-2010), confirmed unrelated by file path -- none
in this ticket's touched set.

### Changed
```
 frob.toml                     |  17 +++++++
 rapid-debt.jsonl              |   4 ++
 tickets/T-2010/done-report.md |  44 +++++++++++++++++
 tickets/T-2010/ticket.md      |  13 ++++-
 tickets/T-2018/ticket.md      | 108 +++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 184 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gitio.py::TestCommitDiff::test_single_commit_reports_its_own_hunk` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestCommitDiff::test_root_commit_has_no_parent_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestRecentCommits::test_since_none_returns_limit_bounded_recent_commits` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestRecentCommits::test_since_a_sha_returns_only_commits_after_it` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_covers_a_commit_the_persisted_queue_never_saw` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_end_to_end_attributes_through_attribute_batch` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_commit_touching_no_resolvable_symbol_is_omitted` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_since_bounds_the_candidate_range` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_ambiguous_two_commits_reach_the_same_symbol_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_unreadable_git_history_degrades_to_empty_batch` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestLoadAttributionContext::test_returns_a_usable_snapshot_and_call_graph` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_attribution.py::TestLoadAttributionContext::test_build_failure_is_graph_unavailable` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestRunExplainAdHocFallback::test_empty_persisted_queue_still_attributes_via_ad_hoc_history` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, COV003@tickets/T-0907, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py
