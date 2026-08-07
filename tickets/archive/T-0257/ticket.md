---
id: T-0257
title: 'frob deploy generate: install/status/uninstall scripts compiled from HostManifest,
  drift-locked'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0255
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- src/frob/app/**
- src/frob/__main__.py
- src/frob/strata/**
- docs/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/deploy/test_generate.py::TestSorted::test_sorted
- tests/unit/deploy/test_generate.py::TestDigest::test_det
- tests/unit/deploy/test_generate.py::TestDigest::test_changes_with_model
- tests/unit/deploy/test_generate.py::TestInstall::test_idempotent
- tests/unit/deploy/test_generate.py::TestInstall::test_empty_model
- tests/unit/deploy/test_generate.py::TestStatus::test_one_line
- tests/unit/deploy/test_generate.py::TestUninstall::test_removes
- tests/unit/deploy/test_generate.py::TestAll::test_returns_all
- tests/unit/deploy/test_drift.py::TestDrift::test_no_dir
- tests/unit/deploy/test_drift.py::TestDrift::test_clean
- tests/unit/deploy/test_drift.py::TestDrift::test_stale
- tests/unit/strata/test_export.py::TestNodeSyscalls::test_base
- tests/unit/strata/test_effects.py::TestNodeMayKinds::test_kinds
- tests/unit/strata/test_effects.py::TestNodeMayKinds::test_no_may_atoms_is_empty
- tests/integration/test_interfaces.py::TestInterfaces::test_deploy_generate_writes_and_checks
designated_repro_test: null
threat: null
component: null
---
T-0254 child 3. frob deploy generate compiles deploy/install.sh, deploy/status.sh, deploy/uninstall.sh from the HostManifest. INSTALL: idempotent by construction -- every step is check-then-apply (user exists? unit enrolled? file hash matches?), re-run = zero changes, exit codes honest; creates service users per T-0255 spec, writes units with the hardening block, sets exact ownership/modes from owns entries. STATUS: per-unit active/health from the model (listens ports probed, declared health endpoints checked), machine-readable + human summaries. UNINSTALL: removes EXACTLY the manifest set (units stopped+disabled+deleted, users removed, owned paths deleted, nothing else touched) -- artifact-freeness is manifest completeness, which the VM audit (child 5) proves empirically. Generated scripts carry a header manifest digest; a DEPLOY001 drift gate (default-on when deploy/ exists) fails check if committed scripts do not match regeneration from the current model -- the tmLanguage drift-lock pattern. Shellcheck-clean bash, no external deps beyond coreutils/systemctl.