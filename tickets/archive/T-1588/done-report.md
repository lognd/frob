## Done report

ledger v2 now has a real per-ticket stale-snapshot guard.

Added `ledger_digest_map(root)`/`archive_digest_map(root)` to
src/frob/tickets/_store.py: v2's per-id fingerprint analog of the v1
`ledger_digest` monofile primitive -- `{ticket_id: ledger_digest(that
ticket's ticket.md)}`, empty map on a non-v2 repo. `write_all`/
`write_archive`'s `expected_digest` parameter is now `str | dict[str, str]
| None`: v1 keeps the old monofile `str`, v2 accepts a digest map from
`ledger_digest_map`/`archive_digest_map`. `_write_all_v2`/
`_write_archive_v2` re-fingerprint only the ids the caller's map covers
against their CURRENT on-disk digest (`_stale_v2_ids`), under the same
`ledger_lock` the v1 branch already holds; any mismatch -- a sibling wrote
or deleted that ticket since the load -- refuses the whole call
(`Err(LedgerChangedSinceLoad)`), same contract as v1. A str handed to a
v2-mode write (a not-yet-updated caller) is treated as "no check", never
misapplied as a per-id digest. `None` preserves unconditional-overwrite
for both modes, unchanged.

Chose a per-id map over a tree-wide digest per the ticket's own design
guidance: a tree-wide digest would make a wholesale write to ticket A
refuse merely because unrelated ticket B also changed since the load,
throwing away v2's structural benefit.

Investigated every current caller of write_all/write_archive
(_archive.py, _new_renumber.py, _land_finalize.py, scaffold's unrelated
_managed.py which is a different expected_digest concept entirely): both
archive() and renumber_one() already dispatch to v2-native paths
(archive_v2/renumber_one_v2) that use per-ticket git mv and never reach
write_all/write_archive at all, so they were never exposed to this gap.
renumber(root)'s plain contiguous-renumber path (distinct from
renumber_one) has no v2 dispatch and reaches write_all's v2 branch via the
generic mode dispatch without building a digest map -- wiring it is out
of this ticket's scope (src/frob/tickets/_new_renumber.py is not in
scope), filed as a follow-up (draft T-1630, cite the real id
once landed).

Documented the new guard in docs/design/ledger-v2.md's lock-model section
(new "3.1 Stale-snapshot guard for wholesale writes (T-1588)"
subsection), including the renumber(root) gap and the follow-up pointer.

Added a v2 mirror test suite to tests/test_ticket_store_stale_snapshot.py
(TestWriteAllRefusesAStaleSnapshotV2, TestWriteArchiveRefusesAStaleSnapshotV2,
TestLedgerDigestMapV2) alongside the existing v1-pinned classes, per the
ticket's own instruction not to convert the v1 cases. 17 tests in the file
total (7 pre-existing v1 + 10 new v2), all pass.

One self-caught bug during implementation: an initial edit accidentally
duplicated the `frob:ticket T-1254` directive onto the newly-multi-line
`_write_all_v2` def, which COV005 correctly flagged as the directive
riding onto a private symbol away from its original public binding (on
`write_all`) -- removed before finishing; only `frob:ticket T-1588` marks
the new private helper.

Verification:
- pytest tests/test_ticket_store_stale_snapshot.py: 17 passed
- pytest tests/unit/test_ticket_store.py: 65 passed (no regression)
- pytest tests/test_tickets.py -k "Archive or Renumber": 16 passed (no
  regression in the real callers)
- frob check --only test --ticket T-1588: 0 errors
- frob check --only coverage --only doclink --only docanchor --ticket
  T-1588: 0 errors (7 errors seen on an earlier pass were the accidental
  COV005 self-inflicted regression above, self-fixed and re-verified 0
  errors after)
- frob check --only archgate --only scope --only prework --only fmt
  --ticket T-1588: 0 errors after refreshing the pre-work sweep
  (frob ticket sweep T-1588) -- the 3 ARCH001 errors and stale PRE001 seen
  were pre-existing, in files this ticket never touches
  (_land_cmd.py/_land.py/_mutation_sweep_queue.py)
- frob check --land-parity: clean, 0 unscoped errors

### Changed
```
 tickets.md | 48 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 46 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshotV2::test_external_replacement_between_load_and_write_all_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestWriteArchiveRefusesAStaleSnapshotV2::test_external_replacement_between_load_and_write_archive_is_refused` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestLedgerDigestMapV2::test_map_keys_are_ticket_ids_values_match_ledger_digest` (pytest node id, verified passing when recorded)
- `tests/test_ticket_store_stale_snapshot.py::TestWriteAllRefusesAStaleSnapshotV2::test_v1_style_string_digest_in_v2_mode_is_treated_as_no_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 412 warning(s), 797 waived
- error-findings: none (measured, zero errors)
