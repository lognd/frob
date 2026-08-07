---
id: T-0255
title: 'std.host: OS-layer modeling -- service users, units, ownership, ports as first-class
  strata'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: T-0254
tier: ticket
sprint: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- editors/**
- docs/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host.py::TestHostAttrs::test_desugars
- tests/unit/strata/test_host.py::TestHostAttrs::test_no_clauses_desugars_to_empty
- tests/unit/strata/test_host.py::TestHostManifest::test_reads
- tests/unit/strata/test_host.py::TestHostManifest::test_node_with_no_host_attrs_returns_none
- tests/unit/strata/test_litmus_host.py::TestHostDeclaredLitmus::test_declared_manifest_round_trips_every_field
- tests/unit/strata/test_litmus_host.py::TestHostUndeclaredLitmus::test_undeclared_node_has_no_manifest
designated_repro_test: null
threat: null
component: null
---
T-0254 child 1 (foundation). New std.host vocabulary: a node/store gains `runs_as "svc-name"` (dedicated service user; the deploy generator creates it system-scoped, no login shell, no home unless declared), `unit` binding (systemd service with hardening directives derived from the model: NoNewPrivileges, ProtectSystem=strict, PrivateTmp, CapabilityBoundingSet from may-capabilities, plus the EXISTING seccomp exporter wired in as SystemCallFilter), `owns <path> <mode>` for files/dirs with explicit modes/ownership, `listens <port>` for sockets. OS users join the trust lattice so flows between service users are model-checked like any flow. Grammar in parse.rs (mirror managed/waive precedent, tmLanguage drift-lock will fire), elaborate to node attrs + a HostManifest model (the single source the generator, conformance checker, and VM auditor all consume -- one manifest, no duplication). Litmus pair + docs/strata/host.md. Do NOT build the generator here -- manifest only.