---
id: T-0449
title: 'ref gate: LINK .pyi type stubs to their native module/crate (a real reference
  edge), do NOT exempt -- strata_core.pyi is the typed interface of the strata_core
  extension built from strata-core/, so it must be accounted, not hidden'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- strata-core/strata_core.pyi
- frob-core/frob_core.pyi
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refs_gate.py::TestNativeStubLinking::test_linked_pyi_beside_matching_manifest_does_not_fire_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_pyi_with_manifest_present_but_module_name_mismatch_still_fires
designated_repro_test: null
threat: null
component: null
---
The REF002 triage first proposed EXEMPTING .pyi sidecar stubs from REF001
(like the test-file implicit-reference exemption). User correction
2026-07-20: that is the lazy escape hatch and violates the "declare exactly
where we use it" North-Star. A .pyi stub is NOT an orphan -- strata_core.pyi
is the typed interface of the strata_core native extension, which is
compiled from the strata-core/ Rust crate (same for frob_core.pyi <-
frob-core/). That is a real, declarable dependency edge; hiding it behind an
exemption is exactly the kind of un-accounted relationship the ref gate
exists to surface.

Correct design: the ref gate should RESOLVE the sidecar-stub relationship as
a genuine reference edge, so the stub is counted as LINKED, not skipped:
- A `<name>.pyi` sitting beside a compiled extension `<name>` (or naming a
  package that a manifest declares as a native module) is a reference edge
  stub -> module: the stub describes/types that module. Record it as a real
  edge in the graph so the stub has an honest referencer and the module has
  an honest referrer.
- Cross-language link: strata_core.pyi <-> strata-core/ (Cargo crate whose
  maturin/pyo3 build produces the strata_core extension); frob_core.pyi <->
  frob-core/. Prefer making this edge explicit via a directive the stub
  carries (e.g. `# frob:describes strata-core/src/lib.rs` or
  `frob:used-by`), AND/OR have ref_gate infer the stub<->extension pairing
  from the build manifest (pyproject [tool.maturin] / the Cargo crate that
  emits the abi3 module), so it is a resolved edge, not a hardcoded skip.
Acceptance: strata_core.pyi and frob_core.pyi each show a REAL reference
edge to their crate/module in the graph (queryable via `frob graph`), REF001
no longer fires on them BECAUSE they are linked (not because they are
exempted), and a NEW un-linked .pyi with no adjacent module still fires
REF001. Supersedes the exemption framing entirely.