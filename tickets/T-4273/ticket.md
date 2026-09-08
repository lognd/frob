---
id: T-4273
title: 'the ledger auto-commit fails under parallel load with an empty stderr and
  its self-heal repeats the same failing command: the single linux CI failure'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- src/frob/app/ticket_runner/_close_cmd.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: tests for the T-4273 fix live in this file; it already carries hundreds
    of pre-existing frob:tests directives from _leases.py so adding it in scope also
    resolves the pre-existing SCOPE002 breadth debt against it
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a ledger commit that exits non-zero, when the failure is logged, then
    both output streams are captured and the message names the actual cause rather
    than an empty string
  evidence: []
- text: given the self-heal path, when its premise that content was written but the
    commit was lost does not hold, then it says so instead of re-running an identical
    command and declaring a human is needed
  evidence: []
- text: given the failing test and its already-marked sibling, when this is fixed,
    then neither is resolved by adding a rerun marker
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE LEDGER AUTO-COMMIT FAILS UNDER PARALLEL TEST LOAD, ITS SELF-HEAL FAILS TOO,
AND THE ONLY DIAGNOSTIC IS AN EMPTY STRING. This is the single failure on the
integration run's linux leg: one test out of 13,637, failing in fixture setup
rather than in anything it asserts.

WHAT THE RUN ACTUALLY SHOWED, quoted from its own log rather than summarised. The
close path's ledger commit reported `returncode=1 stderr=''`. Before that, the
self-heal announced that the commit "was killed after writing its content but
before `git commit` completed" and that it was re-attempting; the re-attempt then
reported that the repository "is still dirty" and that the situation "needs a
human". The test never reached its assertions -- it died inside the helper that
merely creates a done ticket for the case under test.

THE EMPTY STDERR IS THE MOST INFORMATIVE PART. A non-zero exit with nothing on
the error stream is the signature of the tool writing its explanation to the
OTHER stream. The most likely explanation, given a commit restricted to a single
path, is that nothing was staged for that path at the moment the commit ran, so
the message went to standard output and was discarded. If that is what is
happening, then the self-heal's premise -- that the content was written and only
the commit was lost -- does not match the actual state, which is why re-attempting
the identical commit fails identically. Confirm this by capturing BOTH streams
before theorising further; the current code cannot tell these cases apart and
neither can a reader of its logs.

DO NOT FIX THIS BY MARKING THE TEST FLAKY. The sibling test in the same class
already carries a rerun marker, added with the reason that a liveness check races
the archive attempt under load. Both tests call the SAME helper, and that helper
is where this failure happened. So the marker did not fix a test-level race; it
concealed an infrastructure-level one, and the unmarked twin has now surfaced the
same defect from the other side. Adding a second marker would complete the
concealment and leave the real problem to be rediscovered later, in a worse
place, by someone with less context. This is the wrong-incentive shape: the
cheapest action that clears the gate degrades the record.

WHY THIS MATTERS BEYOND ONE TEST. The failing code is the ledger auto-commit that
runs on ordinary ticket verbs, not test-only scaffolding. If it can lose a commit
under parallel load in a temporary fixture repository, it can do the same in a
real checkout under a busy fleet, and the visible symptom there is a ticket whose
state changed on disk but never reached a commit -- which this project already
knows as one of its most expensive failure shapes.

WHAT THE FIX MUST DELIVER.
  Capture and report both output streams when the commit fails, so the next
  occurrence names its own cause instead of presenting an empty string.
  Determine whether the failure is an empty staging area, a lost write, a
  concurrent index lock, or a killed process, and make those distinguishable in
  the log rather than collapsed into one message.
  Make the self-heal verify its own premise before re-attempting, and report
  honestly when the premise does not hold rather than repeating an identical
  command and declaring that a human is needed.

REPRODUCE IT BEFORE FIXING IT. It appeared under parallel workers on a loaded
runner. A fix that cannot be shown to change behaviour under comparable
concurrency is a guess. If it proves genuinely unreproducible locally, say so
plainly and make the diagnostic improvement anyway -- better logging is the part
that pays off on the next occurrence either way.
