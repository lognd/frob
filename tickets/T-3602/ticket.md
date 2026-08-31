---
id: T-3602
title: Confirm and stamp the 0.530.0 (publishable) milestone ticket set
state: queued
kind: docs
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3190: the milestone lifecycle machinery (MILE001/MILE003)
is now proven against fixture data (tests/test_gates_milestone.py, 29
cases) and the two-milestone semantics are documented
(docs/modules/tickets-lifecycle.md#adopting-real-milestones-t-3190):
0.530.0 = publishable (green 3-platform CI + working PyPI install),
1.0.0 = [tickets].default_milestone, everything else.

T-3190's own guardrail explicitly forbids a bulk 'milestone: 0.530.0'
backfill and requires the owner to see the proposed split before it is
treated as settled -- this ticket exists to carry that decision.

PROPOSED CANDIDATE SET (derived 2026-08-31 by scanning open/queued/
in-progress/blocked/planned tickets for titles matching CI/publish/
release-critical-path keywords, filtered by T-3190's stated rule --
directly blocks a green ubuntu/windows/macos CI job, or a working
'pip install frob'):

  T-2939  macOS: git subprocess returncode=128 in test fixtures --
          100+ system/CLI test failures, root cause unconfirmed
  T-3076  Characterize the 278 Windows-only test failures
  T-3212  macOS CI: triage SYS107/SYS003 selfconform finding and
          resolved-root/load_lock path clusters (T-2942 remainder)
  T-3213  (near-duplicate title of T-3212 -- verify whether this is a
          genuine dup before stamping either)
  T-3337  frob release publish always bumps patch only, ignores REL001
          required bump class
  T-3505  Windows works: drain T-3076's failure set and remove the
          T-3425 advisory flag
  T-3512  Remove T-3425 windows-latest continue-on-error advisory flag

NOT included (CI-adjacent but not itself blocking): T-2894, T-2963,
T-2982, T-3010, T-3053, T-3073, T-3274, T-3340, T-3377 -- dev-experience,
architecture, or post-publish concerns under the stated rule.

The KNOWN blocking set named when T-3190's decision was recorded
(T-3246, T-3247, T-3249, T-3250, T-3251) is fully DONE as of 2026-08-31
and needs no stamp (MILE001 only evaluates OPEN tickets).

ACTION: owner reviews/edits the candidate list above, then each
confirmed ticket is stamped individually via 'frob ticket milestone
<id> --set 0.530.0' (never a hand-edit of tickets.md), followed by a
real-data MILE001/MILE003 check ('frob check --only tickets' or
equivalent) to confirm the gate now evaluates real cross-milestone
edges, not just tests/test_gates_milestone.py's fixtures.
