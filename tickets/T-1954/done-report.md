## Done report

frob:no-behavior-change reason="pure doc-anchor fix: adds the missing docs/modules/tickets.md heading/anchor T-1922's own frob:doc directive already pointed at (the directive text is unchanged) so DOC002 resolves. No production code path changed -- src/frob/tickets/_land.py's _restrict_to_branch_own_files logic is byte-identical -- so there is no runtime behavior for a designated repro test to exercise; the bound evidence (both of T-1922's own real regression tests) correctly PASSES at both parent and fix, which is exactly what a no-behavior-change claim predicts."

T-1922's land (b508b0ad3) added a `frob:doc` directive on
`_restrict_to_branch_own_files` pointing at
`docs/modules/tickets.md#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922`,
but never actually added a matching heading to that doc -- confirmed by
reading the commit's own diff (`git show b508b0ad3 -- docs/modules/
tickets.md`): the only new content that commit added was an unrelated
"Auto-rebase after a successful land (T-1720)" section (a joint T-1720+
T-1922 land) plus a passing mention of "T-1922" inside that section's
prose. No heading anywhere in the file ever matched the slug the
directive claimed.

Fix: added a new `## OutOfScopeWaiveDeletion false-refusal on a stale
worktree (T-1922)` section to docs/modules/tickets.md (slugs to exactly
`#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922`,
verified against DOC002's own slug computation below), documenting
`_restrict_to_branch_own_files`'s actual fix -- content drawn from the
function's own docstring (already accurate and complete) plus a citation
of its two real regression tests. Did not touch
`src/frob/tickets/_land.py`'s directive text itself (only its doc target
needed to exist).

Verification: `frob check --only docanchor` (unscoped): 0 errors (was 1
DOC002 before). `frob check --only docanchor --only drift` (unscoped): 0
errors, 0 warnings, 2 waived (pre-existing, unrelated DRIFT001 waivers on
_lifecycle.py/_rapid_sweep.py untouched by this ticket).

Filed: none.

### Changed
```
 tickets/T-1951/ticket.md | 5 ++++-
 tickets/T-1954/ticket.md | 5 ++++-
 2 files changed, 8 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 1010 warning(s), 705 waived
- error-findings: ARCH001@src/frob/gates/_dead_symbols.py, DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1954
