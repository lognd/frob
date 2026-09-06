---
id: T-3950
title: 'F-189: mutation-evidence gate surfaces only at close/land, and needs a declared
  DDL exemption'
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
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/app/config.py
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
Consumer logand.app-v2 F-189, 2026-09-06. Two distinct complaints in one report;
treat them separately because only one is clearly ours.

COMPLAINT A -- THE GATE ARRIVES TOO LATE. "Neither frob check nor pytest flagged
the surviving mutant in 0006_admin_audit_log_source.py (nullable=False) during
development; close and land then refused." So the mutation gate is invisible for
the entire working session and fires only at the moment the user tries to finish.
Their ask: run the mutation gate in gates-fast when a ticket is NEAR DONE.

COMPLAINT B -- IT HARD-REQUIRES AN ESCAPE HATCH FOR MIGRATION DDL. They had to
pass --skip-mutation-evidence for an Alembic migration. Their argument: DDL
fidelity is already proven by the migration chain test, so mutation evidence is
the wrong instrument for that file class. Their ask: exempt Alembic migrations,
or any file in a declared DDL glob, by default.

THIS IS THE THIRD REPORT OF ONE SHAPE and that is the reason to act. F-188 (COV002
demands per-symbol annotation, surfaced late), T-3939 (COV002 provenance edges
refused at land rather than enforced at write time, apollo), and now F-189 are all
the same complaint: A CORRECT GATE THAT ARRIVES AT THE MOMENT OF FINISHING RATHER
THAN THE MOMENT OF WRITING. Nobody disputes the rules. They dispute that the first
notice comes after an hour of work is already committed. Read this ticket
alongside T-3939 rather than in isolation -- if there is one shared mechanism for
"surface a land-time gate earlier", build that once rather than three times.

ON COMPLAINT A, WHAT TO DETERMINE FIRST: what does "near done" mean mechanically,
and is the mutation gate cheap enough to run there? It is normally expensive --
that is presumably why it is not in gates-fast. VERIFY THE COST BEFORE PROMISING
THE MOVE. If it cannot run in gates-fast, the honest fix is different: warn at
`frob check` time that mutation evidence WILL be demanded at close, so the user
learns the obligation exists while there is still cheap time to satisfy it. A
warning that names a future refusal is worth more than a silent gate.

ON COMPLAINT B, BE CAREFUL -- THIS IS THE HALF THAT COULD GO WRONG. A
by-default exemption for a whole file class removes a real check, and "the
migration chain test proves it" is THEIR claim about THEIR test suite, not a
property frob can verify in general. Do not take it on trust. Two honest options:
  (a) exempt only when the DDL glob is DECLARED in config, so the exemption is an
      explicit, auditable statement by the repo rather than a silent default; and
  (b) require the declaration to name what DOES cover those files, so the
      exemption records its own justification.
An undeclared blanket exemption would be a silent zero in exactly the shape this
queue exists to prevent -- the check stops running and nothing says so.

DO NOT close this by documenting --skip-mutation-evidence better. A flag the user
must discover at the moment of refusal is the problem being reported.

MUST-FIRE FIXTURE: a surviving mutant in ORDINARY source is still refused at
close.
MUST-STAY-QUIET: a file under a DECLARED DDL glob does not demand mutation
evidence, and the declaration is visible in the run's output rather than silent.
THIRD FIXTURE: the earlier-warning path names the future refusal before close.

ACCEPTANCE
- The measured cost of running the mutation gate earlier, and the decision that
  follows from it.
- DDL exemption is declared, never a silent default.
- Cross-referenced with T-3939 and F-188; if one shared "surface it earlier"
  mechanism serves all three, say so and build it once.
- All three fixtures committed.