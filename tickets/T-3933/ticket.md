---
id: T-3933
title: 'F-171: vitest execution under frob''s evidence-cmd channel fails with import.meta.url
  not a file: URL'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_ts.py
- src/frob/testing/_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: F-296 H3-1 states the clearest version yet of the doubles-diverge-from-reality
    problem (act() eliminates the async window entirely, not just mocking); appending
    as motivating evidence rather than filing separately
  actor: logan
  at: '2026-09-06'
  old_length: 1329
  new_length: 3191
- mode: set
  reason: 'F-298 sharpens this ticket beyond the synthetic-lambda case: the test is
    entirely real and the HARNESS eliminates the interleaving it asserts on, so nothing
    in the test''s text looks wrong. Reproducing the race required dropping to legacy
    ReactDOM.render to escape act()''s synchronous flushing'
  actor: logan
  at: '2026-09-06'
  old_length: 3191
  new_length: 5708
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer report F-171: "import.meta.url is not a file: URL under the vitest setup frob's evidence-cmd channel uses." This is about EXECUTION (spawning vitest to actually run tests, via a [[test.runner]] command= template or cmd: evidence's shell invocation), not about node-id BINDING -- T-3925 fixed binding (F-134) using a SYNTHETIC LANGUAGE_COLLECTORS['ts'] stand-in in TestTicketEvidenceVitestOracle, which never spawns a real vitest process, so the execution path this report concerns is UNPROVEN by that work. Flagged while addressing F-167/F-134 follow-up so the T-3925/T-3847 support matrix's "verify" column for ts is understood correctly: BINDING is proven end-to-end, real vitest EXECUTION is not.

Investigate: how frob invokes vitest at run time (run_selected's RunnerSpec.command template for a [[test.runner]] language="ts" entry, or the cmd: evidence channel's shell invocation) -- likely a cwd/module-resolution mismatch causes the consumer's own vitest.config's import.meta.url usage to resolve to a non-file:// value (e.g. spawned with a relative cwd, or under an environment/loader frob's spawn helper (run_argv/apply_agent_env) alters in a way plain "npx vitest run" from a shell would not). Needs a real vitest project repro, not a synthetic collector stand-in, to pin down the actual spawn shape at fault.


F-296 H3-1's testing observation, appended here as the clearest statement yet of this ticket's own doubles/adapter-divergence shape. The consumer's own words: gate:TEST bound UT-1716's case as evidence that a pointermove dispatched after a grid resize paints correctly, but the bound test drives React through act(), "which flushes passive effects SYNCHRONOUSLY, so the render/effect window the real scheduler opens simply does not exist under test." No gate models "a React ref written during render is read by a rAF callback before the matching passive effect runs" -- and the test harness cannot even in principle observe this, because act()'s synchronous flush eliminates the exact window the real bug lives in.

WHY THIS SHARPENS THIS TICKET'S OWN FRAMING: T-3933's original shape (and T-4025 item 11) is a test whose MOCKED collaborators prevent it from exercising real behavior. This is the same family taken one step further -- the test's own HARNESS SEMANTICS (act()'s synchronous effect-flush) structurally eliminate an entire class of async-ordering bugs from ever being observable, with no mocking involved at all. A test here can be genuinely bound, genuinely passing, cite a real symbol, and be STRUCTURALLY INCAPABLE of ever catching the defect it is evidence for -- not because anything was mocked, but because the test's own execution model (act()) collapses a window that only exists under the real scheduler. When this ticket's TESTMOCK001-family design (T-3997) is generalized, consider whether "structurally eliminates an async window" (act(), fake timers collapsing real scheduling order, similar harness-level determinism shortcuts) deserves its own detection alongside "every collaborator was mocked" -- both defeat a test's evidentiary value, but by different mechanisms, and a rule looking only for mocks will miss this one entirely.

## F-298: THE HARNESS MADE THE RACE IMPOSSIBLE, AND THE GATE COULD NOT TELL

logand.app-v2, 2026-09-06, confirming and sharpening the F-296/H3-1 note appended
above:

  "To reproduce a rAF tick between commit and passive effect the agent had to use
   LEGACY ReactDOM.render OUTSIDE act(), because act() and createRoot().render()
   FLUSH PASSIVE EFFECTS SYNCHRONOUSLY in vitest. A GATE THAT BINDS A UT CASE AS
   EVIDENCE FOR A RACE CONDITION CANNOT TELL THAT THE HARNESS MAKES THE RACE
   IMPOSSIBLE."

THIS IS THE STRONGEST FORM OF THIS TICKET'S PROBLEM YET, and it is worse than the
synthetic-lambda case this ticket was filed for. There, a stand-in replaced a real
collector and could in principle be spotted by reading the test. Here THE TEST IS
REAL -- real component, real assertions, real framework -- and the HARNESS
SEMANTICS eliminate the interleaving the assertion is supposed to observe. Nothing
in the test's text looks wrong. The evidence is genuinely bound, genuinely
passing, and structurally incapable of failing for the reason it is cited.

NOTE WHAT IT TOOK TO GET A REAL REPRO: dropping to a LEGACY API (ReactDOM.render)
specifically to escape the modern harness's synchronous flushing. So the honest
test is the one that looks less idiomatic -- which is exactly the test a reviewer
would question.

THE GENERALISABLE CLAIM, worth stating in whatever this ticket produces: A TEST
CAN BE EVIDENCE FOR A PROPERTY ONLY IF THE HARNESS PRESERVES THE CONDITIONS THE
PROPERTY IS ABOUT. Timing, ordering, concurrency and scheduling properties are the
vulnerable class, because test harnesses routinely make execution deterministic ON
PURPOSE -- that determinism is a feature for most tests and a falsifier for these.

THEIR OWN CONCLUSION IS THE PRACTICAL ONE AND I AGREE WITH IT: the durable
evidence for a frame-loop property is an INVARIANT on the loop with a
throwing-subscriber test, not an act()-driven component test. That is filed as
T-4090. So the remedy here is not "detect bad harnesses" -- which is likely
undecidable -- but "for this class of property, bind evidence at a level the
harness cannot flatten".

WORTH ASKING, though it may have no cheap answer: can a gate know that a bound
test exercises a TIMING property at all? If frob:tests could carry a kind for
ordering/concurrency claims (the branch-level binding idea on T-3954 is adjacent),
a rule could at least require that such evidence not be a component-render test.
State whether that is tractable rather than assuming it is.
