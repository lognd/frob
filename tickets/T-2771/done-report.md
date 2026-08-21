## Done report

Changed:
src/frob/tickets/_models.py::OVER_BROAD_LITERAL_GLOBS
src/frob/tickets/_models.py::over_broad_literal_globs
src/frob/tickets/_doable.py::_over_broad_scope_entries
src/frob/tickets/_doable.py::large_glob_warnings
src/frob/tickets/_doable.py::_leased_by_one_holder
src/frob/tickets/_doable.py::_narrow_scope_files
src/frob/tickets/_doable.py::already_landed_markers
src/frob/tickets/_new_renumber.py::_worst_over_broad_multiple

`OVER_BROAD_LITERAL_GLOBS` used to hardcode "src/frob/**"/"src/frob/" --
inert off-repo (a sibling repo's own package prefix never got the
chronically-over-broad nudge). It now holds only the repo-convention
literals (tests/**, tests/, docs/, docs/**); a new `over_broad_literal_globs(root)`
unions those with `root`'s own package-prefix globs derived from the
existing `frob.lang.declared_source_prefixes` resolver (T-2195/T-2389),
following the same UNRESOLVED-vs-empty-result discipline T-2772 used for
the identical resolver. Threaded `root`/the derived set through every
call site that used to check membership against the module constant
directly (`_over_broad_scope_entries` now takes an explicit `literal_globs`
param, defaulting to the old constant for callers outside this module).

Evidence (both directions per the ticket's acceptance text):
- must-now-fire: tests/test_tickets_lease.py::TestOverBroadLiteralGlobs.test_derives_package_prefix_for_a_differently_named_project
  -- a src-layout fixture project named "lograder" (own pyproject.toml,
  src/lograder/**) now gets the chronically-over-broad nudge on
  src/lograder/**, which it never did before this change.
- must-still-pass control: tests/test_tickets_lease.py::TestOverBroadLiteralGlobs.test_this_repos_own_src_frob_globs_are_unchanged
  and TestLeasedBy.test_over_broad_lease_demotes_to_warn_only -- this
  repo's own src/frob/**-shaped scope still gets the identical nudge/
  demotion behavior as before the retarget.
- UNRESOLVED fallback: TestOverBroadLiteralGlobs.test_unresolved_package_name_falls_back_to_repo_convention_literals
  -- no pyproject.toml at all still falls back to the repo-convention-only
  literals (never a silent "this project has none").
- tests/unit/test_new_ticket_over_broad_scope_warning.py's two `src/frob/**`
  fixtures (test_over_broad_scope_warns_at_filing_time,
  test_severity_scales_with_a_catastrophic_match_count) updated with the
  now-required pyproject.toml declaration and re-verified green.

Filed: none -- no out-of-scope discoveries.

Gates: `frob check --ticket T-2771` clean of every ticket-attributable
finding after fixes (ruff-check E501 x3, AFFECT001 x3, COV002 x4, DOC007
x2, SCOPE001 x2, PRE001 all resolved); remaining reported findings are
pre-existing repo-wide noise unrelated to this diff (verified by file/
symbol -- none touch _models.py/_doable.py/_new_renumber.py/docs/modules/
tickets.md/the two test files). `frob test --base main` ran the touched
set: 14 python test(s), exit=0.

### Changed
```
 tickets/T-2771/ticket.md | 43 ++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 42 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_derives_package_prefix_for_a_differently_named_project` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_this_repos_own_src_frob_globs_are_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_unresolved_package_name_falls_back_to_repo_convention_literals` (pytest node id, verified passing when recorded)
- `tests/test_tickets_lease.py::TestLeasedBy::test_over_broad_lease_demotes_to_warn_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_over_broad_scope_warns_at_filing_time` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_severity_scales_with_a_catastrophic_match_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 19 error(s), 1111 warning(s), 712 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
