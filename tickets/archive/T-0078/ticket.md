---
id: T-0078
title: 'strata code binding: code globs + import-level conformance'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0052
parent: T-0053
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/gates/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_code_binding.py::TestBindCode::test_partitions_files_by_glob_and_defaults_unmatched_to_foreign
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_cross_component_import_without_declared_flow_is_a_violation
- tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_declared_flow_in_reverse_direction_only_still_refuses_the_import
designated_repro_test: null
threat: null
component: null
---
Undeclared cross-component import = SYS violation with file:line; unclassified code is foreign by default; reflexion-model tier.
## Done report

Kernel-level code binding (surface grammar lacks a code keyword; the
ticket-sanctioned fallback): nodes declare code=<glob> attrs; bind_code
partitions .py files into node-owner buckets with unmatched files
falling to the FOREIGN sentinel (charter law 2) and 2+ matching globs
an AmbiguousCodeBinding error; check_import_conformance walks bound
files' imports via stdlib ast (absolute AND relative, level>=1
resolved against the file's package position) and flags any in-repo
import crossing differently-owned components without a declared Flow
in the EXACT direction -- Flow is directed per kernel.md, and the
first-round either-direction authorization was retracted as a
soundness hole (normative subsection in surface.md documents this,
with the reverse-only-flow-refuses test pinning it).
FOREIGN->bound imports are a disclosed v0 scope cut. Reviewer REJECTed
round 1 (direction hole + relative imports unchecked), APPROVED round
2 after semantic fixes. Verified at merge on main: 258 strata tests
green, 15/15 in test_code_binding.py.