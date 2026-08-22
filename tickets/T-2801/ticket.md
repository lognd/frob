---
id: T-2801
title: 'post-land sweep regression from T-2794, T-2686, T-2795, T-2675, T-2790: 18
  new (rule, file) identit(ies), 37 finding(s) (COV001, CYCLE001, DOC001, DOC006)'
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/audits/test005-zero-classification-t1418.md
- docs/design/registry/check-coverage.yaml
- docs/investigations/T-2790-check-stage-profile.md
- docs/modules/tickets-data-storage.md
- src/frob/__init__.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/check/__init__.py
- src/frob/graph/callgraph.py
- src/frob/lang/_support.py
- src/frob/strata/_multifile.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_evidence.py
- tests/test_release.py
- tickets.md
- src/frob/process/parsers/ruff.py
findings:
- - COV001
  - src/frob/graph/callgraph.py
- - CYCLE001
  - src/frob/__init__.py
- - DOC001
  - docs/investigations/T-2790-check-stage-profile.md
- - DOC006
  - docs/audits/test005-zero-classification-t1418.md
- - DRIFT001
  - src/frob/app/ticket_runner/_verify.py
- - DRIFT001
  - src/frob/tickets/__init__.py
- - DRIFT002
  - docs/modules/tickets-data-storage.md
- - LANG004
  - src/frob/lang/_support.py
- - PERF004
  - src/frob/tickets/_evidence.py
- - REG002
  - docs/design/registry/check-coverage.yaml
- - SEC110
  - src/frob/app/ticket_runner/_verify.py
- - SEC110
  - src/frob/app/verify_runner.py
- - SEC110
  - tests/test_release.py
- - SYS003
  - src/frob/check/__init__.py
- - TEST001
  - src/frob/strata/_multifile.py
- - TICK002
  - tickets.md
- - TICK003
  - tickets.md
- - TICK004
  - tickets.md
evidence_scope:
- tests/unit/strata/test_fragments.py
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: land's own Tier-A REG010 auto-fix added a CHK-GATE-I001 registry entry as
    a side effect of this ticket's DOC013 fix, which then failed REG008 (no frob:enforces
    edge existed for the pre-existing live I001 rule); added the missing edge at its
    real enforcement site rather than reverting the auto-fix
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: 'BUG002 escape hatch: this ticket''s fixes are doc/registry/design-declaration
    corrections with no reproducible runtime behavior change'
  actor: logan
  at: '2026-08-22'
  old_length: 4758
  new_length: 5495
evidence:
- tests/test_release.py::TestPublish::test_env_only_loaded_on_a_real_run
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f60eb5404c7480775e98401b1aaf54ad074ef219
---
The deferred post-land unscoped sweep (T-1684) for T-2794, T-2686, T-2795, T-2675, T-2790 at commit d8610bf1765e4ea739b77eee4248708f912b5dbb found 18 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (18), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 37 actual finding(s) across those 18 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/graph/callgraph.py
- CYCLE001  src/frob/__init__.py
- DOC001  docs/investigations/T-2790-check-stage-profile.md
- DOC006  docs/audits/test005-zero-classification-t1418.md
- DRIFT001  src/frob/app/ticket_runner/_verify.py
- DRIFT001  src/frob/tickets/__init__.py
- DRIFT002  docs/modules/tickets-data-storage.md
- LANG004  src/frob/lang/_support.py
- PERF004  src/frob/tickets/_evidence.py
- REG002  docs/design/registry/check-coverage.yaml
- SEC110  src/frob/app/ticket_runner/_verify.py
- SEC110  src/frob/app/verify_runner.py
- SEC110  tests/test_release.py
- SYS003  src/frob/check/__init__.py
- TEST001  src/frob/strata/_multifile.py
- TICK002  tickets.md
- TICK003  tickets.md
- TICK004  tickets.md

T-2009: 5 lands (T-2794, T-2686, T-2795, T-2675, T-2790) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2794, T-2686, T-2795, T-2675, T-2790 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/graph/callgraph.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- CYCLE001  src/frob/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/investigations/T-2790-check-stage-profile.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  docs/audits/test005-zero-classification-t1418.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/tickets/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT002  docs/modules/tickets-data-storage.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG004  src/frob/lang/_support.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/tickets/_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REG002  docs/design/registry/check-coverage.yaml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SYS003  src/frob/check/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

<!-- frob:waive BUG002 reason="This ticket's 14 fixed identities are all doc-anchor/registry-entry/design-flow-declaration corrections and gate waivers (frob:doc/frob:tests edges added, a stale anchor repointed, a missing DOC013 registry entry added, two undeclared-import design flows declared, PERF004/SEC110 waivers, two DRIFT001 acks) -- none of them change runtime behavior a pytest node id could genuinely fail-then-pass across. No confirmatory-only test was intentionally offered as a real repro; the bound evidence (test_env_only_loaded_on_a_real_run, the three SealedGrantSet tests, the CLI-dispatch integration test) demonstrates the touched code paths still work, not that a behavioral defect was reproduced and fixed." -->