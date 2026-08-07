---
id: T-0297
title: COV001 cannot detect directive rebound to WRONG symbol (only checks attached-to-something)
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/graph/**
- tests/**
- docs/modules/gates.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags
- tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean
- tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean
designated_repro_test: null
acceptance:
- text: given a frob:tests/doc/waive/ticket directive that a refactor displaced from
    its intended public function onto a newly-extracted private helper (the exact
    hazard that hit two arch slices), when COV001 runs, then it FLAGS the mis-binding
    -- today it passes because it only verifies a directive resolves to SOME symbol,
    not the correct one
  evidence: []
- text: given a legitimately-moved symbol whose directive correctly moves with it,
    then no false positive fires
  evidence: []
threat: null
component: null
---
Surfaced by reviewer 2026-07-19 during the core-commands arch burndown: extracting a helper directly above an existing def silently rebinds that defs frob: directives onto the new (private) helper. COV001 does NOT catch this -- it only checks a directive is attached to a resolvable symbol, not the semantically-intended one. So a frob:waive TEST005 or frob:tests evidence binding can silently start describing the wrong function (misrepresenting coverage debt / test evidence) and every gate stays green. This bit TWICE (scan_tree, renumber_one) and was only caught by manual review. Candidate detections: (a) a directive whose target is a PRIVATE (_underscore) symbol when the same directive kind/anchor previously bound a public symbol in that file (git-diff-aware), (b) a frob:tests binding whose named test function bodies do not actually exercise the bound symbol (call-graph reachability -- ties into the shared call-graph substrate of T-0288/T-0290), (c) a frob:doc #public-api anchor on a private helper. This is core to the north star: a displaced obligation is worse than a behavior bug because it is silent. See [[static-quality-vision]].