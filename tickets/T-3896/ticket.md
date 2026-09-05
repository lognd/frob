---
id: T-3896
title: 'post-merge re-verification missed tests the merge itself broke through a shared
  contract: a semantic merge conflict lands green'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Reported in logand.app-v2 FROBLEMS as an addendum, 2026-09-05. A land's
post-merge claims re-verification did not catch tests that its own merge broke.

WHAT HAPPENED, in their words:

    Pre-existing red on main (from T-0011):
      backend/tests/unit/test_db_base.py::test_create_engine_missing_url
      ::test_session_factory_missing_url
      test_migrations_env.py::test_resolve_database_url_missing
      ::test_env_metadata_complete
    -- landed GREEN in the worktree, RED on main after merge (AppConfig gained
    `database_url` from the app-shell land). The land's post-merge claims
    re-verification did not catch it.

THE DEFECT CLASS: A SEMANTIC MERGE CONFLICT. Two lands are each green in
isolation. Neither touches the other's files, so no textual conflict occurs and
no cross-ticket guard fires. Together they are red, because one changed a shared
contract -- here, AppConfig gaining a field -- that the other's tests assert
against. Git cannot see it; only running the merged tree can.

WHY THIS IS SERIOUS RATHER THAN ROUTINE: frob HAS the mechanism that should
catch it. Post-merge claims re-verification exists precisely to run a ticket's
evidence against the MERGED tree rather than the branch. It ran and did not
catch this. So either it did not run these particular tests, or it ran a subset
that excluded them, or it reported unmeasured and that was read as passing.

NOTE THE OVERLAP, AND SEPARATE IT CAREFULLY FROM T-3886. T-3886 covers the
verify worker reporting "unmeasurable" when its own child was killed. If the
re-verification here reported unmeasured for that reason, this is the SAME bug
and should be closed as a duplicate with the evidence added there. If the
re-verification RAN, measured cleanly, and still missed these four tests, it is
a DIFFERENT and arguably worse defect -- a scope problem, not a reliability one.
DETERMINE WHICH FIRST. Do not start designing a fix until that is settled;
the two need opposite work.

IF IT IS A SCOPE PROBLEM, the likely shape is that re-verification runs the
ticket's OWN bound evidence rather than the tests affected by the merged
result. That is a defensible design -- a ticket is accountable for its own
claims -- but it means a land can turn main red through a shared contract and
every gate stays green, which is exactly what happened. The question to answer
explicitly: after a merge, should verification run the ticket's evidence, or the
touched-set of the MERGED diff? The second is more expensive and catches this;
the first is cheap and cannot. State the trade and pick.

MEASURE BEFORE DESIGNING: does this repo have the same hole? Take two landed
commits where the second changed a shared model or config surface, and check
whether the first's evidence would have been re-run against the merged tree. If
frob's own history contains an instance, it is worth naming -- this repo lands
many tickets against shared models (AppConfig, the Ticket model, Violation).

DO NOT fix this by re-running the whole suite on every land. That is the
obvious answer and it is wrong here: the suite takes roughly 14 minutes under
xdist and lands are already the fleet's bottleneck. A touched-set of the merged
diff is the interesting middle, and frob already has touched-set machinery
(`frob test --base main`) to build on.

MUST-FIRE FIXTURE:   a land whose merge breaks a test OUTSIDE its own scope,
                     via a shared contract, is caught before the land reports
                     success
MUST-STAY-QUIET:     an ordinary land that breaks nothing is not slowed
                     materially, and does not start running unrelated tests

ACCEPTANCE
- The is-it-T-3886-or-a-scope-problem question answered first, with evidence.
- If scope: the evidence-vs-merged-touched-set trade stated and decided.
- A check of whether frob's own history contains an instance, reported either
  way.
- Both fixtures committed.
