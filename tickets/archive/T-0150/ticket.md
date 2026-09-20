---
id: T-0150
title: 'self-conformance: vet capability scan of our own source must match design/frob.strata
  interfaces'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/app/__main__.py
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- frob.toml
- tickets.md
- tests/golden/frob_export_seccomp.json
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense benign-capability vocabulary rationale into T-0150 body
  actor: logan
  at: '2026-09-19'
  old_length: 1762
  new_length: 3856
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_fires
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_discharges_once_observed
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_discharges_once_mapped
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob vet already introspects dependencies for capability use (scan_directory_capabilities in src/frob/vet/_capability.py: exec/eval/network/fs/... per-language token scan). Point that same machinery at OUR OWN src/ tree and reconcile against the self-hosted strata design, so the interfaces recorded in design/frob.strata are provably in sync with what the code actually does. Reuse scan_directory_capabilities READ-ONLY (import it; do not modify src/frob/vet -- T-0147 is concurrently editing that package). Mechanism: a node-to-source-path mapping (investigate whether the kernel/surface already supports binding a node to a code path; if not, add the smallest principled mapping -- e.g. a [tool.frob]/frob.toml table or a strata clause -- and document the decision). Conformance rules, all loud (vacuous-pass doctrine): (1) capability observed in a mapped path but not declared on the mapped node = violation (undeclared interface); (2) capability declared on a node with zero observed sites in its mapped paths = violation (stale design); (3) source directories under src/ with no node mapping = violation (unmodeled code), no silent exemption; test paths excluded per _is_test_path precedent. Surface as a new SYS-family gate rule id wired into frob sys audit (follow the THREAT/SYS rule registration precedent) and run against design/frob.strata in our own gates. Expect the first honest run to FAIL until design/frob.strata is updated to declare reality -- updating the design to match observed capabilities (or waiving with written reasons) is part of this ticket. Tests: fixture design+source trees for each rule firing and discharging; drift-lock so an unmapped capability kind in the scanner vocabulary fails loudly rather than being silently ignored.

<!-- narrative-moved:src/frob/strata/_threat_catalog_benign.py:13:T-0150 -->
: T-0150: `may` capability kinds `_selfconform.py`'s SYS100/SYS101 measure
: via `frob.vet._capability`'s scanner vocabulary (net/fs-write-derived
: "fs"/eval/env/ffi/install-hook) that name NO `CWE_CATALOG`/
: `QUALITY_CATALOG` `capability_kind` at all (the catalog's kinds --
: html_render/sql/exec/fetch_url/deserialize/client_storage -- are a
: DIFFERENT, CWE-sink-shaped vocabulary, docs/strata/threat.md#the-
: catalog-stdcwe). Declaring these on `design/frob.strata`'s nodes (so
: SYS100/SYS101 can reconcile them) would otherwise fail THREAT002 on
: every one of them ("matches no sink taxonomy entry") with NO way to
: excuse it, since `BenignCapability` is a Python-side argument neither
: `evaluate_exhaustiveness` (`_audit.py`) nor `audit_claim` (`_sysdoc.py`,
: DOC003's model-side half) wired to a default until now. `exec` IS
: listed below too, despite having a real `CWE_CATALOG` entry (CWE-78) --
: `_evaluate_family` (`_audit.py`) passes the SAME `benign` tuple to BOTH
: the security (`CWE_CATALOG`) and quality (`QUALITY_CATALOG`) family
: loops, and `QUALITY_CATALOG` has no `exec`-mapped entry at all;
: `check_capability_completeness`'s `known` set is catalog-derived, so
: `exec` already being `known` for the security loop makes this entry a
: no-op there (`excused` is consulted only for kinds NOT already known) --
: it only takes effect for the quality loop, where it is a genuine gap in
: `QUALITY_CATALOG`'s vocabulary, not a security exemption.
frob:doc docs/strata/threat.md#the-exhaustiveness-proof-the-point
frob:waive AFFECT001 reason="T-1075 added env.read/env.write entries, same shape as \
every other entry already in this tuple; docs/strata/threat.md is outside T-1075's \
declared scope (src/frob/strata/_effects.py, src/frob/vet/_capability_modes.py, \
extended to src/frob/strata/_selfconform.py, src/frob/strata/_threat.py, \
src/frob/vet/_capability_registry.py, and their test files) -- matches T-1047's own \
precedent for the identical situation on CAPABILITY_KINDS"