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
body_changes:
- mode: set
  reason: 'adds a second shape that cannot demonstrate a red state and needs a different
    answer: a repro that can only run against a live deployment, whose module hard-skips
    by design. Distinguishes it from this ticket''s file-absent case, where placing
    the test into the parent checkout is a viable fix, and warns that any accept-declared-unrunnable
    path must key on a machine-visible declaration rather than a prose reason'
  actor: logan
  at: '2026-09-07'
  old_length: 4084
  new_length: 7132
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

A SECOND SHAPE THAT CANNOT DEMONSTRATE A RED STATE, AND IT NEEDS A DIFFERENT
ANSWER FROM THIS TICKET'S. logand.app-v2 F-387 (on frob 0.530.0): a close was
refused for confirmatory-only evidence, and the analysis is correct on both
halves.

  - The bound test DID pass at the parent, honestly: it asserts a header equals
    an exact string, and both the string and the code changed in the same commit.
    Confirmatory by construction, not a repro. The refusal is RIGHT.
  - The genuine repro exists and is a different test: it parses a live response
    and would fail pre-fix, pass post-fix. But it can ONLY execute against a real
    deployed endpoint. Its module hard-skips otherwise BY DESIGN, and its own
    docstring says it never runs by default in CI or a local invocation. There is
    no local double for it, unlike the compose-stack fixtures their other
    end-to-end tests use.

SO THE TICKET HAS A REAL REPRO THAT THE GATE STRUCTURALLY CANNOT OBSERVE. That is
not the same as this ticket's file-absent-at-parent case, where the test exists
and could be run against the old code if the machinery placed it there. Here,
running it at the parent is impossible without a deployment, and no amount of
checkout machinery changes that.

THE HONEST OPTIONS, AND NEITHER IS "WEAKEN THE GATE":
  a. ACCEPT A DECLARED-UNRUNNABLE REPRO, under a named, checkable condition. A
     test whose module declares it requires an external environment is a
     different category from a test that merely failed to run. If the gate can
     see that declaration -- the skip is by design and documented -- it could
     record the repro as DECLARED BUT UNVERIFIABLE rather than refusing or
     silently passing. That is the unmeasured-not-clean posture this queue has
     demanded everywhere else, applied here.
  b. REQUIRE A LOCAL DOUBLE for the assertion, so a repro exists that CAN run at
     the parent. Their other end-to-end tests already have compose-stack
     fixtures; this module does not. That is arguably the better engineering
     answer and it is also more work, and it is THEIR work rather than frob's.

Prefer (a) as frob's part, because frob cannot require every consumer to build a
local double for every deployment-only assertion, and refusing the close is
currently forcing exactly that or forcing a false binding. But (a) must NOT
degrade into a general escape: the declaration has to be machine-visible and
specific, not prose in a reason string. This repo has already recorded that an
intention stated in prose is not enforcement, four times in one session.

WHAT THIS ADDS TO THIS TICKET'S SCOPE: when enumerating why a repro cannot
demonstrate a red state, the file-absent case is one reason and
declared-environment-dependence is another. Both currently collapse into an
outcome that is either a refusal or a no-verdict. Distinguish them by name, and
decide each separately -- I have deliberately not merged them, because the fix
for one (place the test into the parent checkout and run it) is unavailable for
the other.
