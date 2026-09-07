---
id: T-4168
title: BUG002 misses the file-absent-at-parent shape, so every test-first repro records
  no verdict instead of a named outcome
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a repro test that is new in the ticket and absent at the parent commit,
    when the repro check runs, then it produces a named outcome rather than the generic
    collection-error branch
  evidence: []
- text: given a repro test that genuinely passes at the parent, when the repro check
    runs, then it reports passed-at-parent and BUG002 still fails
  evidence: []
- text: given a ticket whose repro test never demonstrated a red state, when the gate
    runs, then the ticket does not satisfy BUG002
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE REPRO CHECK'S "TEST ABSENT AT PARENT" DETECTION MISSES THE CASE WHERE THE
TEST FILE ITSELF IS ABSENT. Reported as logand.app-v2 F-364: a designated repro
test yielded "exited 4 at parent ... no verdict" at both close and land, because
the test was added in that very ticket and so did not exist at the parent commit.

THE CODE ALREADY HAS THE RIGHT OUTCOME AND DOES NOT REACH IT.
src/frob/gates/_bug_repro.py has a `TEST_ABSENT_AT_PARENT` outcome, and its
docstring shows the author understood this situation -- it even notes the case is
"systematically true for EVERY already-landed ticket's own post-land history",
because landing squashes the repro test and its fix into one commit. But the
detection is:

    zero_collected = bool(re.search(r"\bcollected=0\b", combined_output))
    if zero_collected or "no tests ran" in combined_output:
        ... return _BugReproOutcome.TEST_ABSENT_AT_PARENT

Those two markers are what pytest emits when the FILE EXISTS but no node id
matches. When the whole file is missing, pytest exits 4 with a
file-or-directory-not-found error and emits NEITHER marker, so the run falls
through to the generic branch -- "not a plain pass/fail ... likely a collection
error, e.g. a native extension the parent commit's isolated checkout never built"
-- and records no verdict.

So the outcome exists, the intent exists, and one input shape was not covered.
That is a narrow fix with a wide effect: a test-first workflow means the repro
test is NEW IN THE TICKET, which makes file-absent-at-parent the NORMAL case
rather than an edge one. Every test-first bug ticket hits it.

DO NOT SIMPLY MAP "ABSENT" ONTO "RED", which is what the report asks for. Their
instinct is right that the current outcome is useless, but absent is not evidence
of red. A test that does not exist did not fail; it was not run. Treating absence
as a passing repro check would let a ticket satisfy BUG002 by adding a test that
never demonstrated anything -- which is exactly the confirmatory-only evidence
this gate exists to reject.

THE HONEST FIX IS TO RUN THE NEW TEST AGAINST THE OLD CODE. The question BUG002
asks is "did this bug exist before the fix", and answering it requires the
ticket's test file placed into the parent checkout and run there. The machinery
to check out the parent already exists in this module. Adding the test file to
that checkout is the missing step, and it turns a structural no-verdict into a
real measurement. If that is impractical for some cases (a test whose fixtures
also arrived with the ticket), then say so and report absent under its OWN name
with an explicit statement that the repro was not demonstrated -- never as a pass.

WHAT TO DO
  1. Detect the file-missing shape, not only the node-id-missing shape. Match on
     pytest's file-not-found behaviour as well as its zero-collected markers, and
     prefer checking whether the path exists in the parent tree over parsing
     output at all -- the tree is right there and a filesystem check cannot be
     fooled by output-format drift.
  2. Then decide what to DO with a confirmed absence: attempt the new test against
     the old code, or report a named, honest non-verdict. State the choice.
  3. Whatever is chosen must not let a ticket pass BUG002 without a demonstrated
     red state. That is the gate's whole purpose.

MUST-FIRE FIXTURE:   a repro test that is new in the ticket, absent at the
                     parent, produces a named outcome -- not the generic
                     collection-error branch.
MUST-STAY-QUIET:     a repro test that genuinely passes at the parent still
                     reports passed-at-parent and still fails BUG002.
THIRD FIXTURE:       whatever is chosen for the absent case, a ticket whose test
                     never demonstrated a red state does not satisfy BUG002.

ACCEPTANCE
- File-absence detected by checking the parent tree, not by parsing output.
- The absent case given a named outcome and a stated policy.
- No path added by which an undemonstrated repro satisfies the gate.
- All three fixtures committed.
