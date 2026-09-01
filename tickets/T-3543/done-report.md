## Done report

Folded the record-land-commit stub into the land itself: a per-ticket squash-apply land no longer writes _record_land_commit's dedicated follow-up commit (53 of the last 300 main commits, pure bookkeeping) -- root's tip after land() is now LandReport.commit_sha itself, exactly one commit. Ticket.land_commit stays None going forward for tickets landed this way; readers (_find_landing_commit in _lifecycle.py, scripts/verify_lands.py::load_land_commit) try the persisted field first (still authoritative for old tickets and --plan-finalized tickets) then fall back to a new derive_land_commit_by_grep (frob.tickets._land_squash), a fixed-string git log --grep for the literal 'land <id> ' substring every per-ticket land's own commit subject already durably carries (_land_merge._commit_message's exact shape). _record_land_commit itself is left defined and still covered by its own pre-existing tests (not deleted -- correct, tested out-of-tree/CAS machinery, simply no longer called from the hot path). Updated docs/modules/tickets-landing.md step 10.5 and docs/guides/coordinator-scripts.md's load_land_commit section. Rebound T-2220's stale evidence citation (the renamed test) via frob ticket evidence --archived --replace.

Changed:
src/frob/tickets/_land_squash.py::derive_land_commit_by_grep (new)
src/frob/tickets/_land_squash.py::_finish_real_land_report (no longer calls _record_land_commit)
src/frob/tickets/_land_squash.py::_record_land_commit (docstring note, unused by primary path)
src/frob/app/ticket_runner/_lifecycle.py::_find_landing_commit
scripts/verify_lands.py::load_land_commit
tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit (renamed/rewrote the field-write test to assert derive-on-read)
tests/unit/test_land_record_commit.py (new TestDeriveLandCommitByGrep)
docs/modules/tickets-landing.md, docs/guides/coordinator-scripts.md

Evidence:
tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_finds_the_squash_apply_commit_by_id_and_title_grep (new must-fire)
tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_returns_none_when_no_matching_commit_exists (new must-stay-quiet)
tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_land_commit_is_derivable_with_no_follow_up_commit (real land() end-to-end: exactly one commit, land_commit None, grep-derive resolves)
tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id (unaffected --plan path, still green)
tests/unit/test_coordinator_scripts.py::TestLoadLandCommit::test_returns_land_commit_for_a_landed_ticket (old-ticket field-first path, unaffected)
Full test_land_record_commit.py (8 tests) and TestRecordLandCommit (3 tests) run and green.

Gates: frob check --ticket T-3543 --budget 300 clean of attributable errors (2 remaining errors are pre-existing unrelated claude-config-drift)

### Changed
```
 tickets/T-3543/ticket.md         | 62 +++++++++++++++++++++++++++++++++++++++-
 tickets/archive/T-2220/ticket.md | 15 ++++++++--
 2 files changed, 73 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_finds_the_squash_apply_commit_by_id_and_title_grep` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_record_commit.py::TestDeriveLandCommitByGrep::test_returns_none_when_no_matching_commit_exists` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_land_commit_is_derivable_with_no_follow_up_commit` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_plan_land_finalized_ticket_is_resolvable_by_ticket_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestLoadLandCommit::test_returns_land_commit_for_a_landed_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 26 error(s), 4280 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3543, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
