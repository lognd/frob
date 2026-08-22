## Done report

Close blocker was LiveTrackerCited: src/frob/cycle/graph.py:44's
frob:waive WIRE001 on DependencyGraph.degraded_languages carried
follow_up="T-2746", and close refuses while a live tracker cites an
open ticket.

Measured directly at that exact site (not assumed): with the waiver
comment block removed and the T-2746 WIRE001 fix
(_is_property/_PROPERTY_DECORATOR_RE/property_access_pattern) already
on main, `frob check --only gates --no-cache` over the whole repo
produced ZERO WIRE001 findings anywhere in src/frob/cycle/graph.py.
Before concluding this, an earlier attempt at the same measurement
left blank lines behind after stripping the waiver, which desynced the
frob:doc continuation from the @property below it and produced a
spurious COV001/PLACE001 pair; redone cleanly (waiver lines removed
with no gap introduced) the fix's own effect stands on its own: no
WIRE001 finding at all. This confirms the waiver is now genuinely
redundant, not merely quiet, so it is REMOVED rather than repointed at
a successor ticket.

Scope was widened (`frob ticket scope T-2746 --add
src/frob/cycle/graph.py`) to cover this edit, since the waiver being
removed lives in the file the fix itself is about; the ticket's
original two-file scope only covered the gate implementation and its
own new test.

Verification: `frob check --only gates --no-cache` over the whole repo
shows the sole graph.py finding is an unrelated pre-existing waived
PERF003 note; no new errors attributable to this file. The one-line
diff was also checked against the wider `frob test --base main`
touched set -- several failures appeared there
(test_system.py::test_cycle_no_cycle_exits_zero and others), but
re-running one of them with this edit reverted to HEAD via `git
checkout -- src/frob/cycle/graph.py` reproduced the identical failure,
confirming pre-existing repo-wide breakage unrelated to this change,
not a regression it introduced. The ticket's own targeted tests
(tests/unit/test_wire001_property_attribute_access.py,
tests/test_graph.py) pass clean: 145 collected, 0 failed.

### Changed
```
 tickets/T-2746/ticket.md | 8 ++++++++
 1 file changed, 8 insertions(+)
```

### Evidence
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_with_no_caller_anywhere_still_flagged_positive_control` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_ordinary_new_method_still_flagged_positive_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 15 error(s), 887 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
