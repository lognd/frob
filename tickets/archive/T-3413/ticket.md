---
id: T-3413
title: 'post-land sweep regression from T-3350: 9 new (rule, file) identit(ies), 10
  finding(s) (DOC006, OPAQUE001, SYS003, TEST001)'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/lang/__init__.py
- src/frob/lang/_extract.py
- src/frob/nodeid.py
- src/frob/tickets/_scope_coverage.py
- tests/unit/test_nodeid.py
- design/frob.strata
- tests/unit/test_extract_import_edges.py
findings:
- - DOC006
  - tickets/T-3410/ticket.md
- - DOC006
  - tickets/T-3411/ticket.md
- - OPAQUE001
  - src/frob/_cli_parsers/_ticket/_metadata.py
- - SYS003
  - src/frob/gates/__init__.py
- - SYS003
  - src/frob/tickets/_scope_coverage.py
- - SYS003
  - tests/unit/test_nodeid.py
- - TEST001
  - src/frob/lang/__init__.py
- - TEST001
  - src/frob/lang/_extract.py
- - WIRE002
  - src/frob/nodeid.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'narrowing to the T-3350-attributable subset: OPAQUE001 on _metadata.py
    is already attributed to T-3404 (unrelated, already closed/dropped); the two DOC006
    on tickets/T-3410 and T-3411 ticket docs are UNATTRIBUTED and unrelated to the
    nodeid design-model gap this ticket fixes -- adding design/frob.strata (the design-model
    fix itself) and the new unit-test file'
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tickets/T-3410/ticket.md
  reason: 'narrowing to the T-3350-attributable subset: OPAQUE001 on _metadata.py
    is already attributed to T-3404 (unrelated, already closed/dropped); the two DOC006
    on tickets/T-3410 and T-3411 ticket docs are UNATTRIBUTED and unrelated to the
    nodeid design-model gap this ticket fixes -- adding design/frob.strata (the design-model
    fix itself) and the new unit-test file'
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tickets/T-3411/ticket.md
  reason: 'narrowing to the T-3350-attributable subset: OPAQUE001 on _metadata.py
    is already attributed to T-3404 (unrelated, already closed/dropped); the two DOC006
    on tickets/T-3410 and T-3411 ticket docs are UNATTRIBUTED and unrelated to the
    nodeid design-model gap this ticket fixes -- adding design/frob.strata (the design-model
    fix itself) and the new unit-test file'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: design/frob.strata
  reason: 'narrowing to the T-3350-attributable subset: OPAQUE001 on _metadata.py
    is already attributed to T-3404 (unrelated, already closed/dropped); the two DOC006
    on tickets/T-3410 and T-3411 ticket docs are UNATTRIBUTED and unrelated to the
    nodeid design-model gap this ticket fixes -- adding design/frob.strata (the design-model
    fix itself) and the new unit-test file'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_extract_import_edges.py
  reason: 'narrowing to the T-3350-attributable subset: OPAQUE001 on _metadata.py
    is already attributed to T-3404 (unrelated, already closed/dropped); the two DOC006
    on tickets/T-3410 and T-3411 ticket docs are UNATTRIBUTED and unrelated to the
    nodeid design-model gap this ticket fixes -- adding design/frob.strata (the design-model
    fix itself) and the new unit-test file'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_extract_import_edges.py::test_module_level_import_is_import_time
- tests/unit/test_extract_import_edges.py::test_function_local_import_is_deferred
- tests/unit/test_extract_import_edges.py::test_class_body_import_is_deferred
- tests/unit/test_extract_import_edges.py::test_type_checking_import_is_deferred
- tests/unit/test_extract_import_edges.py::test_dotted_type_checking_import_is_deferred
- tests/unit/test_extract_import_edges.py::test_try_except_import_error_is_import_time
- tests/unit/test_extract_import_edges.py::test_sys_version_info_guarded_import_is_import_time
- tests/unit/test_extract_import_edges.py::test_mixed_module_and_deferred_import_of_the_same_name
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a26ea5ce8aa2d888587d201df5684766b547b6ce
---
The deferred post-land unscoped sweep (T-1684) for T-3350 at commit a07433b7215188fd5acd6985054978ec304c6eb6 found 9 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (9), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 10 actual finding(s) across those 9 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3410/ticket.md
- DOC006  tickets/T-3411/ticket.md
- OPAQUE001  src/frob/_cli_parsers/_ticket/_metadata.py
- SYS003  src/frob/gates/__init__.py
- SYS003  src/frob/tickets/_scope_coverage.py
- SYS003  tests/unit/test_nodeid.py
- TEST001  src/frob/lang/__init__.py
- TEST001  src/frob/lang/_extract.py
- WIRE002  src/frob/nodeid.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3410/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-3411/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  src/frob/_cli_parsers/_ticket/_metadata.py  -> attributed to T-3404 (commit 7313e4af458f, already closed/dropped -- filed below) via src/frob/_cli_parsers/_ticket/_metadata.py::_RefuseRepeatedOption
- SYS003  src/frob/gates/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SYS003  src/frob/tickets/_scope_coverage.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SYS003  tests/unit/test_nodeid.py  -> attributed to T-3350 (commit a07433b72151, already closed/dropped -- filed below) via tests/unit/test_nodeid.py::test_bracketed_case_suffix_dots_pass_through_unchanged
- TEST001  src/frob/lang/__init__.py  -> attributed to T-3350 (commit a07433b72151, already closed/dropped -- filed below) via src/frob/lang/__init__.py::extract_import_edges -> src/frob/lang/__init__.py::_parse -> src/frob/lang/__init__.py::_warn_unsupported_extension
- TEST001  src/frob/lang/_extract.py  -> attributed to T-3350 (commit a07433b72151, already closed/dropped -- filed below) via src/frob/lang/_extract.py::_PYTHON_DEFERRING_SCOPES
- WIRE002  src/frob/nodeid.py  -> attributed to T-3350 (commit a07433b72151, already closed/dropped -- filed below) via src/frob/nodeid.py::symref_to_nodeid

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.