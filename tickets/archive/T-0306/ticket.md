---
id: T-0306
title: SYS100 must honor fs/fs-read alias direction, not just SYS101
state: done
kind: bug
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceFsReadAlias::test_broad_fs_declaration_discharges_read_only_observation
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceFsReadAlias::test_narrow_fs_read_declaration_does_not_cover_fs_read
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceFsReadAlias::test_fs_read_only_declaration_still_fires_on_fs_write_observation
designated_repro_test: null
acceptance:
- text: declared may fs covers observed fs-read with no SYS100 finding
  evidence: []
- text: declared fs-read does not cover observed fs-write for SYS100 (asymmetry preserved)
  evidence: []
- text: regression tests added for all three cases
  evidence: []
threat: null
component: null
---
T-0304 follow-up: the fs/fs-read backward-compat alias (_alias_legacy_fs_observations) only covered SYS101's declared-vs-observed direction. SYS100 (undeclared interface) still fired for a node declaring the broader may "fs" against a real fs-read observation, since _extended_kind_violations intersected declared kinds with _EXTENDED_KINDS before comparing, and bare fs is not itself an extended kind. Live repro (read-only): lithos frob sys audit . fired SYS100 fs-read on 6 nodes (rust_core, regolith_py, stdlib_records, tooling, demos, vscode_ext) all declaring may "fs". Fix: _extended_kind_violations now unions declared with fs-read whenever the node's full declared set contains fs, one-directional only.