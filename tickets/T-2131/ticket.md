---
id: T-2131
title: 'DOC006: exclude tickets/archive/** sharded done-reports from CLI-pointer liveness
  checks'
state: done
kind: docs
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: doc006_gate's own test file, needed to add archival-directory exclusion
    coverage
  actor: logan
  at: '2026-08-11'
evidence:
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_sharded_archive_dir_is_an_archival_record_not_checked
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_ticket_dir_still_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0969 residue (parent epic: burn WARN-tier quality gates to zero).
DOC006 is the dominant WARN family: 584 findings across 350 files.
Measured split (2026-08-11, `frob check --only docblocks`):

  500  tickets/archive/**  (85.6%)
   10  tickets.md
   49  tickets/T-*/{ticket,done-report}.md  (live, not yet archived; 32 files)
   25  docs/**  (live docs; genuinely broken pointers)

`doc006_gate` already has an exclusion mechanism for exactly this class
of file (`_ARCHIVAL_LEDGER_FILES = frozenset({"tickets-archive.md",
"CHANGELOG.md"})`, the pre-v2-migration monofile archive) -- it was
never updated for the v2 sharded per-ticket archive directory
(`tickets/archive/T-*/done-report.md`), so every archived done-report's
correct-at-the-time command citations (several now-removed subcommands:
`frob edit`, `frob dispatch`, `frob mission`, `frob todo`) trip DOC006
as if they were live, broken docs.

Fix: extend the archival-exclusion check in `doc006_gate` to also match
`tickets/archive/**` (glob, not another exact-name entry), mirroring the
existing pattern rather than replacing it. Do NOT touch `_tracked_md_
files` itself (shared by DOC004/DOC005 too -- widening beyond DOC006 is
a different ticket's call). Do NOT touch `tickets.md`'s own 10 findings
here (see the sibling ticket filed for that -- the file looks stale/
orphaned, a separate small investigation, not a DOC006 exclusion
decision). Do NOT touch the 49 live (non-archived) ticket-body findings
or the 25 live docs/** findings here -- those need actual per-pointer
judgment/repair, not a categorical exclusion, and are their own,
separately-filed follow-ups.