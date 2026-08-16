---
id: T-2192
title: 'T-2177''s scope-plausibility check misses every case it was built for: word-overlap
  passes any same-subject-area file, so all three real mis-scopings warn nothing while
  only a wildly unrelated file trips it'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_ticket_new_scope_plausibility_t2192.py
- tests/unit/test_ticket_new_scope_plausibility.py
evidence_scope:
- tests/unit/test_ticket_new_scope_plausibility_t2192.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_new_scope_plausibility_t2192.py
  reason: test file for the identifier-shaped scope-plausibility fix
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_ticket_new_scope_plausibility.py
  reason: changed function already has frob:tests edges to this file
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
- tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction
designated_repro_test: tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
acceptance:
- text: 'Measured against the real historical cases by calling _scope_plausibility_warnings
    directly: title ''auto-rebase conflicts on ledger files leaves worktrees stale''
    + scope src/frob/tickets/_land_git_ops.py -> NO WARNING (this is T-2173, mis-scoped
    for real); title ''land --plan --dry-run created a real merge commit on main''
    + scope src/frob/app/ticket_runner/_land_cmd.py -> NO WARNING (this is T-2189,
    mis-scoped for real); title ''strata header regex symbol count drift'' + scope
    src/frob/logging/color.py -> WARNS. The check is functional but only trips on
    a wildly unrelated file, which nobody files. This test MUST fail against current
    main.'
  evidence:
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction
- text: Require an IDENTIFIER-shaped match, not any shared word. Generic English tokens
    ('land', 'ledger', 'files', 'plan', 'merge', 'commit') appear in every file of
    a subject area, which is exactly where mis-scoping happens -- a wrong file in
    the RIGHT area is the failure mode, and word overlap cannot see it. Count only
    tokens that look like code identifiers (snake_case, CamelCase, dotted qualified
    names) or quoted string literals from the ticket text, matched against the file's
    grammar-parsed symbol and string-literal tokens. The file side is already AST-parsed
    and correct; the defect is that the TICKET side contributes ordinary prose words
    as if they were symbols.
  evidence:
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction
- text: 'Do NOT fix this by expanding the stopword list. That is a lexical patch to
    a lexical problem: the next mis-scoping uses different generic words and reopens
    it, and a growing stopword list is unmaintainable. Do NOT raise the required overlap
    COUNT either -- a same-area file shares many words, so any threshold that catches
    T-2173 would reject legitimate scopes wholesale. Change WHAT counts as a match,
    not how many are needed.'
  evidence:
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_wrong_file_now_warns
  - tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped::test_same_area_right_file_still_files_without_friction
threat: null
component: null
anchor: false
anchor_reason: null
---
