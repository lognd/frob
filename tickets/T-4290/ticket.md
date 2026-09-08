---
id: T-4290
title: 'the last unowned self-gate errors: two doc anchors on private commit-order
  helpers, and four files needing reformatting'
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tdd_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the two doc anchors on private helpers, when they are resolved, then
    the resolution states whether the documentation describes those helpers individually
    or the gate's behaviour, rather than moving the anchors to silence the rule
  evidence: []
- text: given the formatter, when it has run, then no file would be reformatted and
    that change is committed separately from the anchor decision
  evidence: []
- text: given the unscoped gate run the job performs, when it is quoted, then the
    errors owned by the other two tickets are named as still-present rather than counted
    as this ticket's failure
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE REMAINING SELF-GATE ERRORS THAT NO OTHER TICKET OWNS: TWO DOC ANCHORS ON
PRIVATE SYMBOLS, AND FOUR FILES NEEDING REFORMATTING. Small, but they are part of
the set keeping the integration run red, and the run is the release gate.

MEASURED FROM BOTH POSIX LEGS OF THE SAME RUN, WHICH AGREE EXACTLY. Each reports
eleven errors with an identical breakdown: four files the formatter would rewrite,
one architecture error, nine coverage errors, one size error. Seven of the nine
coverage errors belong to a ticket being recovered separately, and the
architecture and size errors belong to another ticket already dispatched. What is
left, and what this ticket owns, is the two remaining coverage errors and the
formatter.

THE TWO COVERAGE ERRORS. Both are documentation anchors placed on private symbols
in the commit-order gate's module -- the two message-building helpers added
yesterday when that gate learned to report malformed directives. Doc anchors
normally cover the public surface, so the rule is asking whether these belong on
the public caller instead.

DECIDE THIS PROPERLY RATHER THAN MOVING THE ANCHORS TO SILENCE THE RULE. There is
established precedent in this repository for a private helper legitimately
carrying its own anchor when a documentation section genuinely walks through that
specific helper, and several such waivers exist with reasons recording exactly
that. So the honest question is whether the documentation actually describes these
two helpers individually, or whether it describes the gate's behaviour and the
anchors drifted onto the nearest private symbol. If the former, waive with that
reason. If the latter, move them to the public entry point. Either answer is
acceptable; guessing is not.

THE FORMATTER. Four files would be reformatted. Run the project's format verb
rather than hand-editing, and commit that as its own change so the diff stays
readable and separable from the anchor decision.

VERIFY UNSCOPED. A scoped gate run proves nothing about the unscoped total the job
computes. Before claiming these are cleared, run the gates the way the job runs
them and quote the summary line, and expect the errors owned by the other two
tickets to still be present -- say so rather than treating their presence as your
failure.
