## Done report

T-0969 leaf: DOC006 was the dominant WARN family (584 of 1584 warnings,
350 files). Measured the split before touching anything, per
instruction:

  500  tickets/archive/**            (85.6%)
   10  tickets.md
   49  tickets/T-*/{ticket,done-report}.md  (32 files, LIVE/not archived)
   25  docs/**                        (12 files)

The prior belief (largely archival) held: 85.6% under `tickets/archive/
**`. Root cause: `doc006_gate` already has an exclusion for exactly this
class of file (`_ARCHIVAL_LEDGER_FILES = frozenset({"tickets-archive.md",
"CHANGELOG.md"})`, the pre-v2-migration monofile archive) -- it was never
extended when the archive migrated to a sharded per-ticket directory
(`tickets/archive/T-*/done-report.md`), so every archived done-report's
correct-at-the-time command citations (several now-removed subcommands:
`frob edit`/`frob dispatch`/`frob mission`/`frob todo`, named honestly
while those commands still existed) tripped DOC006 as if they were live,
broken docs.

Fix: added `_ARCHIVAL_DIR_PREFIX = "tickets/archive/"` and an `_is_
archival_doc()` predicate mirroring the existing exact-name check,
swapped into `doc006_gate`'s one call site. Did NOT touch `_tracked_md_
files` (shared by DOC004/DOC005 -- widening beyond DOC006 was explicitly
out of scope) and did NOT touch `tickets.md`'s findings or any live doc
content. Measured DOC006 before/after against the real repo: 584 -> 88
(a drop of 496, matching the 500 archive-directory count within the
small overlap the fixed test-shape-target check contributes).

`tickets.md` check, as asked: STILL EXISTS, 545KB/11252 lines, last
real commit 2026-08-07 (T-1763's land) while `tickets/T-*/` directories
have moved on every land since -- roughly 150+ lands stale. `LEDGER_
PATH`/`_LEDGER_NAME` ("tickets.md") remains a live constant used
throughout scope-matching as a path-name literal, but that does not by
itself prove the physical file is still read/written -- `ledger_path()`/
`tickets_dir()` in `_store.py` are docstringed "legacy"/"single mode".
This looks like a genuine leftover, not confirmed dead code -- filed as
its own investigation (T-2134) rather than assumed and deleted.

Did NOT fix: the 25 live docs/** findings or the 49 live (non-archived)
ticket-body findings -- both need real per-pointer judgment (which
command was renamed to what, which anchor moved where), not a
categorical exclusion, and touching 32 OTHER tickets' own body content
is its own scope decision. Filed as T-2135, scoped to 11 of the 12 live
doc files (docs/modules/tickets.md excluded from its scope -- currently
leased/in-progress on T-1973 and others; add once free) and left the
49 ticket-body findings' own path forward described in the ticket body
rather than pre-scoped, since which of those 32 files are genuinely
stale-in-place vs. simply not-yet-archived needs its own look.

One live-repo hazard hit and corrected mid-task: I ran `frob ticket new`
for T-2131 itself directly in the SHARED ROOT (not a worktree) before
realizing the mistake -- it auto-committed to main (`ecd20d747`). Root
was left clean (no uncommitted dirt), but this violated the standing
"never edit the shared root" rule; flagging plainly rather than
smoothing over it. All subsequent work happened correctly in worktree
`.claude/worktrees/t2131-doc006`.

## Done report

Changed:
src/frob/gates/_docptr.py::_ARCHIVAL_DIR_PREFIX
src/frob/gates/_docptr.py::_is_archival_doc
src/frob/gates/_docptr.py::doc006_gate (call site swapped to the predicate)

Evidence:
tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_sharded_archive_dir_is_an_archival_record_not_checked
tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_ticket_dir_still_flagged
(47/47 collected/0 failed across tests/test_docptr_gate.py; repro test
confirmed FAILED_AT_PARENT via --check-repro --base-ref 70b6107ca
against its own pre-fix commit, playbook 7b)

Filed: T-2134 (tickets.md staleness investigation), T-2135 (DOC006
remaining 88: live docs/** repair + live ticket-body triage, parented
to T-0969)

Gates: frob check --ticket T-2131 --only scope --only prework clean (0
errors) after a fresh `frob test --collect` (9892 node ids) and `frob
ticket sweep T-2131`; repo-wide DOC006 measured 584 -> 88 via `frob
check --only docblocks --json`

### Changed
```
 src/frob/gates/_docptr.py |  34 ++++++++++-
 tests/test_docptr_gate.py |  47 +++++++++++++++
 tickets/T-2131/ticket.md  |  13 +++-
 tickets/T-2134/ticket.md  |  51 ++++++++++++++++
 tickets/T-2135/ticket.md  | 151 ++++++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 294 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_sharded_archive_dir_is_an_archival_record_not_checked` (pytest node id, verified passing when recorded)
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_ticket_dir_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/gates/_docptr.py, SELFAUDIT001@design, TICK004@tickets.md
