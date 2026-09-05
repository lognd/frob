---
id: T-3862
title: 'a gate''s actual inputs are invisible: which argv ty ran, which lock SYS111
  read, which base PRE001 diffed'
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
Three findings from typani's dogfooding (FROBLEMS T-019, T-020, T-021) that are
one defect wearing three costumes: A GATE'S ACTUAL INPUTS ARE INVISIBLE TO THE
OPERATOR, so a user cannot reproduce what the gate saw, and disagreement between
the gate and a hand-run command is unresolvable without reading frob's source.

INSTANCE 1 (T-020) -- WHICH ARGV. frob's ty stage and a plain ty run disagree on
the SAME ty 0.0.78:

    uv run ty check src tests examples   ->  "All checks passed"
    frob check --only ty                 ->  3 errors + 2 warnings

The 3 errors are one unresolved-attribute finding reported once per platform
(linux/win32/darwin); the 2 warnings are unused `ty: ignore` directives the
plain run never mentions. Likely cause per the reporter: frob invokes ty with
its own flags (per-platform `--python-platform`, `unused-ignore-comment`
enabled) rather than the repo's `[tool.ty]` table.

NOTE THE POLARITY, because it changes the severity: frob is STRICTER, not
falsely green. Nothing is being missed. What is broken is REPRODUCIBILITY -- a
consumer repo cannot reproduce its own gate locally with the documented command,
so a red gate costs several round trips of guessing at flags.

INSTANCE 2 (T-019) -- WHICH LOCK. SYS111's capability-via ratchet reads only the
COMMITTED lock file. An agent created
docs/design/registry/capability-via-ratchet.lock.json with the raised ceilings
exactly as the SYS111 message instructs, re-ran `frob check`, and still saw
"above the committed ratchet ceiling of 0" for all six pairs. The findings
cleared only after `git add` + `commit`. Nothing in the message says the lock
must be committed first.

THIS ONE MAY BE CORRECT BEHAVIOUR WITH A BAD MESSAGE, and the fix must not
assume otherwise. docs/strata/surface.md is explicit that the ratchet is a
SECURITY control whose failure is asymmetric, and that deleting a lock entry
reads as `accepted_count=0` rather than "unchecked" precisely so the lock cannot
be rewritten to un-ratchet a capability. Reading only committed state is a
defensible extension of that: an uncommitted lock edit is not yet part of the
reviewed record. So DECIDE, do not just switch it to the working tree:
  (a) read the working tree, matching every other config file, and rely on
      review to catch an unjustified widening; or
  (b) keep committed-only and FIX THE MESSAGE to say "commit the lock, then
      re-run" -- which is the cheap, safe answer.
State the security argument either way. If (a), say what still prevents a
widening from being self-approved in the same uncommitted edit.

INSTANCE 3 (T-021) -- WHICH BASE. With `check_base = "main"` and HEAD on main,
PRE001/SCOPE001 report "diff against merge-base <sha> touches N file(s) but no
active ticket is derivable", where the sha is the LAST TICKET-CLOSE COMMIT, not
`check_base`. So a one-line docs commit made after a close needs its own ticket
to keep the gate green, and the message gives no hint why `main` vs `main` is
not empty. Confirm whether the close-commit base is intended (it plausibly is --
"since the last accounted-for state" is a sensible base for an accounting gate)
and if so, say so in the message.

THE COMMON FIX, and it is worth doing once rather than three times: A GATE THAT
DERIVES ITS RESULT FROM AN INPUT THE OPERATOR CANNOT SEE MUST NAME THAT INPUT.
Concretely:
  - a stage that shells out prints its exact argv once per run
  - a rule that reads a lock/config says which copy it read (committed vs
    working tree) when it refuses
  - a diff-scoped rule names the base sha AND says what that base IS
     ("last ticket-close commit"), not just the sha

CHECK THE OTHER SHELLED-OUT STAGES while you are here: ruff, pytest, cargo,
ctest, maturin. If ty's argv is unprintable today, theirs probably are too.
Enumerate which stages shell out and which of them can currently be reproduced
by hand from their own output. That table is the durable artifact.

DO NOT make the argv printing verbose-only. The whole failure is that a user
who is already confused cannot see it; putting it behind a flag they do not
know to pass reproduces the problem. Once per run, at the stage's own output
level, is the bar.

MUST-FIRE FIXTURES:
  - a ty stage run prints an argv that, executed verbatim, reproduces the same
    findings
  - a SYS111 refusal names which lock copy it read
  - a PRE001/SCOPE001 finding names the base and what it is
MUST-STAY-QUIET FIXTURE:
  - a clean run does not become noisy (the argv line is one line, not a dump)

ACCEPTANCE
- The three instances fixed.
- The (a)/(b) decision on SYS111 stated with the security argument.
- The shelled-out-stage reproducibility table reported.
- Fixtures committed.
