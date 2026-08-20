---
id: T-2686
title: 'COV003 on 6 closed tickets: deleted/renamed test node ids, six materially
  different dispositions needed'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2344
- tickets/T-2348
- tickets/T-2365
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
6 CLOSED tickets (T-1397, T-1526, T-1688, T-2344, T-2348, T-2365) each
carry a COV003 finding right now: their bound evidence test node id no
longer resolves against the current tree. This is NOT one mechanical
fix -- it splits into materially different situations, each requiring
the original ticket's claim to be read before disposing of it.

## The six-way split (verified directly, 2026-08-19)

1. T-1397 -- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_rc_file_target_is_shared_not_duplicated
2. T-1526 -- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first

   Both cite the SAME now-deleted class (`TestCoverageFastUsesAbsoluteSubprocessRc`).
   The whole class is gone -- `tests/unit/test_makefile_coverage.py`
   has been substantially rewritten (consistent with this repo's own
   "no Makefile" directive), not merely reorganized. No 1:1 replacement
   test exists in the file today. Both tickets' original claims need
   to be read to determine whether ANY current test still proves them,
   or whether the underlying behavior (and therefore the claim) no
   longer applies at all.

3. T-1688 -- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_file_a_ticket_and_do_not_advance

   The CLASS still exists; this specific method does not. The closest
   surviving method by name, `test_unmeasurable_never_advances_
   watermark`, is plausibly related (both about "not advancing" under
   some condition) but is not obviously the SAME claim -- needs T-1688's
   original text read before treating it as a rebind target.

4. T-2344 -- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_gates_module_module_stays_clean
5. T-2348 -- same node id as T-2344 (both tickets cite the identical
   evidence id)

   The CLASS still exists; the cited method does not. The class today
   only has `test_new_lexical_decider_is_flagged` and `test_
   allowlisted_function_is_silent` -- neither an obvious rename match.
   Both tickets' original claims need reading.

6. T-2365 -- tests/test_lang_support.py::TestDeriveCapabilityRegistry::test_typescript_import_graph_is_a_reasoned_known_gap

   THE INTERESTING ONE, possibly not debt at all: the closest surviving
   method is `test_typescript_import_graph_is_implemented`. That is not
   a rename -- it is the OPPOSITE claim (a disclosed gap becoming
   implemented). If T-2365's original claim was "this is a known,
   disclosed gap" and later work actually implemented TypeScript import
   graph support, the honest disposition is CLOSE this COV003 finding
   as OBSOLETE (the gap the ticket documented no longer exists, not
   because the evidence needs rebinding but because the CLAIM does),
   not rebind to a test that now asserts the opposite.

## Root cause (why this class exists at all)

Deleting or renaming a test silently orphans OTHER tickets' evidence.
This is a KNOWN, expensive defect class in this repo -- it has
previously accounted for 4 of 4 of the entire measured error floor in
a prior investigation this session. This is the same mechanism
resurfacing. See the companion ticket (filed alongside this one) for
the systemic fix: a gate that refuses/warns when a cited node id is
deleted or renamed, so the deleter is caught at delete time instead of
a later, unrelated sweep discovering six orphaned citations at once.

## Disposition (per-ticket, NOT mechanical)

Each of the 6 needs at least one of three outcomes, decided only after
reading the ORIGINAL ticket body/claim:
- rebind to a real successor test that proves the same claim
  (`frob ticket evidence <id> --replace OLD NEW --reason "..."`)
- the claim is OBSOLETE (the thing it proved no longer applies, or
  was superseded/closed by later work) -- record that explicitly,
  do not silently rebind to a differently-scoped test
- no current test proves the original claim -- the ticket needs a
  genuine NEW test, not a citation swap

Do NOT touch evidence on any of these 6 closed tickets mechanically.
Each disposition needs the original ticket read first.
