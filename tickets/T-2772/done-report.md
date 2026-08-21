## Done report

`_possible_enforcement_symbols` (src/frob/app/ticket_runner/_new.py:730)
hardcoded the git grep pathspec "src/frob/**/*.py" for its "suggest an
existing _refuse_/_check_ function with a similar name" heuristic --
silently returning () in every sibling repo whose package is not
src/frob/, indistinguishable from a genuine no-match result (T-2384/
T-2391's silent-pass doctrine).

Retargeted onto frob.lang.declared_source_prefixes (T-2195/T-2389's
promoted resolver, the same one T-2389 wired _env_var_docs.py onto) --
no second resolver written. When the resolver cannot determine the
project's own source prefix (pyproject.toml [project].name missing/
unreadable), the function now logs a distinct WARNING naming the
UNRESOLVED cause before returning (), rather than collapsing into the
same silent empty result a genuine no-match grep produces -- there is no
Violation/Severity model at this call site (it is a ticket-authoring
hint, not a gate), so the log line is the fail-loud signal available at
this layer.

Positive controls, both directions, both new pytest fixtures (not
assumed):
- must-now-fire: TestPossibleEnforcementSymbolsRetargeted::
  test_fires_for_a_differently_named_project -- a lograder-named
  src-layout fixture (deliberately no src/frob/ path in the fixture)
  whose _refuse_bogus_widget function is now surfaced; before this
  retarget the hardcoded src/frob/ pathspec matched nothing in it.
- must-still-pass: TestPossibleEnforcementSymbolsRetargeted::
  test_still_fires_for_this_repos_own_src_frob -- re-runs the ORIGINAL
  T-1995 fixture (this repo's own real root, same title/body,
  _refuse_over_broad_scope_on_start) and confirms the same symbol is
  still surfaced after the retarget -- proves the fix is not a loosened/
  blinded check.
- The pre-existing TestPossibleEnforcementSymbolsCue class (unchanged)
  also still passes: 12/12 collected in tests/unit/test_ticket_new_
  related.py.

Note: git's "**/*.py" pathspec glob requires at least one intermediate
directory component to match a file (verified directly against this
git version, 2.34.1) -- the must-now-fire fixture nests its target file
one level under src/lograder/ for exactly this reason, matching how the
ORIGINAL hardcoded src/frob/**/*.py literal was already exercised only
against this repo's own nested package tree; this is a pre-existing
pathspec-glob property, not something this retarget introduces or
changes.

Filed: none.

### Changed
```
 tickets/T-2772/ticket.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 844 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@tests/unit/test_ticket_new_related.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2772, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
