---
id: T-0264
title: 'frob deploy generate windows: PowerShell/DSC install/status/uninstall from
  the manifest, drift-locked'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0257
- T-0261
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- src/frob/app/**
- tickets.md
- docs/modules/deploy.md
- tests/unit/deploy/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/deploy.md
  reason: T-0264 deploy work maps to docs/modules/deploy.md
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/deploy/
  reason: T-0264 deploy work maps to tests/unit/deploy/
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/deploy/test_generate_windows.py::TestWindowsEntries::test_filters_to_windows_only
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_idempotent
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_acl_grant_and_deny_flags
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_firewall_rule_opened
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_gmsa_account_uses_ad_service_account_cmdlets
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_service_not_present_notes_missing_bin_path
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_deny_logon_scope_cut_is_documented
- tests/unit/deploy/test_generate_windows.py::TestStatus::test_one_line
- tests/unit/deploy/test_generate_windows.py::TestUninstall::test_removes
- tests/unit/deploy/test_generate_windows.py::TestUninstall::test_gmsa_uninstall_uses_ad_service_account_cmdlets
- tests/unit/deploy/test_generate_windows.py::TestKrbIntegration::test_spn_registered
- tests/unit/deploy/test_generate_windows.py::TestKrbIntegration::test_constrained_delegation_sets_flags
- tests/unit/deploy/test_generate_windows.py::TestKrbIntegration::test_unconstrained_delegation_sets_flag
- tests/unit/deploy/test_generate_windows.py::TestKrbIntegration::test_rbcd_delegation_is_documented_deferred
- tests/unit/deploy/test_generate_windows.py::TestKrbIntegration::test_no_krb_manifest_issues_no_krb_commands
- tests/unit/deploy/test_drift.py::TestDrift::test_windows_file_no_longer_produced_is_flagged
- tests/unit/deploy/test_drift.py::TestDrift::test_windows_clean
designated_repro_test: null
threat: null
component: null
---
T-0254 Windows generation. The T-0257 generator gains a windows target emitting idempotent PowerShell (check-then-apply, same contract as the bash target): install creates the service account/gMSA, registers the Windows Service with its hardening (service SID type, required-privileges, deny-logon rights), applies the NTFS ACLs exactly from the manifest, opens the declared firewall ports / creates named pipes, and configures the SPN + delegation setting from std.krb (setspn / the delegation flags) when a krb model is present. status queries SCM state + health. uninstall removes exactly the manifest set (service, account, ACL grants, firewall rules, SPN registration) leaving no artifacts. Same DEPLOY001 digest-header drift-lock as bash. Scripts must be PSScriptAnalyzer-clean and depend only on in-box modules (no PSGallery). The conformance gate (T-0258) and VM audit (T-0259) must handle the PowerShell mutation surface too -- coordinate the manifest abstraction so those tickets' parsers are platform-tagged, not bash-only; if T-0258/T-0259 landed bash-only, file follow-ups for their windows extension rather than expanding scope here.