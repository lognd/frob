---
id: T-2347
title: 'post-land sweep regression from T-2337, T-2322: 28 new (rule, file) identit(ies),
  68 finding(s) (ARCH103, COV001, COV003, DOC001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/guides/coordinator-scripts.md
- docs/modules/cli.md
- scripts/fleet_status.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/release/_cli.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_leases.py
- src/frob/verify/_drain.py
- src/frob/verify/_quarantine.py
- src/frob/verify/_worker.py
- tests/test_release.py
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
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
The deferred post-land unscoped sweep (T-1684) for T-2337, T-2322 at commit 997c750fe1184338fa871174a9c1e8038f23e372 found 28 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (28), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 68 actual finding(s) across those 28 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  scripts/fleet_status.py
- ARCH103  src/frob/release/_cli.py
- COV001  scripts/fleet_status.py
- COV001  src/frob/tickets/_land_git_ops.py
- COV001  src/frob/tickets/_leases.py
- COV001  src/frob/verify/_drain.py
- COV001  src/frob/verify/_quarantine.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- DOC001  docs/commands/release.md
- DOC002  scripts/fleet_status.py
- DOC002  src/frob/app/verify_runner.py
- DOC002  src/frob/verify/_drain.py
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- E501  src/frob/verify/_worker.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF004  src/frob/app/ticket_runner/_new.py
- RENDER001  src/frob/release/_cli.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TEST001  src/frob/tickets/_leases.py
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE003  docs/modules/cli.md

T-2009: 2 lands (T-2337, T-2322) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2337, T-2322 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/tickets/_land_git_ops.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['9b644c779b13492b0a9f25e6d09a45966a326554', '3db9fbe21299af22b451c7526b4adc04d18cfc17']
- COV001  src/frob/tickets/_leases.py  -> UNATTRIBUTED (3 batch commits' touched symbols all reach this finding); candidate commits: ['362f1d02e0f0e8f29636c82d1d39cabd3c62cd21', '9b644c779b13492b0a9f25e6d09a45966a326554', '3db9fbe21299af22b451c7526b4adc04d18cfc17']
- COV001  src/frob/verify/_drain.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/verify/_quarantine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1205  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1235  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1688  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/verify/_drain.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  src/frob/verify/_worker.py  -> attributed to T-2324 (commit 30d238be4585, already closed/dropped -- filed below) via src/frob/verify/_worker.py::WorkerOutcome
- PERF003  src/frob/gates/_debt_deprecated.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/app/ticket_runner/_new.py  -> attributed to T-2322 (commit 3db9fbe21299, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_new.py::_scope_plausibility_file_words -> src/frob/app/ticket_runner/_new.py::_split_scope_plausibility_words -> src/frob/app/ticket_runner/_new.py::_SCOPE_PLAUSIBILITY_MIN_WORD_LEN
- RENDER001  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/tickets/_leases.py  -> UNATTRIBUTED (3 batch commits' touched symbols all reach this finding); candidate commits: ['362f1d02e0f0e8f29636c82d1d39cabd3c62cd21', '9b644c779b13492b0a9f25e6d09a45966a326554', '3db9fbe21299af22b451c7526b4adc04d18cfc17']
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-17: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (ARCH103 scripts/fleet_status.py, ARCH103 src/frob/release/_cli.py, COV001 scripts/fleet_status.py, COV001 src/frob/tickets/_land_git_ops.py, COV001 src/frob/tickets/_leases.py, COV001 src/frob/verify/_drain.py, COV001 src/frob/verify/_quarantine.py, COV003 tickets/T-1205, COV003 tickets/T-1235, COV003 tickets/T-1397, COV003 tickets/T-1526, COV003 tickets/T-1688, DOC001 docs/commands/release.md, DOC002 scripts/fleet_status.py, DOC002 src/frob/app/verify_runner.py, DOC002 src/frob/verify/_drain.py, DOC011 docs/design/gate-semantics-classification.md, DOC011 docs/guides/coordinator-scripts.md, E501 src/frob/verify/_worker.py, PERF003 src/frob/gates/_debt_deprecated.py, PERF004 src/frob/app/ticket_runner/_new.py, RENDER001 src/frob/release/_cli.py, SEC110 tests/test_release.py, SELFAUDIT001 design, TEST001 src/frob/tickets/_leases.py, TICK003 tickets.md, TICK004 tickets.md, WIRE003 docs/modules/cli.md) is absent from the fresh unscoped measurement at T-2313's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
