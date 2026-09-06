---
id: T-4032
title: 'F-239: SCOPE001 fires on a gitignored symlink and on a ticket the run itself
  just filed, penalising the encouraged behaviour'
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
- src/frob/gates/_tickets_gate.py
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
Consumer logand.app-v2 F-239, 2026-09-06:

  "T-0209: the node_modules symlink the setup requires and the [freshly filed
   follow-up ticket] both trip SCOPE001 inside the filing ticket."

TWO SUBJECTS THAT SHOULD NEVER BE SCOPE SUBJECTS AT ALL, and each is wrong for a
different reason.

1. A GITIGNORED SYMLINK (frontend/node_modules). It is gitignored, it is a
   symlink, and the project's own setup requires it to exist. None of those
   describe a file a ticket can own or edit. A scope gate reasoning about
   untracked, ignored, non-file entries is reasoning about the wrong universe --
   the denominator should be tracked files. Note this connects directly to
   T-3978 (a scope glob matching zero TRACKED files is accepted silently): both
   are about scope using the filesystem where it should use the git index. If
   scope consistently derived its universe from tracked files, this instance
   could not arise.

2. A TICKET THE RUN ITSELF JUST FILED. This is the sharper half. Filing a
   follow-up ticket is a normal, encouraged act -- this queue is full of
   instructions to file rather than silently fix -- and doing it makes the
   filing ticket dirty in its own scope check. So the gate penalises the exact
   behaviour the system asks for. It is also self-referential in a way that
   cannot be resolved by the user: they cannot pre-declare the id of a ticket
   that does not exist yet, and they should not have to scope tickets/ just to
   file one.

   VERIFY WHETHER ledger WRITES ARE ALREADY EXEMPT SOMEWHERE. frob writes to
   tickets/ constantly during normal operation -- scope mirrors, evidence,
   done-reports -- so there is probably an existing exemption that this path
   misses, rather than no exemption at all. "Nothing exempts X" is a claim about
   our code; grep before adding a second mechanism. If an exemption exists and
   is not reached here, the fix is small and different.

WHY THIS MATTERS BEYOND ANNOYANCE: SCOPE001 is a blocking error. Both subjects
produce a refusal the user cannot legitimately clear -- they cannot delete the
symlink their build needs, and they cannot un-file a ticket they were right to
file. The only remedies are to widen scope to cover things the ticket does not
own, or to waive a correct-looking rule. Both teach that scope declarations are
paperwork rather than statements of intent, which is the habit this whole
subsystem exists to build.

RELATED, READ TOGETHER -- scope is accumulating a cluster of denominator
defects: T-3978 (zero-match globs accepted silently), T-4004 (SCOPE001/002
computed over the transitive import closure, so an EMPTY diff is already in
violation), T-4002 (subtractive mirroring destroys a sibling branch's scope), and
this. Four reports about what scope is computed OVER. Whoever takes any of them
should check the others first; a fix that narrows the denominator may resolve
several at once, and four separate narrowings would conflict.

MUST-FIRE FIXTURE: a genuine out-of-scope edit to a tracked file is still
flagged.
MUST-STAY-QUIET: (a) a gitignored symlink in the working tree produces no
SCOPE001; (b) a ticket filed BY the run does not put the filing ticket in
violation.
THIRD FIXTURE: scope's universe is the git index -- an untracked file cannot
produce a scope finding at all.

ACCEPTANCE
- Whether a ledger-write exemption already exists, answered by grep first.
- Scope's subject universe restricted to tracked files, stated explicitly.
- Checked against T-3978/T-4004/T-4002 so the denominator is narrowed once, not
  four times.
- All three fixtures committed.