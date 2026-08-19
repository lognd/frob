---
id: T-2549
title: 'COV007 reads a strata security clearance as API privacy: 25 false findings
  on design/frob.strata'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public
- tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549
- tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper
- tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol
designated_repro_test: tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ef519d6a017157246aef1e090c3510c5841d2e58
---
COV007 ("frob:doc on private symbol") fires on 25 `design/frob.strata`
component nodes -- `frob.cli`, `frob.security`, `frob.gates`, ... -- none
of which is private in any API sense.

ROOT CAUSE, confirmed by reading both sides:

- `_cov007` (src/frob/gates/__init__.py) skips an edge when
  `snapshot.symbols[edge.src].public` is true, and reports it otherwise.
- For a `.strata` file, `RawSymbol.public` does NOT mean "public API".
  `frob.lang._walk_strata._build_symbol` (T-2410) derives it from the
  node's declared SECURITY CLEARANCE: `public = True if clearance is None
  else clearance == "Public"`. Every `trusted`/`internal` component is
  therefore `public=False`.

So COV007 reads a clearance label as a naming-convention privacy marker
and demands a fix whose stated remedy ("move it onto the public caller")
has no meaning for a strata component node. All 25 findings are false.

This is the SAME blindness class the sibling check already handles
explicitly: `_cov006_edge_violation` skips a non-python target with the
reasoning "`build_call_graph`'s privacy resolution
(`_short_name(qualname).startswith('_')`) is a PYTHON naming convention".
COV007 never got that guard.

FIX: skip a COV007 edge whose src file is not python, matching COV006's
Class-4 precedent. Narrowing, so it needs controls in BOTH directions:
- a python private symbol with a frob:doc edge must STILL fire;
- a strata node with a frob:doc edge must not.

Measured today, unbudgeted `frob check --only coverage --json`: COV007
139 live warnings, of which 25 are this class.