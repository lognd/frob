---
id: T-0941
title: 'docs/modules/deploy.md: update windows binPath/ImagePath scope-cut prose now
  that T-0629 shipped the vocabulary'
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/deploy.md
- tests/unit/deploy/test_generate_windows.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/deploy/test_generate_windows.py
  reason: 'evidence: existing test coverage for the bin_path/sc.exe create behavior
    the doc update describes'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_without_args
designated_repro_test: null
threat: null
component: null
---
T-0629 added `std.host`'s `bin_path`/`bin_path_args` (SCM binPath/ImagePath)
vocabulary and wired `generate_windows_install_script` to `sc.exe create`
idempotently when `bin_path` is declared, closing the honest gap
`docs/modules/deploy.md#scope-and-honesty-notes-generate-windows` documents.
That doc file is NOT in T-0629's scope (scope=['strata-core/src/parse.rs',
'src/frob/strata/_host.py', 'src/frob/deploy/_generate_windows.py',
'tests/unit/strata/', 'tests/unit/deploy/']), so its prose is now stale:

- "`std.host` has no windows binPath/ImagePath vocabulary yet ... `install.ps1`
  cannot itself `sc.exe create` a working service" is no longer true when
  `bin_path` is declared.
- The windows-generation bullet list ("`service`-marked nodes get their SCM
  service hardened ... IF the service already exists") needs the same
  IDEMPOTENTLY-CREATED-WHEN-`bin_path`-DECLARED update
  `src/frob/deploy/_generate_windows.py`'s own module docstring now carries.

Update docs/modules/deploy.md's windows-generation bullet list and its
"Scope and honesty notes" section to describe the new `bin_path` clause and
drop it from the "not yet built" scope-cut list (the three remaining v0 scope
cuts -- required privileges, deny-logon rights, RBCD delegation -- are
unaffected and should stay).