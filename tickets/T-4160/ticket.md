---
id: T-4160
title: OPAQUE001 decides a security-adjacent question with a text search, so an erased
  type-position import reads as a runtime dynamic lookup
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
- src/frob/vet/_capability_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a value-position dynamic import with a non-literal specifier, when the
    opaque gate runs, then OPAQUE001 still fires
  evidence: []
- text: given a type-position import expression, when the opaque gate runs, then nothing
    fires
  evidence: []
- text: given a file that cannot be parsed, when the opaque gate runs, then it reports
    the parse failure rather than falling back silently to a text match
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OPAQUE001 FIRES ON A TYPE-POSITION IMPORT, WHICH HAS NO RUNTIME BEHAVIOUR AT ALL.
Reported as logand.app-v2 F-361: a `typeof import("...")` used in TYPE position
was flagged as an evasion-indicative dynamic lookup. There is no runtime
indirection in that construct -- it is erased entirely before the code runs.

THE MECHANISM IS LEXICAL, AND I TRACED IT. The opaque gate delegates to
`_opaque_indirection_findings` (src/frob/vet/_capability_scan.py:1464), whose
detection path runs through `_needle_hits_outside_comments_ws`
(src/frob/vet/_capability_core.py:383). That function's own docstring describes
what it does: it matches a NEEDLE against the file's bytes via a
whitespace-tolerant pattern, excluding comment spans. It is a text search that
tolerates reformatting. It has no notion of whether the matched text sits in
value position or type position, because it never asks the parser.

So a type-only construct and a real runtime dynamic import are the same bytes,
and the check cannot distinguish them. This is the lexical-hook class -- a check
comparing text where structure was meant -- and it is the twelfth recorded
instance. This project carries a standing directive that checks must parse and
compare symbols, never substrings.

WHAT MAKES THIS INSTANCE WORSE THAN MOST: OPAQUE001 is a SECURITY-ADJACENT gate.
Its module docstring calls its subject an "evasion-indicative dynamic lookup".
Firing it on erased type syntax teaches the reader that this gate produces noise,
and the cheapest response is a waiver. A security gate whose findings are
routinely waived has been disarmed without anyone deciding to disarm it -- and
the consumer's own round-4 audit, filed here as T-4157, records a waiver on this
exact gate whose stated premise later expired unnoticed. The two findings
compound: a noisy gate produces waivers, and waivers are not re-evaluated.

THE SECOND HALF OF THE REPORT IS A DIFFERENT DEFECT AND SHOULD NOT BE BUNDLED
INTO THE SAME FIX: PARSE002 trips on a trailing comma their TSX grammar rejects.
That is a grammar-coverage problem, not a position problem -- valid source that
our parser cannot read. Note the interaction though: a parse failure means no
tree, and no tree is exactly when a needle-based fallback looks attractive.
Establish whether the opaque scan falls back to text when the parse fails; if it
does, then fixing the position question requires the parse to succeed, and the
two findings are ordered rather than independent.

WHAT TO DO
  1. Decide the construct by PARSE POSITION, not by bytes. The tree-sitter grammar
     distinguishes a type annotation context from a value context; use it.
  2. Establish what happens when the parse fails. If the scan degrades to a text
     search, that is a silent correctness change: the gate becomes a different,
     weaker check without saying so. It must report that it could not parse
     rather than quietly answering a lexical question instead.
  3. Audit the other needles fed through this same path. The helper is generic, so
     any construct detected this way has the same blindness. Report how many
     needles exist and which are position-sensitive.
  4. File the TSX trailing-comma grammar gap separately after determining the
     ordering above.

MUST-FIRE FIXTURE:   a genuine value-position dynamic import with a non-literal
                     specifier still fires OPAQUE001.
MUST-STAY-QUIET:     a type-position import expression fires nothing.
THIRD FIXTURE:       when the file cannot be parsed, the gate reports the parse
                     failure rather than silently falling back to a text match.

ACCEPTANCE
- Position decided from the parse tree, not from bytes.
- Parse-failure behaviour made explicit and non-silent.
- The needle population audited, with the position-sensitive ones named.
- The TSX grammar gap filed separately, ordered against this fix.
- All three fixtures committed.
