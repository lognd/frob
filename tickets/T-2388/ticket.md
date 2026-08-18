---
id: T-2388
title: 'PORT001: meta-gate detecting gates that hardcode project identity instead
  of resolving it'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_port_selfcheck.py
- tests/unit/gates/test_port_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py
  reason: T-2397 holds a live lease on gates/__init__.py for unrelated wiring work;
    will add the PORT001 registration line back once that lease clears, per playbook
    step 4 (narrow rather than wait idle)
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/modules/gates.md
  reason: T-2397 also holds a live lease on docs/modules/gates.md; will add PORT001's
    doc entry back once that lease clears
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_path_prefix_is_flagged
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_hardcoded_identity_literal_in_tuple_is_flagged
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_allowlisted_self_match_file_is_silent
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_never_scanned
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_clean_gate_module_is_silent
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_search_literal_is_resolved_not_hardcoded
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_unresolved_project_name_is_not_a_clean_pass
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_unparseable_file_is_parse001_not_silent
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_gate_code_never_scanned
  new_node: tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_never_scanned
  reason: 'T-2405: test renamed to reflect widened DETECTOR_PACKAGE_ROOTS scope, same
    coverage'
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2dd06110cb916bd25ff0201e7c7bae176d8e61dc
---
Child of T-2384. Coordinator directive (2026-08-18): the per-site retarget
of the 22 "src/frob/" literals fixes today's instances only. PORT001 is
the durable meta-check -- same shape as LEXCHECK001
(src/frob/gates/_lexical_selfcheck.py, T-2344), which is the precedent to
mirror, not redesign from scratch: an allowlisted, AST-scanning gate over
src/frob/gates/** (and other gate-bearing packages) with a documented,
reviewed exemption list.

PORT001 flags, per function/module in a gate-bearing package:
  - a string literal containing this project's own package path/name used
    as a path prefix (the `rel.startswith("src/frob/")` shape);
  - a literal duplicating a value an existing resolver already computes
    (general form of the T-2384 bug: "a constant that re-implements a
    resolver" -- e.g. hardcoding "frob" where
    frob.lang._nodes._declared_python_source_roots-derived data exists);
  - absolute filesystem paths, home-directory paths, hardcoded usernames
    in gate logic.

Exemption discipline (mirrors LEXCHECK001's _ALLOWLIST, reviewed with a
one-line reason per entry, not a structural carve-out):
  - gates/_pii_structural/_self_match.py is deliberately about frob's own
    files -- allowlist by (module, function), not by "any self-referential
    string is fine" (that shape would readmit the real bug).
  - app/_config_meta.py's `project.get("name") != "frob"` is a deliberate
    self-identification check for the version floor -- allowlist
    similarly.
  - `strata/_compliance.py`'s owner="logan" is frob's own registry DATA,
    not gate mechanism -- likely out of PORT001's scanned package set
    entirely (not a gates/ file); confirm during implementation.

Verification (same bar as the rest of the epic):
  - must-now-fire fixture: a gate-shaped file (in the scanned package
    shape) containing a hardcoded package-prefix literal PORT001 must
    flag.
  - must-still-pass control: the legitimate self-referential gates named
    above must NOT be reported.
  - report the finding count PORT001 produces against the CURRENT tree
    (before the T-2384 retarget tickets land) as the honest denominator --
    expected close to the 22-file measurement in T-2384's body; a large
    divergence means the detector is miscalibrated, not that the
    measurement was wrong.

Sequencing: does not block T-2386 (sync-skills, stays first) or delay it;
independent scope.