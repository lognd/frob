## Done report

Investigated wiring verify_imports=True into DEAD001 (T-2205's first named
consumer), per the ticket's own instruction to measure and judge before
wiring, and to stop rather than push through if a delta looks wrong.

Measured, DEAD001 only, before/after wiring
src/frob/gates/_dead_symbols.py's `build_reference_graph(root, files)`
call to `verify_imports=True`:

  before: 46 findings
  after:  60 findings (14 new, 0 disappeared)

Judged each of the 14 new findings individually (not just counted). At
least 12 of 14 are FALSE POSITIVES from a single systemic root cause, not
independent flukes:

`frob.lang._extract._python_import_specifiers` only reads the
`module_name` field off a python `import_from_statement` node and drops
every imported NAME. For `from frob.arch import (_python, _cpp,
_patterns, ...)` (src/frob/arch/__init__.py) this yields specifier
"frob.arch" only -- never "frob.arch._python" etc -- so
`resolve_local_import` lands on `arch/__init__.py` itself, never the
submodule files the statement actually names. Same shape recurs with
`from frob.app import ticket_runner as _ticket_runner`
(src/frob/app/ticket_runner/_close_cmd.py/_land_cmd.py/_new.py).
Confirmed by direct grep that every one of these symbols DOES have a real
caller, via exactly this import form:
  - src/frob/arch/_python.py::_check_long_functions/_check_god_classes/
    _check_high_coupling/_check_deep_nesting (arch/__init__.py)
  - src/frob/arch/_cpp.py::_check_long_functions/_check_god_classes
  - src/frob/arch/_abstraction.py::_extract_signatures/
    _collect_file_dispatch_refs/_check_abstraction_opportunities
  - src/frob/arch/_patterns.py::_check_type_switch/
    _check_scattered_construction
  - src/frob/app/ticket_runner/__init__.py::_graph_snapshot (called from
    3 sibling files)

`from package import submodule` is a common Python idiom, not an edge
case -- wiring any of the three named consumers (DEAD001, COV006,
PROTO001-005) against the current `_local_imports_by_path` primitive
would silently mark live symbols dead, exactly the "reporting LIVE
symbols as dead -- silent and destructive" failure direction the
ticket's own acceptance criteria call out as unacceptable. COV006 and
PROTO001-005 share the identical primitive, so wiring them would hit the
same defect; not attempted, per the "stop and report rather than wire
the rest" instruction.

Filed T-2211 (blocking, scope src/frob/lang/_extract.py,
src/frob/lang/_nodes.py, src/frob/graph/callgraph.py -- all outside
T-2205's own scope) with the full repro. T-2205 is blocked by
T-2211 rather than closed done; the DEAD001 wiring edit was
made, measured, judged unsound, and reverted -- no wiring change ships
from this ticket. `git status`/`git diff` against main show zero
production code changes; only the ticket ledger (this ticket's own
transitions, T-2211's filing, and the block edge) is new.

Changed: none (production code) -- src/frob/gates/_dead_symbols.py was
edited, measured, and reverted to its pre-ticket state; tickets.md only.
Evidence: tests/test_graph.py::TestCallGraph::
test_build_reference_graph_catches_dispatch_table_entry (--accepts 0;
this is an investigation ticket with no new production surface of its
own -- the existing build_reference_graph test is the closest bound
evidence per playbook section 5's docs/investigation-ticket precedent).
Filed: T-2211 (blocking follow-up bug, renumbers at land).
Gates: no gate-affecting production change to check; `frob check --only
gates-fast --ticket T-2205` not meaningfully applicable to a reverted
diff.

### Changed
```
 tickets/T-2205/ticket.md           | 11 ++++-
 tickets/T-2211/ticket.md | 90 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 99 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2205/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2205/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
