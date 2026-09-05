---
id: T-3846
title: distill README into the verbs, fix its make-target drift, and answer why no
  gate caught it
state: queued
kind: docs
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
OWNER DIRECTIVE 2026-09-05: "the README is super disorganized. I want you to
distill it into the verbs, check for drift (frob failure), and modernize it. I
want you to make it take after pytest, uv, and ty READMEs."

CURRENT STATE: README.md is 165 lines and already carries measurable drift.

DRIFT FOUND WITHOUT LOOKING HARD -- treat this as a sample, not the list:
  - line 25: "install: `pip install -e .`, then `make core`."
  - lines 18-25: tells the reader to run `make install-tool` to get natives,
    and explains "why the natives aren't a plain `pip install frob[...]` extra
    yet".
Both violate the standing directive that in a frob-enabled repo `frob <verb>`
IS the interface and workflows do not live in GNU-make recipes (T-1382). The
natives claim is also about to become false -- see the sibling ticket making the
cores default dependencies. Do not fix the README's install section by guessing;
land or read that ticket's decision and describe what is actually true.

THE OWNER'S "CHECK FOR DRIFT (FROB FAILURE)" IS THE IMPORTANT HALF. The point is
not just to correct today's README: it is that a README making false claims
about its own tool is a defect frob should CATCH, and frob did not catch this
one. Answer explicitly:
  - Which existing gate should have flagged `make core` / `make install-tool`
    in README.md? DOC010/docmake_gate resolves documented make targets against
    a real Makefile (see T-3415) -- did it not run on README.md, or did it pass
    because the root Makefile genuinely still has those targets? Measure, do not
    infer. If the targets exist, the drift is a POLICY violation (make-vs-frob),
    not a broken pointer, and no pointer gate can catch it.
  - Is there a rule that a README's documented commands must resolve to real
    frob subcommands? If not, say whether one is worth building and why. Do NOT
    build it under this ticket; file it.
Report both answers in the done report. That analysis is the durable output;
the rewrite is the perishable half.

WHAT TO WRITE. Take after pytest, uv, and ty:
  - Open with what frob IS in two or three sentences, then a single copy-paste
    install line and a first-run command that produces visible output. uv and ty
    both get a reader to a working command within one screen; this README
    currently spends its first screen on native-extension caveats.
  - DISTILL INTO THE VERBS. The organizing spine is the verb table -- check,
    test, ticket, format, coverage, ack, vet, doctor, scaffold, serve, release.
    One line each, what it does and when to reach for it. Detail lives in
    docs/; the README points there rather than duplicating it.
  - Show the enforcement loop compactly. The existing "annotate -> check ->
    fix-or-waive" framing is good and should survive the rewrite.
  - Cut anything that is a caveat, a ticket reference, or an explanation of why
    something is not yet done. A README is not a changelog and not a ticket
    body. The T-#### citations in prose are the clearest tell of the current
    structure and should not survive.
  - Keep it ASCII, no emoji.

DO NOT let the rewrite silently drop content that is load-bearing. Anything cut
that a reader genuinely needs moves to docs/ and is linked, not deleted. List in
the done report what moved where.

VERIFY EVERY COMMAND YOU PUT IN IT. Run each one. A README whose commands are
untested is how the current drift got there. If a command cannot be run in this
environment, say so rather than shipping it unverified.

MUST-FIRE FIXTURE:   a README command naming a nonexistent frob subcommand is
                     caught by whatever mechanism exists or is proposed (if
                     nothing catches it, that is the finding -- state it).
MUST-STAY-QUIET:     the rewritten README passes the full gate run clean.

ACCEPTANCE
- README restructured around the verbs, install and first-run in the first
  screen, no make-target instructions, no T-#### prose citations.
- Every command in it executed and confirmed.
- The two drift questions answered with measurements.
- A follow-up ticket filed if a README-command-resolution rule is worth adding.
- What moved to docs/ listed explicitly.
