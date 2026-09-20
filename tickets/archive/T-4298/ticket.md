---
id: T-4298
title: nothing on the land path checks repo-wide formatting, so drift accumulates
  faster than release tickets clear it
state: done
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
- src/frob/gates/__init__.py
- src/frob/gates/_land_format.py
- docs/modules/gates.md
- src/frob/graph/cache.py
- tests/test_ci_workflow_timeout.py
- tests/test_graph.py
- tests/unit/test_graph_lock_holder_naming.py
- tests/unit/test_graph_stat_trust_margin.py
- tests/unit/test_land_cross_ticket_leakage.py
- src/frob/gates/_waive.py
- tests/unit/test_land_format_gate.py
- docs/design/registry/check-coverage.yaml
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_land.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/__init__.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/_land_format.py
  reason: avoid scope collision with in-progress T-4281's lease on _land.py; land-path
    gates are wired via gates/__init__.py, so the new whole-diff formatting gate belongs
    in a new module registered there instead
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/gates.md
  reason: new gate function's frob:doc target lives here
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/graph/cache.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ci_workflow_timeout.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_graph.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_graph_lock_holder_naming.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_graph_stat_trust_margin.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_cross_ticket_leakage.py
  reason: mechanical whole-tree formatter drift cleared by this ticket's part 1 (frob
    format --code)
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: LANDFMT001 must be added to _KNOWN_GATE_RULES, the same 'add to the frozenset'
    step every prior newly-wired gate rule needed
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_format_gate.py
  reason: new test module for LANDFMT001, bound via this ticket's frob:tests directives
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: REG009/REG010 require a CHK-GATE-LANDFMT001 entry here; frob registry audit
    --sync-gate-rules writes it
  actor: logan
  at: '2026-09-08'
- op: add
  glob: design/frob.strata
  reason: declare tests/unit/test_land_format_gate.py's exec/fs.write capability use
    (SELFAUDIT001/SYS100), same testsuite node declaration test_land_parity_gate.py
    already carries
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001/SYS111 requires bumping the exec/fs.write ratchet ceiling in
    the same diff that adds a new via-list site
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: waive SCOPE002's whole-file closure noise on the two large shared gate-registry
    modules this ticket minimally touches, matching T-4255's precedent
  actor: logan
  at: '2026-09-08'
  old_length: 2794
  new_length: 4057
evidence:
- tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires
- tests/unit/test_land_format_gate.py::test_already_formatted_touched_file_is_quiet
- tests/unit/test_land_format_gate.py::test_no_diff_is_quiet
designated_repro_test: null
acceptance:
- text: given a land whose changed files include one the formatter would rewrite,
    when the land runs, then the drift is either refused with attribution or applied
    automatically, rather than reaching the integration branch unnoticed
  evidence:
  - tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires
  - tests/unit/test_land_format_gate.py::test_already_formatted_touched_file_is_quiet
  - tests/unit/test_land_format_gate.py::test_no_diff_is_quiet
- text: given the current drift, when it is cleared, then that mechanical rewrite
    is a separate commit from the mechanism change and the report names the count
    actually found rather than a count quoted from this ticket
  evidence:
  - tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires
- text: given the choice between refusing and rewriting, when the fix lands, then
    which was chosen and why is recorded where the next reader will find it
  evidence:
  - tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
NOTHING ON THE LAND PATH CHECKS REPO-WIDE FORMATTING, SO EVERY LAND CAN ADD DRIFT
THAT ONLY THE INTEGRATION RUN CATCHES -- AND IT IS ACCUMULATING FASTER THAN IT IS
BEING CLEARED.

MEASURED TODAY, TWICE. The first self-gate run this tree ever completed reported
four files the formatter would rewrite. A ticket was filed and landed to clear
exactly those four. Immediately afterwards, a fresh check of the working tree
reports SIX files needing reformatting -- more than before the fix -- because
several lands in between introduced new drift of their own. Clearing the count is
therefore not a fix; the count refills.

WHY THE EXISTING GATE DOES NOT CATCH THIS, AND IT IS BY DESIGN RATHER THAN BY
ACCIDENT. The formatting gate this project runs on the land path examines only
the directive-comment lines touched by the current diff. Its own scope note says
so plainly: it never scans the whole tree and is not a general formatter check, and
a clean result from it does NOT mean the repository is formatter-clean. That note
is honest and correct. The problem is that nothing else on the land path covers
what it deliberately excludes, so the honest disclaimer has become a gap.

THE CONSEQUENCE IS A RELEASE-BLOCKING GATE THAT ONLY FAILS AFTER THE FACT. The
integration run does check the whole tree, so drift surfaces there -- minutes to
an hour after the land that caused it, attributed to nobody in particular, and
mixed in with whatever else that run found. Whoever is driving the release then
files a ticket to clear a count that has already moved on. That is a treadmill,
not a check.

WHAT THE FIX SHOULD DO. Make the land path answer the same question the
integration run asks, for the files that land is actually touching. A land should
not be able to introduce a file the formatter would rewrite. Prefer checking the
land's own changed files over scanning the whole tree on every land, so the cost
stays proportional and the attribution stays exact -- the person who introduced
the drift is the one told about it, while it is still cheap to fix.

CONSIDER WHETHER FORMATTING SHOULD SIMPLY BE APPLIED RATHER THAN REPORTED. This
project already has a formatting verb and already runs automatic fixes on the
land path for other rule families. If applying the formatter to the land's own
changed files is safe and deterministic -- and formatters are chosen precisely
because they are -- then refusing a land over formatting is friction where a
rewrite would do. Decide deliberately and record which was chosen and why.

CLEAR THE CURRENT DRIFT AS PART OF THIS, and commit that as its own change so the
mechanical rewrite stays separable from the mechanism change. Expect the exact
file count to differ by the time you run it; report what you actually found rather
than the six named here.


## SCOPE002 waiver (T-4298)

# frob:waive SCOPE002 reason="src/frob/gates/__init__.py and src/frob/gates/_waive.py \
are large shared gate-registry modules whose existing frob:doc/frob:tests/private-helper \
closure spans dozens of unrelated files across the whole repo (docs/modules/*.md, \
tests/gates_suite/*, tests/unit/test_check.py, and more). T-4298 touches only: one new \
import, three small additions to existing dispatch/order lists (_ALL_GATES, \
_CANONICAL_GATE_ORDER, the run_gates dispatch dict), one __all__ entry, and one new \
frozenset literal in _KNOWN_GATE_RULES -- the exact same 'add to the frozenset'/'add a \
dispatch entry' shape T-3456/T-3466's own LANDPARITY001/002 and CROSSTICKET001 land \
comments already establish as the minimal touch these files require to wire a new gate \
in. Pulling every pre-existing closure edge already living in these two files into scope \
would be scope creep out of all proportion to that touch, and directly contradicts the \
attribution/proportionality point T-4298 itself makes about LANDFMT001's own touched-set \
design. Same doc-anchor/closure-tension precedent already documented by T-1010/T-1937/ \
T-3903/T-1895/T-3847/T-4255's own SCOPE002 waivers for this exact large-shared-file shape."