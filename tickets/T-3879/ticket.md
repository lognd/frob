---
id: T-3879
title: establish a tail-me result-block contract for every verb, and collapse high-cardinality
  warnings by default
state: queued
kind: feature
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
OWNER OBSERVATION 2026-09-05: "for the important messages, I think we do a
little bit of spam; is there any way we can compact the most important things at
the bottom so that tailing it gives you the best context? Or maybe the solution
is to ensure there is no spam for all the frob verbs."

BOTH, BUT THE FIRST IS THE PRIMARY FIX, and the reason is that most of the
"spam" is real information. Deleting it loses signal; burying the RESULT under
it is the actual defect.

FROB ALREADY HAS THIS PATTERN. It is not a new mechanism to invent, it is an
existing convention applied to some verbs and not others:

    SUITE-RESULT: exitstatus=0 collected=95 failed=0        (pytest conftest)
    LAND-PROOF: ticket=T-3820 commit=4e91c221 ... verified=SKIPPED-UNMEASURED
    gate-summary  29 errors, 4182 warnings, 0 unresolved, 857 waived
    gate:scope-note  NOTE: --only ran 2/65 gate familie(s); NOT run this
                     invocation (status unknown, not clean): ...

Those four are exactly right: compact, last, greppable, and the scope-note even
states what was NOT measured. The problem is that other verbs have no
equivalent, and that warnings are emitted AFTER the result in some paths.

MEASURED INSTANCES FROM ONE SESSION, 2026-09-05:
  - `frob ticket scope T-3403 --add ...` emitted 247 scope-closure warnings,
    then on the next invocation 272, with the actual outcome line
    ("T-3403: scope now [...]") buried among them. The advice in those warnings
    was also unfollowable at that volume, which trains operators to ignore
    closure warnings entirely -- the real cost.
  - `frob check --only release` emitted 423 DOCARCH001 warnings before the ONE
    REL001 error that was the entire point of the run.
  - `frob ticket new` emits 2 warnings then `created T-####` -- this one is
    already fine, and is the shape to copy.

THE CONTRACT TO ESTABLISH, one line stated plainly so every verb can be checked
against it:

  EVERY frob VERB ENDS WITH A COMPACT, GREPPABLE RESULT BLOCK, AND NOTHING IS
  PRINTED AFTER IT.

Concretely:
  1. A stable, prefixed last line (or short block) per verb, in the shape the
     four existing markers already use: `VERB-RESULT: key=value ...`. Machine
     -readable, one line where possible.
  2. It states the OUTCOME and the counts, including what was NOT done --
     gate:scope-note is the model. "0 errors" and "not measured" must never
     look the same.
  3. Warnings and per-item detail come BEFORE it, never after. `tail -n 20`
     must be sufficient to know what happened, for every verb, without knowing
     which verb it was.

AND THE SECOND HALF, which is the "no spam" answer: COLLAPSE HIGH-CARDINALITY
DETAIL BY DEFAULT. frob already does this too --

    WARNING: ... 239 more warning(s) collapsed -- set
             FROB_SCOPE_CLOSURE_VERBOSE=1 and retry to see all 247

That is the right behaviour and it should be the default everywhere a class of
finding exceeds a small threshold, not just in scope closure. Print the first
few, collapse the rest with the exact count and the env var to expand. Do NOT
simply silence them: the count is information and the expansion path must exist.

DO NOT hide anything behind a verbosity flag that a user must already know to
pass. The failure being fixed is that a confused operator cannot see what
matters; requiring a flag they do not know about reproduces it. Collapse with a
visible count, do not suppress.

WHAT TO DO
  1. Enumerate every frob verb and record whether it currently ends with a
     result block, and whether anything prints after it. That table is the
     durable artifact and is most of the work.
  2. Define the contract above in docs, in ONE place, with the four existing
     markers cited as precedent.
  3. Apply it to the verbs that lack it, starting with the measured offenders
     (`ticket scope`, `check --only`).
  4. Apply default collapsing to any finding class that can exceed a threshold.
     Pick the threshold and say why.

CONSIDER, and decide explicitly rather than defaulting: should the result block
be machine-parseable JSON behind a flag, given that agents are the primary
consumer? There is already `--json` on several verbs; the answer may be "the
text block is for humans, --json is for machines, and the contract applies to
both". Say which, and make sure --json output is not itself polluted by warning
text -- logand.app-v2 F-035 reports exactly that (`frob check --json` output not
parseable in a consumer repo).

MUST-FIRE FIXTURE:   a verb that prints anything after its result block fails a
                     test asserting the contract.
MUST-STAY-QUIET:     an already-conforming verb (`ticket new`) is unchanged.

ACCEPTANCE
- The per-verb table reported.
- The contract documented once, citing the existing markers.
- The measured offenders fixed.
- Default collapsing applied with a stated threshold and a visible count.
- The --json question answered, cross-referenced with F-035.
