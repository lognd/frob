---
id: T-4119
title: a closed ticket's evidence is re-resolved against the current tree, so a later
  rename retroactively breaks a ticket that was correct when it landed
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: high
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
acceptance:
- text: given a closed ticket with valid evidence, when a later commit renames the
    test it cited, then no finding is reported against the closed ticket
  evidence: []
- text: given an open ticket whose cited test is renamed, when the gate runs, then
    the broken binding is still reported exactly as today
  evidence: []
- text: given a close attempted against a test that does not exist at close time,
    when close runs, then it is still refused
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CLOSED TICKET'S EVIDENCE IS RE-RESOLVED AGAINST THE CURRENT TREE, so any later
rename of a test retroactively breaks a ticket that was correct when it landed.
Reported as logand.app-v2 F-310: COV003 fired on T-0252's evidence because a
LATER ticket, T-0272, renamed the test the older one cited. Their proposed rule
is the whole ticket in one sentence: a closed ticket's evidence should be frozen
at its land commit, not re-resolved against the current tree.

THIS IS A ROOT CAUSE WE HAVE REPEATEDLY TREATED AS SYMPTOMS. The queue already
carries several tickets in this neighbourhood -- rebinding evidence ids when
tests are renamed or parametrized, an orphaned-evidence guard that did not fire
on a rename, and a ticket about evidence naming variants that were renamed away.
Every one of those is a tool for REPAIRING the breakage after it happens. None
of them asks the prior question the consumer just asked: why is a landed,
closed ticket's evidence being re-evaluated at all?

WHY THE CONSUMER IS RIGHT, and why this is worth more than another repair tool:

  1. THE CLAIM A CLOSED TICKET MAKES IS HISTORICAL. Its evidence asserts "at the
     commit where this landed, these tests existed and passed." That statement
     is either true or false forever, and nothing done in the tree afterwards
     can change it. Re-resolving it against today's tree replaces a true
     historical claim with a false present-tense one.
  2. IT PUNISHES THE WRONG TICKET. The agent working the LATER ticket did
     nothing wrong -- it renamed a test, which is ordinary work -- and gets a
     finding attributed to a ticket it never touched. The cheapest way to clear
     it is to edit the closed ticket's record, which corrupts history to satisfy
     a check.
  3. IT IS A STANDING CONTRIBUTOR TO THE ERROR FLOOR. This repo has already
     measured a drive where orphaned evidence from deletions and renames was
     the entire error floor. That was treated as a burndown; it is a design
     consequence that will regenerate every time anyone renames a test.
  4. THE PRECEDENT ALREADY EXISTS HERE. This repo established that landed
     done-reports are historical artifacts that must not be rewritten. Evidence
     on a closed ticket is the same kind of object and should get the same
     treatment. The inconsistency is the defect.

WHAT TO BUILD
  a. FREEZE EVIDENCE RESOLUTION AT THE LAND COMMIT for any ticket in a closed
     state. The land commit is already recorded on the ticket, so the anchor
     exists -- this is a question of which tree the resolver reads, not of new
     data.
  b. DECIDE WHAT REPLACES THE LOST SIGNAL, and say so explicitly. Re-resolution
     was presumably catching something real: an evidence id that never existed,
     or a ticket closed against a test that was already gone. Freezing must not
     turn that into a silent pass. The honest split is that a closed ticket is
     verified ONCE, at close, against the tree it closed against, and never
     again -- so strengthen the close-time check by exactly as much as the
     ongoing check is weakened.
  c. LEAVE OPEN TICKETS ALONE. An in-flight ticket's evidence SHOULD track the
     current tree; that is the whole point. The change is state-conditional and
     must be proven not to weaken the open case.

DO NOT IMPLEMENT THIS AS A WAIVER OR AN EXEMPTION LIST. An exemption that
matches the normal case disables the guard, and "every closed ticket" would be
most of the queue. This is a change to WHICH TREE the resolver reads for a
closed ticket, not a suppression of its findings.

THREE OTHER ITEMS CAME IN THE SAME REPORT and are noted here rather than filed
separately only if they prove to be the same mechanism -- check before assuming:
a doc directive on a private helper fired a rule the consumer's playbook does not
document; two wiring findings on dependency-injected guards were waived per an
existing pattern the queue has now seen three times; and renamed tests were
flagged as not test-first, which the consumer marks as a repeat. The last one is
plausibly the SAME rename event seen by a different gate -- if so it belongs in
this ticket's fix, and if not it needs its own. Determine which.

MUST-FIRE FIXTURE:   a ticket closed with valid evidence stays clean after a
                     LATER commit renames the test it cited.
MUST-STAY-QUIET:     an OPEN ticket whose cited test is renamed still reports the
                     broken binding -- the open case is unchanged.
THIRD FIXTURE:       a ticket that attempts to close against a test that does not
                     exist at close time is still refused.

ACCEPTANCE
- Closed-ticket evidence resolves against the land commit, not the working tree.
- The open-ticket case is proven unchanged.
- The close-time check is strengthened to cover exactly what the ongoing check
  stops covering, and that trade is stated rather than implied.
- The test-first finding on renamed tests is determined to be the same mechanism
  or filed separately.
- All three fixtures committed.
