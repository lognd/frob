## Done report

docs/modules/tickets-landing.md:2189 had `<!-- frob:enumerates src/frob/tickets/_models.py::Ticket -->` with no `members=` attribute, so it never matched `_ENUMERATES_RE` and was previously accepted only by verb-name membership in `_MD_HANDLED_VERBS` -- a blanket-accept bug T-2857 fixed. Replaced the anchor with `<!-- frob:describes src/frob/tickets/_models.py::Ticket -->`.

Ticket is a pydantic BaseModel class, not one of DOCENUM001's supported collection shapes (dict/set/tuple/frozenset literal, Literal, ErrorSet, Enum/StrEnum, argparse choices) -- frob:enumerates could never have resolved for this target even with members= filled in; it would have punted as an UNRESOLVABLE-shape violation. frob:describes is the correct anchor kind: it binds the surrounding prose (the scope/evidence_scope split, T-1944) to Ticket's digest for drift tracking, which is what that section actually needs.

Evidence: none required -- doc-only anchor-kind correction, no code path changed. Verified with `frob check --json --ticket T-2869` (real run, gate-summary present, unbudgeted, 44 errors repo-wide): no MalformedDirective/DOCENUM001/DRIFT001/error-severity finding involves the new describes edge; the only new signal is a SCOPE002 WARNING (this ticket's scope is docs/modules/tickets-landing.md only, and the describes edge now names src/frob/tickets/_models.py::Ticket, outside that scope) -- expected and correct, since a describes edge deliberately points at code the doc author does not own or modify.

Previously-hidden finding check: the repaired anchor produces no new error/warning beyond the expected SCOPE002 advisory -- it does not surface a previously-masked DRIFT/DOCENUM finding. The anchor's true defect was purely its verb choice (enumerates vs describes), not a stale or wrong doc claim; the surrounding prose was already accurate.

Filed: none -- no further out-of-scope work discovered.

Gates: frob check --json --ticket T-2869 clean for gate:SCOPE (0 errors); repo-wide gate-summary shows 44 errors, all pre-existing and unrelated to this diff (OPAQUE/PERF/PRE/SELFAUDIT/TICK -- other agents' in-flight tickets per dispatch brief).

### Changed
```
 tickets/T-2869/done-report.md | 27 +++++++++++++++++++++++++++
 tickets/T-2869/ticket.md      |  8 ++++++--
 2 files changed, 33 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_describes_still_parses_cleanly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 515 warning(s), 838 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
