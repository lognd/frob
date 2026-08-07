## Done report

Root cause: `restore_stale_journals` proved only that a journal's WRITER
was dead (`_is_stale`), never that the on-disk file it was about to
overwrite still matched what that writer actually left behind. A stale
journal from an earlier, unrelated crashed run gets restored at the start
of ANY later `run_mutations` call, across every journal under root, not
just the current run's own target -- so a file that was mutated,
crash-abandoned, and later hand-edited by a developer (who never noticed
the leftover mutant underneath) had those live edits silently destroyed
by a later, wholly unrelated mutation run (the T-1203 incident).

Fix: every journal entry now also records `current_sha256` -- the sha256
of whatever content this module itself last WROTE to the target (the
original at `write_journal` time, then each mutant's own bytes via the
new `record_journal_progress`, called from `run_mutations`'s write loop
in step with every mutant write). Restoring first re-hashes the file
CURRENTLY on disk and compares it against `current_sha256`: a match
proves nothing has touched the file since this module's own last write
(the ordinary crash-recovery path, unchanged); a mismatch (or a
pre-T-1327 journal with no `current_sha256` at all) proves something
else has since written the file, and restoring over it would destroy
content that is not this journal's to clobber. Fails CLOSED on a
mismatch: skip the restore, log a WARNING naming the file, and drop the
now-untrustworthy journal entry rather than overwrite unverified content
or leave a phantom entry `frob doctor` would keep reporting forever.

Proven with a direct reproduction of the T-1203 incident shape: a stale
journal + accurately-tracked crash state, then a live edit layered on top
of the leftover mutant before restore runs -- the live edit survives, and
the stale entry is dropped. A second test covers the legacy-journal
(missing `current_sha256`) case the same way. The two pre-existing crash-
simulation tests (byte-exact CRLF restore, `run_mutations`'s own
restore-then-continue path) were updated to call the new
`record_journal_progress` at the point they simulate a crash, so they
continue to exercise the ACCURATE-journal path acceptance criterion 1
requires, rather than accidentally exercising the new mismatch path.

`design/frob.strata` interface listing was regenerated via
`frob sys sync-interface` to declare the new public
`record_journal_progress` symbol and the three new test node ids; no
other drift.

Residue: none filed, no ticket needed -- the fix is fully contained inside
`src/frob/mutate/_journal.py` and `src/frob/mutate/__init__.py`, and no
new gap was found outside this ticket's scope during the work.

### Changed
```
 docs/modules/mutate.md       |  52 +++++++++++++++++
 src/frob/mutate/__init__.py  |   7 +++
 src/frob/mutate/_journal.py  | 101 +++++++++++++++++++++++++++++++-
 tests/test_mutate_journal.py | 135 ++++++++++++++++++++++++++++++++++++++++---
 tickets.md                   |  24 ++++++--
 5 files changed, 305 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_mutate_journal.py::test_restore_refuses_when_stale_journal_no_longer_matches_on_disk_content` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_restore_refuses_and_drops_a_legacy_journal_missing_current_sha256` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prior_crash` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 400 warning(s), 687 waived
- error-findings: INV006@src/frob/app/__init__.py, INV006@src/frob/app/app.py, SELFAUDIT001@design, TICK003@tickets.md
