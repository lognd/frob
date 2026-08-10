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
---
Full unscoped frob check on main (commit caf23ffc0a7c, measured while closing T-1933/T-1935) found: [gate:DOC] src/frob/tickets/_land.py:2179 DOC002 -- frob:doc anchor 'docs/modules/tickets.md#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922' does not resolve to any real anchor in docs/modules/tickets.md; closest suggested match is #mega-glob-scope-refused-at-start-t-1866. Looks like T-1922's land added the frob:doc directive with a slug that never got a matching heading/anchor added to docs/modules/tickets.md, or the doc's heading text drifted after the directive was written. Not attributable to T-1933/T-1935 (neither touched src/frob/tickets/_land.py). Fix: either add the missing anchor to docs/modules/tickets.md, or correct the frob:doc directive's slug to point at the real section documenting T-1922's OutOfScopeWaiveDeletion fix.