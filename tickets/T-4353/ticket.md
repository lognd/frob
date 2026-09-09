---
id: T-4353
title: Windows abort recurs intermittently despite the heavy-group fix
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
- tickets/T-4360/**
- tickets/T-4362/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: T-4353's fix needs unit test coverage for the new xdist scheduler hardening;
    the companion test file is the natural home for it
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tickets/T-4360/**
  reason: 'SCOPE001 false-positive: blame attributes tickets/T-4360/ticket.md to its
    pre-promotion draft-filing commit, whose subject names only the draft id (no T-####
    digits for the cross-ticket exemption regex to match) -- explicitly scoping the
    file here until that gate gap is fixed separately'
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tickets/T-4362/**
  reason: same promoted-draft SCOPE001 blame gap as T-4360 (now tracked as T-4362
    itself) -- explicitly scoping until that gate gap is fixed separately
  actor: logan
  at: '2026-09-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE WINDOWS ABORT RECURRED AFTER ITS FIX. ONE COMPLETED RUN WAS NOT A FIX, AND THE
FAILURE IS INTERMITTENT RATHER THAN GONE.

MEASURED ACROSS TWO CONSECUTIVE RUNS OF NEARLY THE SAME TREE. The first completed
and emitted a real total failing set of five. The next aborted:

  SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR)
    collected=13823 (partial) failed=3 (partial, lower-bound)
    cause=KeyError: <WorkerController gw5>

That is the SAME worker-controller error the earlier fix was built to eliminate,
and the partial failing set names the very self-model tests that fix added to the
heavy serialisation group. So the grouping change helped -- it produced the first
completion this project has had -- but it did not close the hole.

WHAT THE EARLIER FIX ESTABLISHED, AND WHICH STILL HOLDS. The mechanism was two
full-repo graph scans running concurrently on separate parallel workers,
exhausting memory, killing each other, and corrupting the scheduler's bookkeeping
into this exact error. The fix derived heavy-group membership from each test's
FIXTURE CLOSURE rather than a hand-maintained name list, so any test using the
shared self-scan fixture is serialised automatically. Do not undo that; it is the
right shape and it demonstrably changed the outcome.

SO THE QUESTION IS WHAT ELSE CAN STILL COINCIDE. Candidates worth separating
rather than guessing between: another heavyweight test that does NOT use that
fixture but is comparably memory-hungry, so it never joined the group; the group
serialising against itself but still overlapping something else scheduled
concurrently; or a genuine memory ceiling where even one scan plus normal parallel
load is too much on this runner. Establish which by MEASURING memory during the
run rather than by reasoning -- the earlier fix was found by reading the scheduler
error and the worker logs together, and the same evidence is available here.

TREAT THE INTERMITTENCY AS THE PRIMARY DIFFICULTY. A failure that happens on some
runs and not others cannot be confirmed fixed by one green run -- that mistake has
already been made once on this exact defect. Whatever you change, state how many
consecutive completions you consider proof, and prefer a mechanism whose
correctness is arguable from the code rather than one that merely has not failed
yet.

CONSIDER WHETHER THE SCHEDULER ERROR SHOULD BE SURVIVABLE. Independently of the
memory cause: a worker dying currently takes the whole session down and destroys
the failing set for every other test. Even with the memory problem solved, a
single killed worker turning a partial result into no result at all is a fragile
arrangement. Say whether that is worth addressing separately, and file it rather
than building it here if so.

VERIFY ON WINDOWS. The `winrun` script syncs this repo to a Windows mirror and
runs natively -- measure rather than reason. Caveats: single shared mirror
checkout (concurrent syncs clobber), venv uses `Scripts/` not `bin/`, bare
`python3` hits a Store alias stub exiting 9009.
