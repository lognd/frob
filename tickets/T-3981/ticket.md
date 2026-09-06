---
id: T-3981
title: 'F-195: unresolved evidence id asserts the test does not exist instead of suggesting
  the nearest collected id'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
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
Consumer logand.app-v2 F-195, 2026-09-06:

  "T-0180's agent bound wasm-engine/src/color.rs::gradient_stops_equal_apollo_tokens
   and got 'does not resolve'; the collected id is
   wasm-engine/src/color.rs::tests::gradient_stops_equal_apollo_tokens.
   The resolver should suggest the nearest collected id."

THE ERROR IS NOT MERELY UNHELPFUL -- IT IS CONFIDENTLY WRONG, and that is what
raises this above a nicety. The message on this path (see
_reject_unresolved_evidence in src/frob/tickets/_evidence.py, the empty
missing_natives branch) tells the user:

  "every declared native is built and collection ran against the full tree, so
   this test does not exist in this tree (not a stale cache; fix the id)"

The test DOES exist. It is one module segment away. The message asserts a strong,
specific, false conclusion, and it explicitly forecloses the two cheapest
hypotheses a user would otherwise try. Note that wording was itself a deliberate
improvement (T-2090 chose it after "two wasted cycles" following the older
cache-deletion advice) -- so this is a case where a message got more confident
without getting more correct. A confident wrong diagnosis costs more than a vague
one.

THE FIX: when an id fails to resolve, compute the nearest collected id and name
it. The candidate set is already in hand at the point of failure -- the resolver
has `collected` right there -- so this is a suggestion over a set already
computed, not new work. For the rust case the miss is highly structured (a
missing `::tests::` module segment), but do NOT special-case rust: a generic
nearest-match over the collected set covers this, the python class/method
analogue, and the kotlin dot-form case already filed as T-3945.

WHILE YOU ARE THERE: soften the false certainty. The message should say the id
did not resolve and name the closest matches, rather than asserting the test does
not exist. Only claim non-existence when there is NO near match.

WATCH THE OBVIOUS FAILURE MODE: a nearest-match that fires on everything is
noise, and a suggestion that is confidently wrong repeats the current bug in a
new costume. Pick a distance threshold and prove it -- an id sharing the file path
and differing by one module segment is a strong match; an unrelated id in another
file is not. If no candidate clears the bar, say there is no near match rather
than offering the least-bad one.

RELATED, DO NOT DUPLICATE: T-3945 (normalize_evidence_separator mangles dotted
kotlin ids) is a different defect -- there the id is corrupted before matching.
This ticket is about what to SAY when matching legitimately fails. Both touch
evidence resolution; keep them distinct.

MUST-FIRE FIXTURE: binding a rust id missing its ::tests:: segment names the
correct collected id in the error.
MUST-STAY-QUIET: a genuinely nonexistent id with no near match is still rejected,
and does NOT get a misleading suggestion.
THIRD FIXTURE: the same near-match behaviour for a non-rust language, proving the
fix is not rust-special-cased.

ACCEPTANCE
- Nearest collected id suggested, over the already-computed collected set.
- The "this test does not exist in this tree" claim made conditional on there
  being no near match.
- All three fixtures committed.