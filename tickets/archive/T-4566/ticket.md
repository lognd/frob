---
id: T-4566
title: 'post-land sweep regression from T-4550: 24 new (rule, file) identit(ies) (COV001,
  COV002, COV005, DOC005)'
state: dropped
kind: bug
origin: agent
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .frob-release.json
- .git/frob-leases/T-3259.json
- .git/frob-leases/T-4554.json
- .git/frob-leases/T-4556.json
- .git/frob-leases/T-4562.json
- README.md
- docs/commands/
- src/frob/_cli_parsers/_root.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_models.py
- src/frob/vet/_capability_registry/_matrix.py
- src/frob/vet/_capability_registry/_unity_api.py
- tests/test_ticket_leases.py
- tests/unit/test_cli_group_parity.py
- tests/unit/test_land_in_progress_window.py
- tests/unit/test_land_merge_conflict_drop.py
- tickets.md
findings:
- - COV001
  - src/frob/tickets/_leases.py
- - COV002
  - src/frob/_cli_parsers/_root.py
- - COV002
  - src/frob/app/ticket_runner/_verify.py
- - COV002
  - src/frob/tickets/_models.py
- - COV002
  - src/frob/vet/_capability_registry/_matrix.py
- - COV002
  - src/frob/vet/_capability_registry/_unity_api.py
- - COV002
  - tests/test_ticket_leases.py
- - COV002
  - tests/unit/test_land_in_progress_window.py
- - COV005
  - src/frob/tickets/_leases.py
- - DOC005
  - README.md
- - DOC007
  - src/frob/tickets/_leases.py
- - DOC012
  - docs/commands/
- - DRIFT002
  - src/frob/app/ticket_runner/_verify.py
- - DRIFT002
  - src/frob/tickets/_leases.py
- - PERF004
  - tests/unit/test_cli_group_parity.py
- - REL002
  - .frob-release.json
- - TICK004
  - tickets.md
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-3259.json
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4554.json
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4556.json
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4562.json
- - WIRE001
  - tests/unit/test_cli_group_parity.py
- - WIRE001
  - tests/unit/test_land_in_progress_window.py
- - WIRE002
  - tests/unit/test_land_merge_conflict_drop.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-4550 at commit 8a58eecd31d22686d4039495aa32280af468426c found 24 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV001  src/frob/tickets/_leases.py
- COV002  src/frob/_cli_parsers/_root.py
- COV002  src/frob/app/ticket_runner/_verify.py
- COV002  src/frob/tickets/_models.py
- COV002  src/frob/vet/_capability_registry/_matrix.py
- COV002  src/frob/vet/_capability_registry/_unity_api.py
- COV002  tests/test_ticket_leases.py
- COV002  tests/unit/test_land_in_progress_window.py
- COV005  src/frob/tickets/_leases.py
- DOC005  README.md
- DOC007  src/frob/tickets/_leases.py
- DOC012  docs/commands/
- DRIFT002  src/frob/app/ticket_runner/_verify.py
- DRIFT002  src/frob/tickets/_leases.py
- PERF004  tests/unit/test_cli_group_parity.py
- REL002  .frob-release.json
- TICK004  tickets.md
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3259.json
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4554.json
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4556.json
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4562.json
- WIRE001  tests/unit/test_cli_group_parity.py
- WIRE001  tests/unit/test_land_in_progress_window.py
- WIRE002  tests/unit/test_land_merge_conflict_drop.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/tickets/_leases.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['aba61c81670d3150826603052e26926d6f998314', '8a58eecd31d22686d4039495aa32280af468426c']
- COV002  src/frob/_cli_parsers/_root.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/app/ticket_runner/_verify.py  -> attributed to T-4550 (commit 8a58eecd31d2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_verify.py::_DONE_REPORT_CHECK_DEFAULT_BUDGET_S
- COV002  src/frob/tickets/_models.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['3671159aa2ae81cd8885f10aba0091b9357fb98a', '8a58eecd31d22686d4039495aa32280af468426c']
- COV002  src/frob/vet/_capability_registry/_matrix.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/vet/_capability_registry/_unity_api.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/test_ticket_leases.py  -> attributed to T-3612 (commit aba61c81670d, already closed/dropped -- filed below) via tests/test_ticket_leases.py::TestCommitTicketLedgerChange
- COV002  tests/unit/test_land_in_progress_window.py  -> attributed to T-3612 (commit aba61c81670d, already closed/dropped -- filed below) via tests/unit/test_land_in_progress_window.py::TestLandInProgressWindowNarrowedToSplice
- COV005  src/frob/tickets/_leases.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['aba61c81670d3150826603052e26926d6f998314', '8a58eecd31d22686d4039495aa32280af468426c']
- DOC005  README.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC007  src/frob/tickets/_leases.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['aba61c81670d3150826603052e26926d6f998314', '8a58eecd31d22686d4039495aa32280af468426c']
- DOC012  docs/commands/  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  src/frob/app/ticket_runner/_verify.py  -> attributed to T-4550 (commit 8a58eecd31d2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_verify.py::_DONE_REPORT_CHECK_DEFAULT_BUDGET_S
- DRIFT002  src/frob/tickets/_leases.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['aba61c81670d3150826603052e26926d6f998314', '8a58eecd31d22686d4039495aa32280af468426c']
- PERF004  tests/unit/test_cli_group_parity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REL002  .frob-release.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3259.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4554.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4556.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4562.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  tests/unit/test_cli_group_parity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  tests/unit/test_land_in_progress_window.py  -> attributed to T-3612 (commit aba61c81670d, already closed/dropped -- filed below) via tests/unit/test_land_in_progress_window.py::TestLandInProgressWindowNarrowedToSplice
- WIRE002  tests/unit/test_land_merge_conflict_drop.py  -> attributed to T-4552 (commit 52166b6bd7d0, already closed/dropped -- filed below) via tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-09-19: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (COV001 src/frob/tickets/_leases.py, COV002 src/frob/_cli_parsers/_root.py, COV002 src/frob/app/ticket_runner/_verify.py, COV002 src/frob/tickets/_models.py, COV002 src/frob/vet/_capability_registry/_matrix.py, COV002 src/frob/vet/_capability_registry/_unity_api.py, COV002 tests/test_ticket_leases.py, COV002 tests/unit/test_land_in_progress_window.py, COV005 src/frob/tickets/_leases.py, DOC005 README.md, DOC007 src/frob/tickets/_leases.py, DOC012 docs/commands, DRIFT002 src/frob/app/ticket_runner/_verify.py, DRIFT002 src/frob/tickets/_leases.py, PERF004 tests/unit/test_cli_group_parity.py, REL002 .frob-release.json, TICK004 tickets.md, WIRE001 tests/unit/test_cli_group_parity.py, WIRE001 tests/unit/test_land_in_progress_window.py, WIRE002 tests/unit/test_land_merge_conflict_drop.py) is absent from a direct re-check of exactly the 824 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
