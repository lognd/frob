---
id: T-1477
title: 'warning burn-down: NEGEXIST/DOC/WAIVE/COV binding classes'
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Drain four warning classes to honest zero (or bound/justified) across the
repo, per the drain-to-zero drive wave 13 brief:

1. NEGEXIST001 (~39): unbound negative-existence claims in docs -- bind
   each absence-claim to a real open ticket via frob:until where the
   absence is tracked work, or reword prose that is descriptive rather
   than normative. Never blanket-waive.
2. DOC (~26 warnings): read the actual DOC00x findings and fix (stale
   refs, unresolvable anchors).
3. WAIVE004 (~20): stale waivers matching 0 findings -- for each, verify
   the underlying finding is genuinely gone, then DELETE the waiver; keep
   any whose finding is merely intermittent, with a dated note.
4. COV006/COV007 (~41): COV006 = frob:tests edges bound to private
   symbols the call graph cannot reach -- rebind to a symbol the test
   actually calls. COV007 = frob:doc anchors on private symbols -- move
   onto the public caller unless genuinely warranted (keep with a reason
   comment).

Batch commits by class; scoped verification after each class; evidence
via an evidence-cmd capturing before/after counts per class.