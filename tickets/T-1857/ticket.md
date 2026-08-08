---
id: T-1857
title: 3 ty errors in src/frob/strata/_sync_may.py from T-1545 (invalid-type-form/invalid-argument-type)
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_drift_reports_clean
- tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_inserts_whole_node_grant_for_extended_kind
- tests/unit/strata/test_sync_may.py::TestApplySyncMayExtended::test_writes_only_changed_files
designated_repro_test: null
threat: null
component: null
---
main's unscoped `frob check --only lint` (ty) is red with 3 errors, all in
this file, all traced to T-1545's `sync_may_extended_report`/
`apply_sync_may_extended` addition:

1. src/frob/strata/_sync_may.py:402 `invalid-type-form`: `_MaySyncResult =
   "FileMaySyncResult | FileMayExtendedSyncResult"` is a plain string
   assignment (not annotated as `typing.TypeAlias`), so ty treats
   `_MaySyncResult` as a `Literal[...]` string VALUE, not a type alias --
   downstream annotations that reference it as a forward ref
   (`"tuple[_MaySyncResult, ...]"` at `_write_changed_may_files`) then
   fail with "Variable of type Literal[...] is not allowed in a parameter
   annotation". `FileMayExtendedSyncResult` is defined below this line
   (line 466), which is presumably why the original author used a bare
   string instead of an eager `X | Y` expression -- needs `TypeAlias`
   (`typing.TypeAlias` import + `_MaySyncResult: TypeAlias = "..."`) so
   the deferred string is understood as an alias, not a literal.

2. src/frob/strata/_sync_may.py:598/644 `invalid-argument-type`:
   `_extended_may_additions` declares `capability_files: tuple[str, ...]`
   (line 593), but both its call site (line 644, passed
   `_sorted_capability_files(root)`) and its own internal forward to
   `_bind_conformance_inputs` (line 598, which requires `list[Path]`)
   disagree -- `_sorted_capability_files` (src/frob/strata/
   _selfconform.py:474) returns `list[Path]`, not `tuple[str, ...]`. The
   parameter annotation is simply wrong; should be `list[Path]` to match
   what every caller actually passes and what it forwards downstream.

Confirmed pre-existing and unrelated to any of this agent's own tickets:
`git diff main -- src/frob/strata/_sync_may.py` is empty at the point this
was filed. File ownership: `src/frob/strata/**` is this agent's held
scope per the standing series brief.

frob:waive BUG002 reason="both defects are ty (static type-checker) findings, not runtime behavior -- pytest exercises an already-imported, already-typechecked module, so no pytest node id can differ in pass/fail between the pre-fix and post-fix checkout the way BUG002 wants: the annotation is either well-formed (ty passes) or not (ty fails), and that distinction is invisible to any test the running interpreter executes, only to a separate static-analysis pass over the source text. The 3 bound evidence ids are the module's existing real coverage (sync_may_extended_report/apply_sync_may_extended behavior), demonstrating the fix did not change runtime behavior, which is the correct and only evidence a pure type-annotation fix can carry."