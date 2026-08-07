---
id: T-0261
title: 'std.host windows backend: services, gMSA/service accounts, ACLs, named pipes,
  firewall ports'
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
- strata-core/src/parse.rs
- src/frob/strata/**
- src/frob/deploy/**
- editors/**
- docs/strata/**
- tickets.md
- tests/unit/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/unit/strata/
  reason: T-0261 strata work maps to tests/unit/strata/
  actor: logan
  at: '2026-07-20'
evidence:
- tests/unit/strata/test_host.py::TestHostAttrs::test_desugars_windows_fields
- tests/unit/strata/test_host.py::TestHostManifestWindows::test_reads_windows_fields
- tests/unit/strata/test_host.py::TestHostManifestWindows::test_no_platform_attr_defaults_to_linux_systemd
- tests/unit/strata/test_host.py::TestHostManifestWindows::test_unknown_platform_value_raises
- tests/unit/strata/test_host.py::TestHostAclRuleValidation::test_valid_rule_accepted
- tests/unit/strata/test_host.py::TestHostAclRuleValidation::test_deny_and_no_inherit_flags_accepted
- tests/unit/strata/test_host.py::TestHostAclRuleValidation::test_missing_rights_rejected
- tests/unit/strata/test_host.py::TestHostAclRuleValidation::test_unknown_flag_rejected
- tests/unit/strata/test_host.py::TestHostAclRuleValidation::test_no_colon_rejected
- tests/unit/strata/test_litmus_host.py::TestHostWindowsDeclaredLitmus::test_declared_manifest_round_trips_every_windows_field
designated_repro_test: null
threat: null
component: null
---
T-0254 Windows pillar. Generalize the HostManifest (T-0255, Linux/systemd-first) into a platform-tagged model so a node can target windows. Windows analogs: service account instead of runs_as (dedicated low-priv local account, or a group Managed Service Account gMSA for domain-joined hosts -- NO interactive-logon right, deny-network-logon where possible, SeDenyBatchLogonRight per hardening); Windows Service (SCM) instead of systemd unit, with the hardening equivalents (service SID type restricted, required-privileges allowlist derived from may-capabilities, protected-process where applicable); NTFS ACLs (owner + explicit DACL entries) instead of POSIX owns MODE -- model must express deny-inheritance and per-principal rights, richer than a 3-octal mode; named pipes + Windows firewall rules for the listens surface. The platform tag drives which fields are required (a windows node without an ACL model is a HOST-family gap, mirroring a linux node without owns). Keep ONE HostManifest with a platform discriminator, not two parallel models -- the movement proofs (T-0256) and conformance (T-0258) must consume both uniformly. Grammar in parse.rs, tmLanguage drift-lock, litmus pair (linux + windows), docs/strata/host.md gains a Windows section. Generator/audit are separate tickets -- manifest + model only here.