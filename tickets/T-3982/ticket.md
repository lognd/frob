---
id: T-3982
title: 'F-194: rust formatting may reformat the whole crate instead of the touched
  set, manufacturing unowned diff (3 tickets tripped)'
state: queued
kind: bug
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
- src/frob/app/fmt_runner.py
- src/frob/check/_native.py
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
Consumer logand.app-v2 F-194, 2026-09-06:

  "cargo fmt -p <crate> -- <files> ignores the file list and reformats the whole
   crate. T-0155, T-0166 and T-0180 each reformatted level.rs/player.rs by
   accident and had to revert. Not a frob bug, but frob fmt (or the playbook)
   should document rustfmt --check <files> as the per-file form and the land
   pre-check should run rustfmt on the touched set only."

CREDIT THEIR OWN FRAMING: they explicitly say the cargo behaviour is not a frob
bug. It is not. The frob-owned part is the second half -- that our tooling hands
agents a whole-crate reformat when it means to check a touched set.

THREE TICKETS TRIPPED ON IT AND EACH HAD TO REVERT. That is the signal. A
footgun that catches three consecutive agents is not user error; it is a default
pointed the wrong way.

WHY THIS IS MORE THAN TIDINESS: a whole-crate reformat inside a ticket's branch
manufactures diff that the ticket does not own. Every downstream mechanism that
reasons about a touched set -- scope enforcement, COV/SCOPE attribution, land
diff-attribution, TDD ordering -- then reasons about files the ticket never
meant to change. It converts a formatting convenience into false attribution,
which is expensive to unpick and easy to land by accident.

WHAT TO DETERMINE FIRST, because the ask has two halves and only one is
certainly ours:
1. Does frob itself ever invoke the whole-crate form? Read
   src/frob/app/fmt_runner.py and src/frob/check/_native.py and find out. If
   frob's own fmt or land pre-check shells out to `cargo fmt` in a way that
   ignores a file list, that is a REAL defect and the primary fix -- change it
   to the per-file `rustfmt` form over the touched set only. If frob already
   does the right thing and only the agent playbook is wrong, say so plainly:
   the fix is then documentation, and claiming a code fix would be inventing
   work.
2. Whichever it is, the land pre-check must operate on the TOUCHED SET, not the
   crate. State which it does today, measured, before changing anything.

DO NOT fix this by adding a warning telling users to use the other command. The
whole complaint is that the wrong form is the one reached for; a warning after
the reformat has already happened is too late, and this repo's standing doctrine
is automatic over commands.

CROSS-LANGUAGE CHECK WORTH DOING WHILE HERE: if the rust path formats more than
the touched set, verify the python and TS paths do not have the same shape. One
language's over-broad formatter is a bug; three would be a design default.

MUST-FIRE FIXTURE: formatting a ticket's touched set leaves untouched files in
the same crate byte-identical.
MUST-STAY-QUIET: a genuine formatting violation IN the touched set is still
caught and fixed.

ACCEPTANCE
- Measured answer to whether frob invokes the whole-crate form, stated plainly
  even if the answer is "we already do it right and only the docs are wrong".
- Land pre-check demonstrably scoped to the touched set.
- Python/TS paths checked for the same shape.
- Both fixtures committed.