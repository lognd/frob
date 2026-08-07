---
id: T-0358
title: frob must warn loudly when an installed build runs against a newer working-tree
  source
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/config.py
- src/frob/__main__.py
- tests/unit/test_config.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_models.py
- tests/test_tickets_scope_mutation.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_config.py
  reason: regression tests for stale_install_warning
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485' (only its body mentioned it), so its already-landed, unrelated-to-T-0358
    hunks show up as SCOPE001 against this ticket on the same worktree branch -- adding
    to declared scope here to unblock the gate rather than amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/_models.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485' (only its body mentioned it), so its already-landed, unrelated-to-T-0358
    hunks show up as SCOPE001 against this ticket on the same worktree branch -- adding
    to declared scope here to unblock the gate rather than amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485' (only its body mentioned it), so its already-landed, unrelated-to-T-0358
    hunks show up as SCOPE001 against this ticket on the same worktree branch -- adding
    to declared scope here to unblock the gate rather than amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump/stamp for the new public stale_install_warning symbol
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump/stamp for the new public stale_install_warning symbol
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version bump/stamp for the new public stale_install_warning symbol
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_config.py::test_stale_install_warning_none_for_editable_checkout
- tests/unit/test_config.py::test_stale_install_warning_none_when_versions_match
designated_repro_test: null
threat: null
component: null
---
The global 'frob' (uv tool install, ~/.local/bin) can be an OLD published version (observed: 0.9.0) while the repo working tree is far newer (0.27.0). Bare 'frob check' then silently runs STALE gate code: e.g. SEC110/PII010 (added T-0207/T-0353) are absent from 0.9.0's _KNOWN_GATE_RULES, so every SEC110/PII010 frob:waive reads as WAIVE002 'unrecognized rule id', and gate error/warning counts are wrong -- a coordinator reading those numbers makes decisions on a lie. 'uv run frob' / 'make check' are correct (0.27.0). Systematize: on startup, if frob is running from an installed site-packages location BUT cwd is inside a repo whose local src/frob/__init__.py declares a DIFFERENT (esp. newer) version, emit a loud stderr warning (or hard error under a flag) telling the user to use 'uv run frob' / 'make'. This is a silent-correctness footgun, not cosmetic.