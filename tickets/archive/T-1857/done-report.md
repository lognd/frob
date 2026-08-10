## Done report

Fixed the 3 pre-existing ty errors main's unscoped `frob check --only lint`
reported in this file (from T-1545, not this agent's own T-1838 diff --
confirmed via `git diff main -- src/frob/strata/_sync_may.py` empty at
filing time, per coordinator instruction).

1. `_MaySyncResult = "FileMaySyncResult | FileMayExtendedSyncResult"` was a
   bare string assignment -- ty read it as a `Literal[...]` string VALUE,
   not a type alias, so every downstream forward-ref annotation quoting
   `_MaySyncResult` (`_write_changed_may_files`'s `results` param) failed
   with invalid-type-form. Added `from typing import TypeAlias` and
   annotated the assignment `_MaySyncResult: TypeAlias = "..."` -- this is
   the standard PEP 613 spelling for a deferred (string) alias, needed
   here because `FileMayExtendedSyncResult` is defined later in the file
   and a bare unquoted `X | Y` union would NameError at import time.

2. `_extended_may_additions` declared `capability_files: tuple[str, ...]`
   but every real caller passes `_sorted_capability_files(root)`'s actual
   return type, `list[Path]` (src/frob/strata/_selfconform.py:474), and
   `_extended_may_additions` itself forwards the same value straight into
   `_bind_conformance_inputs(model, root, capability_files)`, which
   requires `list[Path]` -- the annotation was simply wrong on both ends.
   Corrected to `list[Path]`, matching the one real type that flows
   through this parameter everywhere.

Verified: `frob check --only lint` now reports 0 errors (was 3, same 3
lines). Did not touch `_selfconform.py` (the actual `list[Path]` producer/
consumer) -- it already had the correct type; only this file's own
declared-vs-actual mismatch needed correcting.

### Changed
```
 tickets/T-1857/ticket.md | 55 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```

### Evidence
- `tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_no_drift_reports_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestSyncMayExtendedReport::test_inserts_whole_node_grant_for_extended_kind` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestApplySyncMayExtended::test_writes_only_changed_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 11 error(s), 658 warning(s), 742 waived
- error-findings: COV001@.claude/hooks/_shellscan.py, COV001@.claude/hooks/diagnosis-nudge.py, COV001@.claude/hooks/dispatch-telemetry.py, COV001@.claude/hooks/frob-suggest.py, COV001@.claude/hooks/frob-timeout-guard.py, COV001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, DOC003@docs/commands/sys.md, DOCENUM001@docs/modules/gates.md, PRE001@tickets/T-1857, TEST001@.claude/hooks/_shellscan.py
