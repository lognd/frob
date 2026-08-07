## Done report

Investigated the 4 pre-existing unbound NEGEXIST001 claims T-1229's Done
report disclosed: docs/modules/gates.md:50, :91, :456, docs/modules/
graph.md:384. gates.md:50 (DEC001) and :91 (REF003) are rule-catalog
table rows describing those gates' own "points at a missing record"
semantics -- the heuristic false-positived on their definition prose,
not a real "frob X doesn't exist yet" claim, so reworded rather than
bound. gates.md:456 (T-0809's RAII escaped/acquired cross-check) and
graph.md:384 (T-0686's may-raise engine) are genuine disclosed gaps with
no open ticket naming the work -- rather than fabricate a placeholder
ticket just to satisfy frob:until, reworded both to state the fact
plainly ("left unwired" / "has no implementation") without matching
_NEGEXIST_PHRASE_RE, per the wave brief's explicit "bind ... or reword;
do not blanket-waive" instruction.

Verified via `frob check --only docblocks`: none of the 4 original
locations fires NEGEXIST001 any more (docs/modules/gates.md/graph.md
absent from the finding list). The gate itself still reports other,
out-of-scope findings across the rest of the repo -- untouched, a
separate burn-down not requested here.

Note: the actual doc wording for all 4 locations was already present on
main by the time this ticket was picked up (a prior, unticketed pass
carried the rewording along with unrelated work). This ticket's own
Done report previously carried a contaminated Changed diffstat
(17 files spanning strata/scope-config/self-audit work far outside this
ticket's docs/modules/gates.md + docs/modules/graph.md scope) -- that
was a splice artifact from a different ticket's evidence-capture run,
not this ticket's real change. This report replaces it with only this
ticket's own scope.

Evidence: docs-only ticket with no pytest surface of its own (playbook
section 5) -- recording the existing CLI-dispatch integration test per
the T-0167 precedent.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 464 warning(s), 745 waived
- error-findings: SELFAUDIT001@design
