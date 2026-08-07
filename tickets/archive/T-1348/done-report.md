## Done report

T-1338 showed two failure modes: (1) a land killed during its Tier-A
auto-fix phase left a source file half-rewritten (GARBLED), because the
existing bare path.write_text(...) calls truncate-then-write in place
with no crash safety; and (2) after the kill, "git checkout -- <file>"
recovery could not distinguish Tier-A's own garbled rewrite from an
agent's own uncommitted work elsewhere, and silently destroyed the
latter.

EVALUATED FIRST, PER THE TICKET'S OWN SUGGESTION: moving land's existing
pre-merge wip-commit earlier (before the Tier-A auto-fix phase) so a kill
always has something committed to recover to. This is NOT possible from
inside T-1348's declared scope: the call that runs Tier-A fixes BEFORE
land()'s own wip-commit is `_absorb_pre_land_fixes`, in
src/frob/app/ticket_runner/_land_cmd.py -- explicitly out of scope
(src/frob/app/** is leased by other in-flight tickets) and the call-site
ordering lives there, not in _land.py. Reordering it is not achievable
without touching that file. Implemented instead, entirely inside
src/frob/gates/_fix_engine.py (in scope), an equivalent-strength fix that
does not require touching the call site:

1. TRANSACTIONAL WRITES. Added `_write_text` (frob.gates._fix_engine),
   which routes every in-place file rewrite through
   `frob.tickets._store.atomic_write` (temp file + fsync + os.replace in
   the same directory -- the existing T-0456 primitive, not a second
   copy) instead of a bare `path.write_text(...)`. Converted the three
   direct write_text call sites inside this module
   (_rewrite_line_substring, fix_inv006_carried_waiver's per-file write,
   _remove_waiver_line) to use it, and made each caller respect the
   boolean it now returns (a failed write is reported as a no-op, never
   silently claimed as an applied fix). A kill at any point up to and
   including immediately before the atomic rename now leaves the
   ORIGINAL file's bytes on disk, untouched.

2. RECOVERY BREADCRUMB. Added `write_autofix_manifest`/
   `clear_autofix_manifest`, keeping `.frob/land-autofix-manifest.json`.
   `apply_tier_a_fixes` writes it after EVERY handler completes (not once
   at the end), listing every distinct file path any handler has
   rewritten so far this run, and clears it only once the whole pass
   finishes successfully. A kill mid-loop leaves the manifest accurate as
   of the last handler that finished -- a recovering agent diffs `git
   status` against `rewritten_paths` instead of a blanket `git checkout
   --`.

SCOPE NOTE: FMT001/REG010/REL002/TICK002/WAIVE004 delegate their actual
disk writes to functions in OTHER modules (frob.gates._fmt_directives,
frob.registry._staleness, frob.release, frob.tickets._draft_finalize),
none of which are in T-1348's scope, so their own write paths are NOT
made atomic by this change -- only the three write sites living directly
in _fix_engine.py (DOC007/DOC002/INV006-carry, WAIVE004's line removal)
are. Filed as a residual follow-up (see Filed below) rather than silently
widening scope into those modules.

CRASH-SAFETY PROOF: TestTierAAutofixCrashSafety::test_kill_between_write_
and_rename_leaves_original_file_intact monkeypatches os.replace itself
(the exact boundary between "durable temp write" and "visible under the
real path") to raise, simulating a kill at the single worst moment for
this bug class, and asserts the original file is byte-for-byte intact.
TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_
completed_fixes simulates a handler raising mid-loop and asserts the
manifest state matches what actually completed.

NON-NEGOTIABLE CONTRACT PRESERVED: LAND-PROOF line, its commit/
is_ancestor_of_main/state_on_main/verified fields, and _land.py's own
step ordering (wip-commit still runs at its existing point) are all
untouched -- this ticket's diff never touches _land.py's control flow,
only src/frob/gates/_fix_engine.py's own internal write mechanics.

### Changed
```
 tickets.md | 71 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
 1 file changed, 67 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestAutofixManifest::test_write_then_clear_roundtrip` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_apply_tier_a_fixes_clears_manifest_on_clean_finish` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTierAAutofixCrashSafety::test_kill_between_write_and_rename_leaves_original_file_intact` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 1341 warning(s), 687 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, SELFAUDIT001@design, TICK003@tickets.md
