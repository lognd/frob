---
id: T-0515
title: burn down residual 604 INV003/INV004 findings after T-0509 calibration
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- invariants
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/
- docs/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: T-0509 next-step calibration required editing the INV004 gate implementation
    itself (file-granularity + spec-dir scoping), plus its unit tests
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates.py
  reason: T-0509 next-step calibration required editing the INV004 gate implementation
    itself (file-granularity + spec-dir scoping), plus its unit tests
  actor: logan
  at: '2026-07-21'
- op: remove
  glob: docs/modules
  reason: bare dir entries (no trailing slash) don't fnmatch-expand to recurse (frob.tickets._models._scope_globs);
    use dir/ form so docs/modules/*.md actually falls in scope (SCOPE001 was firing
    on docs/modules/gates.md)
  actor: logan
  at: '2026-07-21'
- op: remove
  glob: docs/strata
  reason: bare dir entries (no trailing slash) don't fnmatch-expand to recurse (frob.tickets._models._scope_globs);
    use dir/ form so docs/modules/*.md actually falls in scope (SCOPE001 was firing
    on docs/modules/gates.md)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/
  reason: bare dir entries (no trailing slash) don't fnmatch-expand to recurse (frob.tickets._models._scope_globs);
    use dir/ form so docs/modules/*.md actually falls in scope (SCOPE001 was firing
    on docs/modules/gates.md)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/strata/
  reason: bare dir entries (no trailing slash) don't fnmatch-expand to recurse (frob.tickets._models._scope_globs);
    use dir/ form so docs/modules/*.md actually falls in scope (SCOPE001 was firing
    on docs/modules/gates.md)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory
- tests/test_gates.py::TestInv004Gate::test_section_with_any_invariant_marker_is_silent
- tests/test_gates.py::TestInv004Gate::test_section_with_no_normative_language_is_silent
- tests/test_gates.py::TestInv004Gate::test_two_sections_only_flags_the_underspecified_one
- tests/test_gates.py::TestInv004Gate::test_any_bound_invariant_anywhere_in_file_silences_every_section
- tests/test_gates.py::TestInv004Gate::test_missing_docs_dir_is_silent
- tests/test_gates.py::TestInv004Gate::test_outside_spec_dirs_is_silent
- tests/test_gates.py::TestInv004Gate::test_markdown_waive_marker_with_reason_is_silent
- tests/test_gates.py::TestInv004Gate::test_markdown_waive_marker_without_reason_still_warns
- tests/test_gates.py::TestInv004Gate::test_claim_without_verb_in_sentence_is_silent
designated_repro_test: null
threat: null
component: null
---
T-0509 calibrated INV003/INV004: noise-stripping (fenced/inline code, links, table rows), a claim-verb requirement in the same sentence as the trigger word, INV003 scoped to INV003_SPEC_DIRS (docs/modules, docs/strata) instead of all docs/**.md, and markdown-side frob:waive support. Combined warnings dropped from 765 to 604 (INV003 88->31, INV004 677->573), measured via frob check --only invariant on this worktree before/after. 604 is still above the <30 in-ticket-burndown threshold, so this residual was NOT hand-burned down in T-0509. Next steps: bind real invariants/INV-###.md files for genuine claims, add <!-- frob:waive INV003|INV004 reason="..." --> markers for design-intent-only prose, and reword sections that used normative language loosely. INV004's 573 is the larger share (all of docs/**.md still in scope) -- consider whether INV004 also warrants directory scoping or a further claim-shape narrowing as part of this burndown.