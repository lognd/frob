---
id: T-1784
title: 'New rule: flag repo-root asset directories with zero code references'
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_root_asset_dirs.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_root_asset_dirs.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates.py
  reason: 'narrow package glob to the exact files this ticket touches: new gate module,
    its __init__.py wiring, the _KNOWN_GATE_RULES registry, docs, and tests'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires
- tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_under_src_frob_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_directory_referenced_in_pyproject_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_directory_with_external_reader_declaration_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_makefile_referenced_directory_is_silent
- tests/test_gates.py::TestRootAssetDirGate::test_allowlisted_directories_are_silent
designated_repro_test: tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires
acceptance:
- text: given a repo-root directory with zero code references, when frob check runs,
    then ROOT001 fires -- FAIL before this rule existed (frob.gates._root_asset_dirs.root_asset_dir_gate
    did not exist, ModuleNotFoundError), PASS after (root_asset_dir_gate reports ROOT001
    for the fixture directory)
  evidence:
  - tests/test_gates.py::TestRootAssetDirGate::test_unreferenced_root_directory_fires
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1611 classification: today's session produced the "root agents/
skills/ are live-read by the dispatching harness" incident. T-1767's
audit concluded KEEP, reporting the 13 tracked SKILL.md files
"empirically confirmed live-read" because their prose content happened
to match this very session's own system-prompt role definitions and
available-skills roster near-verbatim -- a coincidence of AUTHORSHIP
(the harness's real ~/.claude/agents, ~/.claude/skills were almost
certainly seeded FROM these files at some point), misread as proof of a
LIVE LOAD PATH. T-1772 corrected it: `grep` across src/frob/** for
`agents/`/`skills/` path references returns nothing, pyproject.toml
packages `src/` only, `frob scaffold` does not emit either directory --
nothing in this repo's own code reads either tree. Deleted.

Classified as NO RULE EXISTS for this obligation. This is not a
misfire of DEAD001 or REF002 -- both are scoped to Python
symbols/`.strata` fixture files respectively; neither one's domain
covers "a whole repo-root directory of markdown assets that a doc or
ticket claims is read by some process." The verification that settled
T-1772 (grep the tree for path references, confirm packaging config,
confirm scaffold does not emit it) was manual and ad hoc; nothing
mechanizes it, so the same wrong "must be live, the names match" READ
can recur on the next repo-root directory someone audits.

Add a rule: for each repo-root top-level directory NOT under `src/`,
`tests/`, `.git/`, or an explicit allowlist (docs/, tickets/, design/,
scripts a Makefile target actually invokes, etc.), verify at least one
of (a) `src/frob/**` references its path literally, (b)
`pyproject.toml`'s package/data-files config includes it, (c)
`frob scaffold`'s own data emits it, or (d) an explicit
`frob:external-reader reason="..."` doc-side declaration names the
external process that reads it (the harness-config case: a real,
checkable claim instead of an inferred one). A directory satisfying
none of the four is flagged -- not auto-deleted, just surfaced, so the
next audit starts from a measured "zero code references" fact instead
of re-deriving it from scratch and getting fooled by name-matching
again.