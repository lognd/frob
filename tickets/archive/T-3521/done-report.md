## Done report

DEAD001 burn-down for T-3521. Measured 2026-08-30 via `uv run frob check
--only dead_symbols --json`, filtering severity=warning:

Before: 22 findings in scope (23 total minus src/frob/serve/_socketd.py,
dropped from scope at start-time -- it collides with T-3506's in-progress
lease, left for that ticket's own holder).
After: 0 findings in scope. gate:DEAD: 0 errors, 2 warnings (both
out-of-scope: _socketd.py and src/frob/tickets/_leases.py, the latter a
NEW finding that appeared on re-measurement, also out of scope), 28
waived.

Every finding reviewed individually, not blanket-waived:
- 15 genuinely wired, call-graph resolution gaps (named the real caller
  in each waiver): 12 module-attribute-qualified cross-module calls
  (frob.arch's _cpp/_patterns/_python check functions dispatched as
  _cpp.foo()/_python.foo() from arch/__init__.py), one functools.partial-
  wrapped cross-module call (_load_parser_factory_from_root), one direct
  cross-module imported-name call the resolver still misses
  (_cpp_symref_qualname), one with an existing frob:tests directive
  DEAD001's own resolver does not match (_resolve_via_git_rename).
- 2 deliberately-kept, currently-unreached scaffolding, waived with their
  own documented intent: _qualname_stack (its own docstring already says
  "placeholder... not referenced elsewhere"), _ticket_state_on_main
  (T-2125's documented fallback/reference implementation -- also
  corrected its stale "still exercised by its own unit tests" docstring
  claim, which did not hold up to a grep).
- 2 real wiring/design gaps, waived and filed as follow-ups rather than
  silently accepted: _save_unlanded_summary_cache's own docstring
  documents an intended _reconcile.py production caller that was never
  actually added (filed T-3522, out of this ticket's _query.py-only
  scope to fix); _cross_node_referenced_symbols is claimed by a T-1870
  comment to be a SYS106 dependency, but SYS106 was never wired to call
  it anywhere in the repo (filed T-3523).
- 2 genuinely dead, deleted: _py_except_exception_type (T-2539 orphaned
  it in favor of the plural _py_except_exception_types, zero remaining
  callers or tests), and tests/unit/strata/test_litmus_cwe.py's own
  duplicate _repo_root helper (unlike every sibling litmus test file,
  this one's _LITMUS_DIR never calls it).

Did NOT promote DEAD001 WARN -> ERROR: 2 findings remain in files this
ticket could not touch (src/frob/serve/_socketd.py, leased by in-progress
T-3506; src/frob/tickets/_leases.py, out of scope and newly appeared on
this measurement) -- the family is not at a genuine repo-wide zero yet.
A follow-up can promote once those two are reviewed.

Filed: T-3522 (wire _save_unlanded_summary_cache into _reconcile.py),
T-3523 (SYS106 never wires _cross_node_referenced_symbols/
_node_real_public_surface).

### Changed
```
 src/frob/_cli_parsers/_root.py                |  1 +
 src/frob/app/ticket_runner/_query.py          |  1 +
 src/frob/arch/_abstraction.py                 |  3 +++
 src/frob/arch/_cpp.py                         |  2 ++
 src/frob/arch/_patterns.py                    |  2 ++
 src/frob/arch/_python.py                      | 12 ++++--------
 src/frob/gates/_docblocks_refs.py             |  1 +
 src/frob/gates/_fix_engine.py                 |  1 +
 src/frob/graph/summary.py                     |  1 +
 src/frob/lang/_common.py                      |  1 +
 src/frob/strata/_selfconform_surface_rules.py |  1 +
 src/frob/tickets/_unlanded.py                 | 13 ++++++++-----
 tests/test_measure_evidence_reach.py          |  1 +
 tests/unit/strata/test_litmus_cwe.py          | 11 -----------
 tickets/T-3521/ticket.md                      |  5 +++++
 15 files changed, 32 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/unit/test_unlanded_branch_work.py::TestUnlandedBranchWork::test_confirmed_leak_shape_done_report_plus_in_progress` (pytest node id, verified passing when recorded)
- `tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain::test_runs_clean_over_a_minimal_ticket_ledger` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestLoadParserFactoryFromRoot::test_resolves_fresh_from_root_not_the_process_import` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 18 error(s), 4162 warning(s), 895 waived
- error-findings: ARCH103@src/frob/tickets/_leases.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3521/tests/unit/strata/test_litmus_cwe.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
