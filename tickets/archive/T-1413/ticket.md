---
id: T-1413
title: DOC006 has no in-worktree path to zero for land-owned CHANGELOG.md findings
state: done
kind: docs
origin: human
created: '2026-08-01'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_changelog_is_an_archival_record_not_checked
- tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_doc_still_flagged_after_changelog_exclusion
- cmd:bash -c "grep -q _ARCHIVAL_LEDGER_FILES src/frob/gates/_doclink_docanchor.py
  || grep -rq _ARCHIVAL_LEDGER_FILES src/frob/gates/" exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: A genuine historical-record DOC006 finding in CHANGELOG.md can be dispositioned
    (waived or excluded) without a worktree agent hand-editing a land-owned file
  evidence:
  - tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_changelog_is_an_archival_record_not_checked
  - tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_live_doc_still_flagged_after_changelog_exclusion
threat: null
component: null
---
Found while working T-1412 (drain residual DOC006 to zero). CHANGELOG.md
carries a genuine, honestly-classifiable historical-record DOC006 finding
at line 1952 (a since-nonexistent _elaborate_module symbol named in a
0.9.0 release note). The correct disposition per DOC006's own rules is a
frob:waive comment naming the historical-record status -- but CHANGELOG.md
is land-owned (T-0731) and a scaffolded pre-commit hook refuses ANY
worktree commit touching it, comment-only doc waivers included. There is
currently no in-worktree path to zero for this finding.

Two options worth considering: (a) give frob ticket land a mechanism to
apply a queued DOC006 waiver comment to CHANGELOG.md on a ticket's behalf,
alongside its existing auto-generated changelog-entry behavior, or (b)
exempt CHANGELOG.md from DOC006 scanning entirely, the same way
tickets-archive.md is already excluded, on the reasoning that CHANGELOG.md
is equally an append-only historical record where every entry documents
a past release rather than the current tree.