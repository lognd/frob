---
id: T-2844
title: Split _host_isolation.py along lateral/vertical/movement seams (blocked on
  via-scope migration review)
state: in-progress
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_host_isolation.py
- design/frob.strata
- tests/unit/strata/test_host_isolation.py
- src/frob/strata/_host_isolation_shared.py
- src/frob/strata/_host_isolation_lateral.py
- src/frob/strata/_host_isolation_vertical.py
- src/frob/strata/_host_isolation_movement.py
- docs/strata/host.md
evidence_scope:
- tests/unit/strata/test_litmus_host_isolation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_host_isolation.py
  reason: T-2844's split moves symbols out of _host_isolation.py into new sibling
    files; the frob:tests directives in test_host_isolation.py are anchored to the
    OLD file path per-symbol and must be updated to the new definition file to avoid
    orphaning coverage evidence (T-2729 selfconform precedent did the same). New sibling
    files hold the moved code itself.
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/strata/_host_isolation_shared.py
  reason: T-2844's split moves symbols out of _host_isolation.py into new sibling
    files; the frob:tests directives in test_host_isolation.py are anchored to the
    OLD file path per-symbol and must be updated to the new definition file to avoid
    orphaning coverage evidence (T-2729 selfconform precedent did the same). New sibling
    files hold the moved code itself.
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/strata/_host_isolation_lateral.py
  reason: T-2844's split moves symbols out of _host_isolation.py into new sibling
    files; the frob:tests directives in test_host_isolation.py are anchored to the
    OLD file path per-symbol and must be updated to the new definition file to avoid
    orphaning coverage evidence (T-2729 selfconform precedent did the same). New sibling
    files hold the moved code itself.
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/strata/_host_isolation_vertical.py
  reason: T-2844's split moves symbols out of _host_isolation.py into new sibling
    files; the frob:tests directives in test_host_isolation.py are anchored to the
    OLD file path per-symbol and must be updated to the new definition file to avoid
    orphaning coverage evidence (T-2729 selfconform precedent did the same). New sibling
    files hold the moved code itself.
  actor: logan
  at: '2026-08-22'
- op: add
  glob: src/frob/strata/_host_isolation_movement.py
  reason: T-2844's split moves symbols out of _host_isolation.py into new sibling
    files; the frob:tests directives in test_host_isolation.py are anchored to the
    OLD file path per-symbol and must be updated to the new definition file to avoid
    orphaning coverage evidence (T-2729 selfconform precedent did the same). New sibling
    files hold the moved code itself.
  actor: logan
  at: '2026-08-22'
- op: add
  glob: docs/strata/host.md
  reason: 'DOC006: docs/strata/host.md:438 points at _host_isolation.py::host_movement_flows,
    which T-2844 moved to _host_isolation_movement.py -- the doc pointer must follow
    the symbol to its new file, same as the frob:tests directive updates.'
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: 'BUG002 refused the land: kind=bug ticket''s evidence is confirmatory-only
    because this ticket is actually a refactor with no intended behavior change, not
    a defect fix -- the remedy documented in BUG002 own error message'
  actor: logan
  at: '2026-08-22'
  old_length: 1245
  new_length: 1782
evidence:
- tests/unit/strata/test_host_isolation.py::TestLateralIsolation::test_skips_below_two_users
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
- tests/unit/strata/test_host_isolation.py::TestHostIsolationWaivers::test_vuln_model_fires_unwaived
- tests/unit/strata/test_litmus_host_isolation.py::TestHostIsolationVulnLitmus::test_shared_user_model_fires_host001_and_host002
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2826 (LARGE001 strata batch). src/frob/strata/_host_isolation.py (1285 lines) has a genuine structural seam T-2826 did NOT act on: three independent top-level checks (evaluate_lateral_isolation, evaluate_vertical_isolation, host_movement_flows) each with their own violation-computation helper cluster, sharing only the HostIsolationViolation model and a few small utilities (_mode_digits/_mode_owner_writable/_mode_has_setuid). Unlike this batch's other 9 files, this genuinely looks splittable along those three functions. NOT done under T-2826 because: this module carries via-scoped capability grants in design/frob.strata (per this repo's own recent incident where an innocuous import change nearly broke a noflow assertion, and T-2729's own split of _selfconform.py needed a via-list update when code moved between files) -- moving functions between files may require updating which file a via-glob covers, and that needs a dedicated, careful pass (read the current via-declarations, confirm what moves, re-verify SYS003/SYS100 exhaustively) rather than a batch LARGE001 judgment call. Scope includes design/frob.strata so whoever picks this up can update via-declarations in the same change if the split requires it.

frob:no-behavior-change reason="T-2844 is a pure LARGE001 file-split refactor: every function/class moved verbatim (same name, same body/signature) into a new sibling module with a facade re-export -- no logic changed. The bound evidence passes at both main and this commit because there is no defect to reproduce; this is not a bug fix, it is a structural move. Verified by direct test-suite comparison (226 tests, identical pass set before and after) and by frob.gates._arch measurement showing zero net behavior-affecting findings."