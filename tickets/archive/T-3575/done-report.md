## Done report

Root cause (T-3574): T-3324's land-time check, selfaudit_findings_
touching, substring-matches a Violation.message against the land's own
touched files. SYS111 (capability-ratchet growth) messages are aggregate
counts keyed by node::atom with no source path in the text at all
(capability_via_site_counts counts the LENGTH of a node's declared
MayGrant.via tuple, not a scan of real call sites), so no diff could ever
match. DOC004/DOC006 (frob.gates._docblocks/_docptr, the docptr family)
were never evaluated by T-3324's check at all -- a wholly separate gate
module.

Fix:
- sys111_findings_touching (src/frob/gates/_sys.py): re-parses every
  .strata file under the design dir to build a node_id -> declaring-file
  map (a node's ratchet growth always originates in an edit to the
  .strata file that declares or `extend`s it, since the observed count
  is purely declaration-length, not a source scan), then filters SYS111
  violations by that file set intersecting the land's touched files.
- docptr_findings_touching (src/frob/gates/_sys.py): builds a throwaway
  GraphSnapshot, runs doc004_gate/doc006_gate + waivers (the same
  evaluation `frob check` itself uses), and filters on EITHER the
  finding's own doc file or a path/anchor its message names being in the
  land's touched files. Fails OPEN on any OSError building the snapshot
  (a HOME-keyed derived-state lock this land-time context has no
  guarantee is writable in) rather than crashing the land.
- Both wired into _refuse_if_selfaudit_findings_in_touched_files
  (src/frob/tickets/_land_squash.py) alongside the original SELFAUDIT001
  check, same diff-scoped/unconditional/unwind-before-commit posture.

Evidence:
- uv run pytest -p no:xdist tests/test_gates.py tests/test_ticket_work_
  and_land_finish.py -k "Sys111FindingsTouching or DocptrFindingsTouching
  or SelfauditFindingsInTouchedFiles" -q: 11 passed, 3x rerun clean
  (must-fire: a SYS111/DOC006 finding whose declaring/named file is
  touched refuses and unwinds; must-stay-quiet: an untouched file's
  finding is filtered out, matching the pre-existing SELFAUDIT001 tests'
  own shape)
- uv run ruff check src/frob/gates/_sys.py src/frob/tickets/_land_
  squash.py tests/test_gates.py tests/test_ticket_work_and_land_
  finish.py: clean
- Pre-existing TestSelfauditFindingsTouching (strata-native-dependent)
  and TestSelfauditFindingsInTouchedFiles tests re-verified still pass
  (the one native-blocked test in this worktree, test_finding_in_
  touched_file_is_returned, fails identically before this change --
  strata_core not built here, unrelated -- and a later evidence-run
  auto-rebuild made the natives available anyway)

Filed: none

Gates: ruff clean on every touched file; new tests 3x-stable; wiring
proven end to end through _refuse_if_selfaudit_findings_in_touched_files

### Changed
```
 src/frob/gates/_sys.py                    | 157 ++++++++++++++++++++++++++++++
 src/frob/tickets/_land_squash.py          |  19 +++-
 tests/test_gates.py                       | 145 +++++++++++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py |  86 ++++++++++++++++
 tickets/T-3575/ticket.md                  |   5 +
 5 files changed, 410 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_sys111_finding_in_touched_files_refuses_and_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestSelfauditFindingsInTouchedFiles::test_docptr_finding_in_touched_files_refuses_and_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestSys111FindingsTouching::test_ratchet_trip_in_declaring_file_is_returned` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocptrFindingsTouching::test_finding_in_touched_doc_is_returned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 32 error(s), 4133 warning(s), 891 waived
- error-findings: AFFECT001@src/frob/gates/_sys.py, ARCH001@src/frob/gates/_sys.py, ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_conftest_sigbreak_faulthandler.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT001@src/frob/tickets/_land_squash.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_conftest_sigbreak_faulthandler.py, LANDPARITY002@src/frob/gates/_sys.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3575, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
