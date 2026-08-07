## Done report

Split two of the eight remaining unwaived LARGE001 files at session start
(measured via `frob check --only archgate`, not the ticket's stale 51-file
prose): src/frob/tickets/_reporting.py (845 -> 754 lines) and
src/frob/vet/_scan.py (915 -> 765 lines). Both splits are verbatim
relocations of a cohesive function family into a new sibling module,
re-exported from the original for existing callers (no caller-visible
behavior change).

_reporting.py: the attach()/_attachment_bytes/_next_attachment_path/
_record_attachment quartet moved to _reporting_attachments.py (its own
filesystem-I/O boundary). Repointed docs/modules/tickets.md's
frob:describes edge and tests/test_tickets.py's frob:tests directive to
the new file.

_scan.py: the seven per-rule Violation-constructor functions
(_vet001/002/003/004/006/011_violation, _quarantine_violation) plus their
shared _lockfile_name helper moved to _scan_violations.py. No cross-file
frob:tests/frob:describes directives named the old locations (grepped
clean). Also carries a new frob:waive INV006 on _scan.py for two
pre-existing 'only' design-prose hits (a waiver-reason string, a log
message) that were never anchored on main either -- unrelated to the
split itself, surfaced only because gate:invariant was run scoped to this
ticket for the first time.

Both source files were grepped for `frob:waive` before moving anything
(the portion-2 lesson in the T-1420 brief); no waiver directly attached to
either moved function family in either file.

Verified: ruff format/check clean on all 4 touched+created files; pytest
on tests/test_tickets.py -k Attach and tests/test_vet.py (full file, 244
tests) all green; frob check --only archgate --only wire --only
dead_symbols --only drift --only doclink --only invariant --only
pii_structural --only fmt --ticket T-1420 is 0 errors after both splits.
LARGE001 warning count dropped from 49 findings (measured pre-work-sweep
archgate baseline this session) to 47.

Not done this portion: src/frob/tickets/_models.py, _store.py,
_new_renumber.py, src/frob/vet/_capability.py (6070 lines, T-1074-flagged
-- needs a dedicated follow-up decision before splitting, not a plain
verbatim relocation), and the two strata-core Rust files
(strata-core/src/lib.rs 869, strata-core/src/parse/mod.rs 1744) remain on
T-1420's list for a future portion.

### Changed
```
 docs/modules/tickets.md                    |   2 +-
 src/frob/tickets/_reporting.py             | 127 ++------
 src/frob/tickets/_reporting_attachments.py | 140 +++++++++
 src/frob/vet/_scan.py                      | 215 +++-----------
 src/frob/vet/_scan_violations.py           | 201 +++++++++++++
 tests/test_tickets.py                      |   2 +-
 tickets.md                                 | 461 ++++++++++++++++++++++++++++-
 7 files changed, 852 insertions(+), 296 deletions(-)
```

### Evidence
- `tests/test_tickets.py::TestAttach::test_file_source_copies_and_records_sha256` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAttach::test_index_increments` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAttach::test_large_file_logs_warning` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestAttach::test_unknown_ticket_not_found` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestQuarantine::test_fresh_package_blocked` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestQuarantine::test_old_package_ok` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestQuarantine::test_network_failure_degrades_to_unverified` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestQuarantine::test_typosquat_name_blocked_before_any_registry_lookup` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestAllowConfig::test_vet_section_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 569 warning(s), 729 waived
- error-findings: none (measured, zero errors)
