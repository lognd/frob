---
id: T-1230
title: non-python doc targets -- Makefile/frob.toml/pyproject/Rust layout edges into
  the graph
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- docs/audits/docs-staleness-2026-07-29.md
- docs/modules/graph.md
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
- src/frob/gates/_waive.py
- tests/test_gates.py
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/audits/docs-staleness-2026-07-29.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/graph.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_doclink_docanchor.py
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1230: non-python (Makefile) target validation lands as DOC010 in the
    existing doclink/docanchor family, same infra DOC008/DOC009 already used -- wiring
    touches the same gate-registration files those tickets touched'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestDocmakeGate::test_bogus_make_target_fires_doc010
- tests/test_gates.py::TestDocmakeGate::test_real_make_target_passes
- tests/test_gates.py::TestDocmakeGate::test_no_makefile_is_a_noop
designated_repro_test: null
threat: null
component: null
---
Doc edges to Makefile recipe/dep claims, frob.toml severity claims, pyproject entries, Rust file layout; builds on the multi-language graph. Relate to T-1193's python-only theme; check whether its children already cover part of this and cross-reference rather than duplicate. Ref: gate-gap class 4 in docs/audits/docs-staleness-2026-07-29.md.