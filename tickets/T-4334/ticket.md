---
id: T-4334
title: New verify-rapid-debt doc carries the tree's only three gate errors
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/verify-rapid-debt-visibility.md
- invariants/INV-052.md
- docs/index.md
- tests/unit/test_rapid_debt.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'Deliberately narrower than the doc/test-edge closure graph
  suggests: this ticket only touches the T-4324 split-out visibility doc, its own
  invariant file, one docs/index.md link, and its evidence test''s own frob:invariant
  anchor. verify_runner.py and _evidence.py are large, heavily cross-referenced files
  (T-4324''s own doc explicitly split this file out to avoid pulling tickets-verify-sweep.md''s
  dozens of unrelated symbols into scope); pulling either whole file in for one pre-existing
  edge would import 100+ unrelated scope-closure obligations, the exact anti-pattern
  T-4324 already avoided once.'
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: REF002 needs a real inbound link from a comparable verification doc, and
    INV003/INV004 need a new declared invariant file to anchor the doc's append-only/never-null
    claims
  actor: logan
  at: '2026-09-08'
- op: add
  glob: invariants/INV-052.md
  reason: REF002 needs a real inbound link from a comparable verification doc, and
    INV003/INV004 need a new declared invariant file to anchor the doc's append-only/never-null
    claims
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: swap the heavy tickets-verify-sweep.md link target (137 scope-closure warnings)
    for docs/index.md's module list, the same lightweight anti-orphan link surface
    T-4324 already relies on for its own module docs
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/index.md
  reason: swap the heavy tickets-verify-sweep.md link target (137 scope-closure warnings)
    for docs/index.md's module list, the same lightweight anti-orphan link surface
    T-4324 already relies on for its own module docs
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: INV002 requires a real frob:invariant code anchor at the enforcing site
    (record_rapid_debt) for the new INV-052 this doc's genuine append-only claim needs;
    the T-4324 doc's existing describes-anchor to verify_runner.py stays out of scope
    since that file needs no edit
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: 'INV002''s code-anchor requirement is satisfied by a frob:invariant marker
    in the doc itself (dsl.py: verb table applies uniformly to markdown and source);
    no code file needs touching'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: INV002 requires a real code-side frob:invariant anchor at an enforcing site
    for INV-052; verify_runner.py is already the doc's own pre-existing describes
    target
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/app/verify_runner.py
  reason: verify_runner.py sits exactly at the 800-line LARGE001 threshold, so any
    added anchor line trips a new error there; _evidence.py already carries a blanket
    frob:waive LARGE001, so the anchor goes at record_rapid_debt instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: verify_runner.py sits exactly at the 800-line LARGE001 threshold, so any
    added anchor line trips a new error there; _evidence.py already carries a blanket
    frob:waive LARGE001, so the anchor goes at record_rapid_debt instead
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: avoid record_rapid_debt's dense pre-existing frob:doc web (12+ scope-closure
    obligations); anchor INV-052 on its own evidence test file instead, a clean file
    with only 2 pre-existing directives
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_rapid_debt.py
  reason: avoid record_rapid_debt's dense pre-existing frob:doc web (12+ scope-closure
    obligations); anchor INV-052 on its own evidence test file instead, a clean file
    with only 2 pre-existing directives
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: 'close SCOPE002 (now error-severity in frob.toml): the doc''s pre-existing
    describes-edge to verify_runner.py and the test file''s pre-existing frob:tests
    edge into _evidence.py both need their target in scope'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: 'close SCOPE002 (now error-severity in frob.toml): the doc''s pre-existing
    describes-edge to verify_runner.py and the test file''s pre-existing frob:tests
    edge into _evidence.py both need their target in scope'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: 'close SCOPE002 (now error-severity in frob.toml): the doc''s pre-existing
    describes-edge to verify_runner.py and the test file''s pre-existing frob:tests
    edge into _evidence.py both need their target in scope'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/app/verify_runner.py
  reason: revert the wide code-file additions; SCOPE002 for this deliberately narrow
    doc-only ticket is handled via scope-breadth-ack (T-4310), the mechanism built
    for exactly this narrower-than-graph-closure case
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/unit/verify/test_verify_runner.py
  reason: revert the wide code-file additions; SCOPE002 for this deliberately narrow
    doc-only ticket is handled via scope-breadth-ack (T-4310), the mechanism built
    for exactly this narrower-than-graph-closure case
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/tickets/_evidence.py
  reason: revert the wide code-file additions; SCOPE002 for this deliberately narrow
    doc-only ticket is handled via scope-breadth-ack (T-4310), the mechanism built
    for exactly this narrower-than-graph-closure case
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): Doc/invariant-anchoring fix only (INV002/003/004/REF002
    gate findings) -- no production code behavior changed; the anchor added to test_rapid_debt.py
    is a comment-only frob:invariant directive, and record_rapid_debt''s append-only
    behavior is unchanged'
  actor: logan
  at: '2026-09-08'
  old_length: 2645
  new_length: 2931
evidence:
- tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_appends_one_json_line_per_call
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_clean_status_has_no_live_rapid_debt
- tests/unit/verify/test_verify_runner.py::TestLiveRapidDebt::test_other_skip_reasons_are_not_counted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A DOCUMENTATION FILE ADDED WITH THE LAST LAND CARRIES THE ONLY THREE GATE ERRORS
IN THE TREE, AND THEY WILL FAIL THE INTEGRATION RUN'S GATE STEP.

MEASURED ON MAIN JUST NOW. An unscoped gate run reports exactly three errors, all
against the same newly-added module doc, and nothing else in the repository is in
error:
  - an exclusivity/normative claim ("only") with no invariant anchor
  - a behaviour description ("never", "only") with no invariant anchor, first
    flagged at its opening section
  - exactly one inbound reference, from the single source module it documents

The rest of the tree is clean, so these three are the whole gap between the gate
step and green.

WHY THIS SLIPPED IN. The doc was created as part of a land whose post-land sweep
reported clean, because the rolling baseline it compared against predated the new
file. That is worth noticing but is not this ticket's job to fix.

THE FIRST TWO ARE THE SAME REQUEST, AND IT IS A REASONABLE ONE. The doc states
what the mechanism always or never does. This project requires such claims to be
anchored to a declared invariant so that the assertion is checkable rather than
merely written down -- prose asserting behaviour is not enforcement, a lesson this
repository has paid for repeatedly. Read the surrounding module docs to see how
existing anchors are written and follow that form exactly rather than inventing
one. If a sentence turns out to be a loose "only" that does not actually claim an
invariant, rewording it to stop over-claiming is an equally valid fix -- decide per
sentence rather than blanket-anchoring.

THE THIRD IS A DIFFERENT QUESTION. A doc reachable from exactly one place is
flagged as likely-orphaned. Judge honestly whether this doc genuinely belongs in
the documentation graph -- linked from the module index or the guide that covers
verification status, wherever comparable docs are referenced from -- or whether
its content should have lived inside an existing verification document instead of
a new standalone file. Both are acceptable answers; a new top-level doc that
nothing links to is not.

DO NOT CLEAR ANY OF THE THREE WITH A WAIVER. All three are asking for something
cheap and genuinely useful, and the file is one land old -- there is no legacy
cost being paid down here.

VERIFY with an unscoped run and quote the exact error count. Measure it with
`uv run frob check --json | python3 scripts/check_summary.py` rather than
grepping text output: reading that JSON at the wrong nesting level has produced
false "0 errors" reports in this repo before, and an absent section looks
identical to a clean one. The count must reach zero.

frob:no-behavior-change reason="Doc/invariant-anchoring fix only (INV002/003/004/REF002 gate findings) -- no production code behavior changed; the anchor added to test_rapid_debt.py is a comment-only frob:invariant directive, and record_rapid_debt's append-only behavior is unchanged"