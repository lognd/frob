---
id: T-1946
title: 'Deleting or renaming a test silently orphans other tickets'' evidence: nothing
  refuses it, and it is the entire current error floor'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT FINDING (2026-08-10). Deleting or renaming a test
silently orphans OTHER tickets' recorded evidence. Nothing refuses it at
the moment of the edit, and nothing catches it before land -- it only
surfaces later as COV003 on a ticket the author never touched.

MEASURED: this is 100% of the current unscoped error floor (4 of 4
errors, `frob check --only gates` at 2d8476ab4):

  COV003 T-0185 <- tests/unit/test_research_assets.py::
                   test_skill_frob_doc_anchor_resolves_in_guide
  COV003 T-1351 <- tests/unit/test_check.py::TestScopeDisclosure::
                   test_full_unfiltered_run_adds_no_disclosure
  COV003 T-1507 <- (same node)
  COV003 T-1512 <- (same node)

TWO INDEPENDENT ACTORS, ONE HOUR, DIFFERENT FILES -- this is a mechanism
failure, not carelessness:
  - commit 72902adc0 (coordinator) deleted the first test while removing
    the project-scope .claude/agents and .claude/skills copies.
  - T-1928's land e68f129b115f (agent) REPLACED the second test with
    `test_full_run_discloses_fmt_scope`, correctly asserting the opposite
    behavior -- a legitimate, well-reasoned change that silently broke
    three unrelated tickets.

Neither actor could have seen it: the orphaned tickets were outside both
scopes, and the deleting diff gives no signal. One deletion took out
THREE tickets at once, so blast radius is superlinear in how well-cited a
test is.

THE RULE ALREADY EXISTS AND DID NOT WORK. This exact hazard is recorded
(refactor invalidates out-of-scope edges; re-measure unscoped before
accepting a refactor land). It was written down and still happened twice
in an hour, to two different actors. Per the standing audit rule: when a
recorded rule is not followed, the rule is not the fix -- find what
enforces it.

FIX DIRECTION, preferred order:
(a) REFUSE AT THE MOMENT. A diff that deletes or renames a test node id
    bound as evidence on ANY ticket is statically detectable: the set of
    recorded evidence node ids is already in the ledger, and the set of
    removed node ids is derivable from the diff. Refuse the land, naming
    every orphaned ticket, and require either an evidence re-point or an
    explicit acknowledgement.
(b) Failing that, a pre-land gate that reports the orphan set.

DO NOT FIX IT THIS WAY: do not make COV003 lenient, and do not
auto-delete or auto-rewrite the orphaned evidence to make the gate go
quiet. The evidence binding is the only record that a ticket was ever
proven; silently repointing it fabricates proof. This is the WAIVE004
failure mode (a "safe" cleanup that deleted 55 live waivers) applied to
evidence. The correct outcome is a human/agent decision per orphan --
re-point to the replacement test, or re-scope the ticket and record fresh
evidence.

ACCEPTANCE: first test must FAIL before the fix -- construct a diff that
deletes a test node bound as evidence on an unrelated ticket, assert the
land is refused and the orphaned ticket id appears in the message. Then
assert a deletion of an UNBOUND test still lands cleanly (no false
refusal), and that a rename which re-points evidence in the same diff is
accepted.
