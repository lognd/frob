## Done report

Checked for a second consumer of tests/test_ticket_land.py's
_make_design_worktree helper across the whole test tree
(grep "_make_design_worktree" tests/ --include="*.py"): the only matches
are its own definition and TestLandPlan's five call sites, all in
tests/test_ticket_land.py itself. No second module needs this fixture.

Disposition: won't-fix at this ticket's scope -- the existing per-file
WIRE001 waiver on _make_design_worktree stays in place; there is nothing
to promote to a shared conftest helper today. Revisit if/when a second
test module genuinely needs an identical design-phase worktree fixture
(the condition the ticket's own follow-up names). No code change made.

### Changed
```
 tickets.md | 104 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 97 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 365 warning(s), 790 waived
- error-findings: none (measured, zero errors)
