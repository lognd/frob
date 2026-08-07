---
id: T-0960
title: 'static checks: kernel/userspace-interface classification + per-process cgroup
  resource-bound declaration obligations'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_process_bounds.py
- docs/strata/reliability.md
- src/frob/strata/__init__.py
- tests/unit/strata/test_process_bounds.py
- src/frob/gates/__init__.py
- docs/design/registry/system-design.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/__init__.py
  reason: 'Ticket scope only listed src/frob/strata/_process_bounds.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was explicitly dispatched to follow (mirroring T-0646/T-0919) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py (the same re-export

    list every sibling obligation-family module joins), and registering the

    new REL390-REL393 rule ids in src/frob/gates/__init__.py''s

    _KNOWN_GATE_RULES (so REG002/registry re-disposition can resolve

    handled_by:REL39x references). Widening to match T-0646/T-0919''s own

    declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/strata/test_process_bounds.py
  reason: 'Ticket scope only listed src/frob/strata/_process_bounds.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was explicitly dispatched to follow (mirroring T-0646/T-0919) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py (the same re-export

    list every sibling obligation-family module joins), and registering the

    new REL390-REL393 rule ids in src/frob/gates/__init__.py''s

    _KNOWN_GATE_RULES (so REG002/registry re-disposition can resolve

    handled_by:REL39x references). Widening to match T-0646/T-0919''s own

    declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Ticket scope only listed src/frob/strata/_process_bounds.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was explicitly dispatched to follow (mirroring T-0646/T-0919) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py (the same re-export

    list every sibling obligation-family module joins), and registering the

    new REL390-REL393 rule ids in src/frob/gates/__init__.py''s

    _KNOWN_GATE_RULES (so REG002/registry re-disposition can resolve

    handled_by:REL39x references). Widening to match T-0646/T-0919''s own

    declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/system-design.yaml
  reason: 'Ticket scope only listed src/frob/strata/_process_bounds.py and

    docs/strata/reliability.md, but the obligation-family pattern this ticket

    was explicitly dispatched to follow (mirroring T-0646/T-0919) requires:

    tests under tests/unit/strata/ for the new REL39x checks, wiring the new

    module''s exports into src/frob/strata/__init__.py (the same re-export

    list every sibling obligation-family module joins), and registering the

    new REL390-REL393 rule ids in src/frob/gates/__init__.py''s

    _KNOWN_GATE_RULES (so REG002/registry re-disposition can resolve

    handled_by:REL39x references). Widening to match T-0646/T-0919''s own

    declared scope shape.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_kernel_interface_node_without_classification_fires
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_discharged_and_non_kernel_interface_nodes_clean
- tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification::test_waiver_discharges_finding
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_deployed_process_node_without_bounds_fires
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_discharged_and_non_deployed_process_nodes_clean
- tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds::test_waiver_discharges_finding
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
threat: null
component: null
---
Filed while reconciling T-0958's system-design.yaml deferred rows. SDC-13-EVERY-KERNEL-USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-IS-CLASSIFIED-INT and SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-BOUNDS-CGROUP-LIMITS-CPU-MEMORY-IO-AND name two genuinely checkable, currently-unbuilt obligations: (1) every kernel/userspace interface (syscall, procfs/sysfs entry, ioctl) a node touches being classified (trusted/untrusted, read/write, etc.) into the same kind of deny-by-default declared-attr obligation REL2xx/REL3xx already use, and (2) every deployed process node declaring its resource bounds (cgroup cpu/memory/io limits) -- structurally the same "declared bound + provability" shape _backpressure.py's REL260/261 and _interactive_cost.py's REL310/311 already establish for other resource dimensions, just not yet built for process-level cgroup bounds or kernel-interface classification. No landed REL/SYS family covers either concept today. Scope: a new strata rule module (e.g. src/frob/strata/_process_bounds.py) plus docs/strata/reliability.md plus the corresponding registry re-disposition once built.