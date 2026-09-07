---
id: T-4264
title: 'drive the posix gate errors to zero: formatter drift, two stale acks, a broken
  tests edge, a missing doc edge, three unreachable bindings, and a waiver whose symref
  does not match'
state: in-progress
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/vet/_bare_toolchain.py
- src/frob/check/_python.py
- src/frob/lang/_walk_bash.py
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the integration run's own unscoped gate invocation, when it runs on
    the fixed tree, then it reports zero errors apart from any that belong to tickets
    still in flight
  evidence: []
- text: given the formatter, when it runs on the fixed tree, then it reports no files
    needing reformatting
  evidence: []
- text: given the type-check refusal helper's rule finding, when it is resolved, then
    the resolution addresses why the existing waiver's symref did not match rather
    than adding a second waiver
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DRIVE THE POSIX GATE ERRORS TO ZERO. This is the release blocker. Measured from
the first integration run that has ever seen the current tree.

THE TEST SUITE IS ALREADY GREEN. That run collected 13,668 tests and failed
zero. The job still exits non-zero because the gate step reports 19 errors and
the formatter reports work to do. Do not go looking for test failures; there are
none on this platform.

THE EXACT SET, taken from the run's own tool summary and finding lines.

  FORMATTER: 33 files would be reformatted. Run the project's format verb rather
  than reformatting by hand, and commit the result as its own change.

  DRIFT001, two sites: a gate entry point and the rule-registry scan both have
  digests that moved since their last acknowledgement, one with four dependents
  and one with twelve. These are acknowledgement updates, not code fixes, and
  the finding text names the exact command for each. Read what actually changed
  before acknowledging; an ack is an assertion that the dependents are still
  correct, not a way to silence the gate.

  DRIFT002, one site: a tests edge from the ruff autofix helper names a test that
  no longer resolves. Find where that test went and repoint the edge.

  COV001, one site: a public constant in the bare-toolchain module has no doc
  edge.

  COV006, three sites: the bash walker's tests bind private symbols the call
  graph cannot reach from the test bodies. Check whether the tests genuinely
  exercise those symbols. If they do and the graph simply cannot see it, that is
  a waiver with a real reason. If they do not, bind a symbol they actually call.

  ARCH103, one site: a touched-files type-check refusal helper mixes input and
  output, string formatting, and three decision points. NOTE FIRST that a waiver
  for this rule already exists in the same file, on a neighbouring symbol, and
  the run reports it as NOT APPLIED because the symrefs do not match even after
  separator normalisation. Determine whether the intent was to cover this symbol
  and the waiver simply names the wrong one. If so the fix is the waiver's
  symref, not a refactor. That same file also carries an unmatched waiver
  reported by the waiver gate as matching zero findings, which is the other half
  of the same mismatch; resolve both together.

THE THIRTEEN REMAINING COV003 ERRORS ARE NOT YOURS TO FIX. They belong to two
tickets whose evidence names tests that exist only in unlanded worktrees, so the
ledger on the integration branch cites tests the branch does not have. They clear
when those tickets land, and their owners are already working them. Do not touch
those tickets, do not edit their evidence, and do not delete their ledger
entries. If your own run still shows them at the end, say so and leave them.

VERIFY THE WAY THE INTEGRATION RUN DOES. A scoped gate run proves nothing about
the unscoped total that the job actually computes. Before you claim zero, run the
gates the way the job runs them and quote the summary line.
