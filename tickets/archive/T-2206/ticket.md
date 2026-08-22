---
id: T-2206
title: 'post-land sweep regression from T-2199: 17 new (rule, file) identit(ies),
  32 finding(s) (ARCH001, ARCH103, COV004, DOC011)'
state: done
kind: bug
origin: agent
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_lang.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: design
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/design/gate-semantics-classification.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: docs/guides/coordinator-scripts.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/telemetry.py
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/app/ticket_runner/_new.py
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: src/frob/lang/_nodes.py
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
  reason: narrowing to the one genuinely-new, cheaply-fixable finding (TEST010 malformed
    directive in tests/test_ticket_work_and_land_finish.py); ARCH001/ARCH103/PERF004/SELFAUDIT001
    findings are genuine but real function-level refactors, filed separately; COV004/DOC011/DRIFT001(_land_cmd.py)/TEST010(test_lang.py)
    did not reproduce on re-measure; TICK004/E501/DRIFT001(_nodes.py) already resolved
    by T-2260's land
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a39d81cc95bcc4b1b8f2ae31751c6d751eb3eda0
---
The deferred post-land unscoped sweep (T-1684) for T-2199 at commit 26ff8cdecd6444942b61ac9fa012e321c2ca78e9 found 17 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (17), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 32 actual finding(s) across those 17 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/app/telemetry.py
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py
- ARCH001  src/frob/app/ticket_runner/_new.py
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py
- COV004  tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
- COV004  tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
- COV004  tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py
- DRIFT001  src/frob/lang/_nodes.py
- E501  src/frob/lang/_nodes.py
- PERF004  src/frob/app/ticket_runner/_land_cmd.py
- SELFAUDIT001  design
- TEST010  tests/test_lang.py
- TEST010  tests/test_ticket_work_and_land_finish.py
- TICK004  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/telemetry.py  -> attributed to T-2191 (commit c30c384aeb1f, already closed/dropped -- filed below) via src/frob/app/telemetry.py::_HOME_CLAUDE_RUNTIME_STATE_DIRS
- ARCH001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f']
- ARCH001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['9050729816d9343502cdc94a00f850439d5b59da', '7f8c48060c8e8b4f884db6ac13dc24379c096e73']
- ARCH103  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f']
- COV004  tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f']
- DRIFT001  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- E501  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- PERF004  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f']
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST010  tests/test_lang.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via tests/test_lang.py::TestResolveLocalImportConsumers
- TEST010  tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['a1d37e461d4818c14af3a4a00170d60b083955ac', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429']
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.