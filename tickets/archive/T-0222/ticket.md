---
id: T-0222
title: per-node capability excuse channel + missing needles (fs-read, uvicorn bind,
  pyo3 import)
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability_registry.py
- src/frob/vet/_capability.py
- tests/**
- docs/strata/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_operations
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 5 (HIGH for adoption; 6 residual gaps across graphite+feldspar trace here): real-but-scanner-invisible capabilities force permanent SYS101 red or dishonest under-declaration -- may ffi on a pyo3-import node, may net for uvicorn.run, may fs for Path.read_text are all 'declared but never observed'. Fix both sides: (a) BenignCapability-style per-node excuse with a written reason (relates to T-0174 waiver channel -- coordinate, do not duplicate); (b) add the missing needles: fs-read (Path.read_text/open-for-read), socket/uvicorn bind, compiled-extension import as ffi observation. Litmus per needle per T-0182 discipline.