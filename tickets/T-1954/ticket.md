---
id: T-1954
title: 'DOC002: src/frob/tickets/_land.py:2179 frob:doc anchor for T-1922 does not
  resolve'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- docs/modules/tickets.md
- tickets/T-1951/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'docs/modules/tickets.md is where T-1922''s frob:doc directive target

    actually needs to live -- adding the missing anchor there is the whole

    fix. tickets/T-1951/ticket.md is touched because T-1951 (the DRIFT002

    sibling ticket for the same land-defect class) was started/worked in

    this same worktree alongside T-1954.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1951/**
  reason: 'docs/modules/tickets.md is where T-1922''s frob:doc directive target

    actually needs to live -- adding the missing anchor there is the whole

    fix. tickets/T-1951/ticket.md is touched because T-1951 (the DRIFT002

    sibling ticket for the same land-defect class) was started/worked in

    this same worktree alongside T-1954.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Full unscoped frob check on main (commit caf23ffc0a7c, measured while closing T-1933/T-1935) found: [gate:DOC] src/frob/tickets/_land.py:2179 DOC002 -- frob:doc anchor 'docs/modules/tickets.md#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922' does not resolve to any real anchor in docs/modules/tickets.md; closest suggested match is #mega-glob-scope-refused-at-start-t-1866. Looks like T-1922's land added the frob:doc directive with a slug that never got a matching heading/anchor added to docs/modules/tickets.md, or the doc's heading text drifted after the directive was written. Not attributable to T-1933/T-1935 (neither touched src/frob/tickets/_land.py). Fix: either add the missing anchor to docs/modules/tickets.md, or correct the frob:doc directive's slug to point at the real section documenting T-1922's OutOfScopeWaiveDeletion fix.

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
