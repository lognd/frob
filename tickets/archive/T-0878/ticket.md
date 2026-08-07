---
id: T-0878
title: 'gate: src/frob/exports/__init__.py missing frob:doc anchors (COV001/DOC, landed
  via T-0601 area merge)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/exports/__init__.py
- docs/modules/exports.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_exports.py::TestExportsConsumers::test_as_text_output
- tests/unit/test_exports.py::TestExportsConsumers::test_as_json_output
- tests/unit/test_exports.py::TestExportsConsumers::test_finds_import_consumer
- tests/unit/test_exports.py::TestExportsConsumers::test_excludes_prose_mention
designated_repro_test: null
threat: null
component: null
---
Pre-existing, unrelated to any arch-cluster ticket: after merging current main into a worktree mid-session (T-0632), a fresh frob check --only gates-fast shows 5 new gate:COV001/gate:DOC errors on src/frob/exports/__init__.py (ConsumerRef, ConsumersResult, ConsumersResult.as_text, ConsumersResult.as_json, exports_consumers all public with no frob:doc edge). This file/these symbols are not part of any ticket in this worktree's scope -- discovered purely as a side effect of picking up main's advancement mid-session. File to track adding the missing frob:doc anchors (and any docs/modules/exports.md content they should point at).