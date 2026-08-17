---
id: T-2025
title: 'Post-land --check-repro cannot verify a squashed ticket''s repro test: no
  ref in main history has test-without-fix'
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
- src/frob/gates/_mutation_evidence.py
- src/frob/tickets/_land_git_ops.py
- docs/modules/tickets.md
- src/frob/app/ticket_runner/_verify.py
- tests/test_gates_mutation_evidence.py
- tests/unit/test_ticket_runner_designate_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: the message function for the new outcome lives in _verify.py; both existing
    test files cover the new outcome's classification and message
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates_mutation_evidence.py
  reason: the message function for the new outcome lives in _verify.py; both existing
    test files cover the new outcome's classification and message
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: the message function for the new outcome lives in _verify.py; both existing
    test files cover the new outcome's classification and message
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_test_absent_at_parent_is_distinct_from_no_verdict
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_test_absent_at_parent_exit1_with_explanatory_message
designated_repro_test: tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_test_absent_at_parent_is_distinct_from_no_verdict
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2019 (re-verifying 10 BUG002 repro designations
against T-2005's PYTHONPATH fix).

`frob ticket land` squashes every worktree ticket's commits into ONE
commit on main (confirmed: T-1546's own worktree commits, e.g.
086172ad8, are NOT ancestors of main -- only the single "land T-1546"
squash commit 4b6695745 is). This means main's own history never
contains a commit where a ticket's designated repro test exists
WITHOUT that same ticket's fix already applied: the test method and
the fix land together, atomically, in the same commit.

Consequence: `frob ticket evidence <id> --check-repro [NODE-ID]
--base-ref <ref>` run AFTER landing, against ANY ref in main's history
(including the land commit's own immediate parent, main's tip right
before the squash), cannot ever produce a real verdict for a NEWLY
ADDED repro test -- pytest exits 5 ("no tests collected") because the
specific test method does not exist yet at that ref, and the tool
correctly reports this as NO_VERDICT, not a pass or fail.

Measured directly: 9 of the 10 tickets T-2019 asked to re-verify
(T-1546, T-1749, T-1838, T-1841, T-1848, T-1853, T-1861, T-1882,
T-1907; T-1670 excluded as N/A, see T-2019's Done report) all returned
NO_VERDICT this way. Confirmed by direct inspection for T-1546 and
T-1907 that the designated test method is absent from the git blob at
the chosen parent ref, while the surrounding test class is present --
exactly the squash-history shape, not a per-ticket anomaly.

This means `--check-repro`/`--designate-repro`'s parent-commit
classification is ONLY ever meaningfully checkable from INSIDE a
ticket's own worktree, BEFORE it lands (where the test-added-then-fix-
added commit sequence still exists un-squashed) -- once a ticket lands
and its worktree is removed, there is structurally no way to
independently re-verify its BUG002 classification against main alone.
T-2019 needed to fall back to reading whether the tool's OWN validation
ran correctly at designate/land time (audit trail, --designate-repro's
synchronous validation per T-1929) rather than being able to
reproduce the check itself post-land.

Proposed scope: either (a) `frob ticket land` records the pre-squash
parent SHA (the worktree branch point, or the specific commit
immediately after the repro test was added but before the fix) into
the ticket's ledger at land time, so a later `--check-repro --base-ref
<recorded-sha>` has a real ref to check against, or (b) explicitly
document this as a permanent limitation of `--check-repro` post-land,
so a coordinator does not ask an agent to do what T-2019 asked (which
this repo's own review process is going to keep re-discovering
otherwise).

## Done report

DECISION (per the coordinator's two constraints): documented limitation
plus a precision fix, NOT recording a pre-squash commit. Both options
weighed explicitly:

Option (a), rejected -- record the pre-squash test-only commit at land
time (e.g. under a retained refs/frob-repro/<id> namespace) so
--check-repro has a real post-land ref:
  - Only helps if the implementer split test-then-fix into two commits;
    the common case is one commit with both, so this would need a NEW,
    universally-enforced commit-discipline rule across every dispatched
    agent plus a gate to catch tickets that skipped it -- ceremony added
    to EVERY land for a capability rarely exercised.
  - The recorded ref needs active retention (a real branch/tag) or it is
    garbage-collected the moment the worktree is removed -- permanent
    extra ref-namespace bookkeeping and repo growth, forever, per
    bug/security-kind ticket.
  - Does not restore "one clean atomic commit per ticket" -- only threads
    a side-channel around the squash guarantee, exactly the kind of
    fragile mechanism that looks like it gives a verdict while depending
    on an invisible discipline.

Option (b), shipped -- refuse loudly and explain why, distinctly from a
genuinely transient/retryable NO_VERDICT:
  - `TEST_ABSENT_AT_PARENT`, a new `_BugReproOutcome` member
    (src/frob/gates/_mutation_evidence.py), fired when pytest reports
    zero collected items for the designated node id at `base_ref`.
  - Message (src/frob/app/ticket_runner/_verify.py's
    `_bug_repro_outcome_message`) explicitly names the squash-history
    cause for an already-landed ticket, points to the documented
    limitation, and names the still-working technique (commit the repro
    test alone first, confirm it fails, then commit the fix, pass the
    test-only commit as --base-ref -- T-2021's own evidence used exactly
    this).
  - No caller needed to change: every existing consumer already checks
    `is FAILED_AT_PARENT` / `is not PASSED_AT_PARENT` (never an
    exhaustive switch over every member), so the new outcome falls
    through to "not a pass" automatically -- a messaging refinement,
    zero new gating behavior, zero blast radius.
  - `docs/modules/tickets.md#--check-repro-cannot-verify-a-squashed-
    tickets-repro-test-after-it-lands-t-2025` documents the limitation,
    the measured evidence (T-2019's 9-ticket re-verification), both
    rejected/shipped options with their cost, and the still-working
    technique.

MEASUREMENT CORRECTION mid-ticket: the exit code the "test absent" case
produces is NOT stable -- confirmed directly: pytest 9.0.3 returns exit 4
("not found: NODEID, no match in any of [...]") in a minimal synthetic
repo with no conftest, but this repo's OWN real historical commits
(T-1546, T-1907) measured exit 5 for the identical shape once this
repo's own tests/conftest.py/plugin set are involved (confirmed via a
direct isolated-worktree pytest invocation matching frob's own spawn
shape exactly: cwd=the checked-out worktree, not the caller's root --an
earlier attempt using the wrong cwd produced a misleading exit 0/pass
that does not represent what BUG002 actually does). Branching on either
exit code alone would silently misclassify the other environment's
shape as a bare NO_VERDICT (no explanation) instead of
TEST_ABSENT_AT_PARENT. Classification instead checks the process output
for "collected=0" (this repo's own SUITE-RESULT summary line, T-1596,
predates BUG002 and is present at every real historical ref this
function is ever called against) with pytest's builtin "no tests ran"
text as a fallback for a checkout that somehow lacks the hook -- both
confirmed present in the same measured real-repo run.

Evidence: 2 new tests, one genuine FAILED_AT_PARENT BUG002 repro (built
via the T-2021 split-commit technique: test-only commit dfef29f8a
committed first, confirmed to fail against the still-unfixed
_mutation_evidence.py/_verify.py, then the fix committed separately as
b4cfae653).
  - tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_test_absent_at_parent_is_distinct_from_no_verdict
    (designated repro, FAILED_AT_PARENT at dfef29f8a) -- a real git repo
    fixture reproducing the exact squash shape (class exists at parent,
    method does not) and asserting the outcome is TEST_ABSENT_AT_PARENT,
    never NO_VERDICT.
  - tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_test_absent_at_parent_exit1_with_explanatory_message
    -- the CLI message contains "TEST_ABSENT_AT_PARENT" and "squash",
    not the old generic wording.

Re-verified against REAL historical data, not just the synthetic
fixture: `frob ticket evidence T-1546 --check-repro --base-ref
57caecf76... --archived` (the same call T-2019 made) now classifies as
TEST_ABSENT_AT_PARENT with the new explanatory message, where it
previously fell through to the generic NO_VERDICT wording -- confirmed
by direct invocation before and after the fix.

Ran: `uv run pytest tests/test_gates_mutation_evidence.py
tests/unit/test_ticket_runner_designate_repro.py -q` -- 47 passed, 0
failed, both before-commit (test-only, 2 of 47 genuinely fail) and
after-commit (fix restored, 47 of 47 pass) states measured directly.

`uv run frob check --ticket T-2025 --only test`: 0 errors, 25 warnings
(pre-existing, unrelated), 7 waived (pre-existing) -- one real DRIFT002
finding surfaced and fixed mid-ticket (a `frob:describes` anchor
pointing at an enum MEMBER rather than the enclosing class, which the
graph indexer cannot resolve; retargeted to `_BugReproOutcome`).

`uv run frob check --land-parity`: clean -- 0 unscoped error(s).

Scope note: added src/frob/app/ticket_runner/_verify.py (the shared
message function lives there) and the two test files to the ticket's
declared scope via `frob ticket scope --add`, with reason. Did not
touch src/frob/tickets/_land_git_ops.py (no code there needed changing
for the chosen fix) or _rapid_sweep.py/_query.py (explicitly the
coordinator's exclusion, another agent's ownership).

### Changed
```
 docs/modules/tickets.md                          | 103 +++++++++++++++++++++++
 src/frob/app/ticket_runner/_verify.py            |  28 +++++-
 src/frob/gates/_mutation_evidence.py             |  86 +++++++++++++++++--
 tests/test_gates_mutation_evidence.py            |  42 +++++++++
 tests/unit/test_ticket_runner_designate_repro.py |  36 ++++++++
 tickets/T-2025/ticket.md                         |  29 ++++++-
 6 files changed, 311 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestBugReproAtRef::test_test_absent_at_parent_is_distinct_from_no_verdict` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_reports_test_absent_at_parent_exit1_with_explanatory_message` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/unit/test_tickets_evidence_only_scope.py
