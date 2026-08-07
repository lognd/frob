---
id: T-0270
title: 'std.host manifest: validate owns MODE and listens PORT (deferred from T-0255)'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: T-0254
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/_host.py
- src/frob/strata/**
- tests/**
- docs/strata/host.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host.py::TestHostOwnsModeValidation::test_non_octal_mode_rejected
- tests/unit/strata/test_host.py::TestHostManifestListensValidation::test_out_of_range_port_rejected
designated_repro_test: null
threat: null
component: null
---
T-0255 deliberately left HostOwns.mode (str) and HostManifest.listens (int) UNVALIDATED -- a bogus mode ('999'/'rwx') or out-of-range port is stored raw. T-0255's reviewer confirmed this is a correct deferral (mode-as-opaque-string is intentional so a Windows ACL/SDDL string fits the same field later -- platform-tagged validation belongs here, not in the manifest schema). Implement per-platform validation: LINUX_SYSTEMD validates octal mode (0-7 triples, optional setuid bits) and port in 1-65535; WINDOWS (when T-0261 lands) validates SDDL/ACL shape. Validation fires at elaborate time (MalformedHost error, fail-closed), NOT parse time (keep the grammar platform-agnostic). Litmus: bogus mode/port rejected per platform, valid ones pass. T-0255 added frob:todo T-0270 anchors at the two fields -- this ticket discharges them.