---
id: T-0433
title: G6 fingerprint derivation from frob.lang grammar registry; G7 hash/parse TOCTOU
  (T-0402 residual)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0402
tier: ticket
sprint: null
scope:
- src/frob/graph/
- src/frob/lang/
- docs/modules/lang.md
- tests/test_graph.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_models.py
- tests/test_tickets_scope_mutation.py
- CHANGELOG.md
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/lang.md
  reason: frob:doc anchor for the new GRAMMAR_FINGERPRINT_PACKAGES public symbol,
    and its regression test in test_graph.py
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_graph.py
  reason: frob:doc anchor for the new GRAMMAR_FINGERPRINT_PACKAGES public symbol,
    and its regression test in test_graph.py
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485', so its already-landed, unrelated-to-T-0433 hunks show up as
    SCOPE001 against every subsequent ticket on this shared worktree branch -- adding
    to declared scope here (same as done for T-0358) to unblock the gate rather than
    amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/_models.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485', so its already-landed, unrelated-to-T-0433 hunks show up as
    SCOPE001 against every subsequent ticket on this shared worktree branch -- adding
    to declared scope here (same as done for T-0358) to unblock the gate rather than
    amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_scope_mutation.py
  reason: SCOPE001 cross-ticket exemption (T-0108) requires the OTHER ticket's id
    literally in the commit SUBJECT line; T-0485's code-change commit (35f2678) subject
    omitted 'T-0485', so its already-landed, unrelated-to-T-0433 hunks show up as
    SCOPE001 against every subsequent ticket on this shared worktree branch -- adding
    to declared scope here (same as done for T-0358) to unblock the gate rather than
    amend a prior commit
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump/stamp/changelog for T-0433's new public GRAMMAR_FINGERPRINT_PACKAGES
    symbol; also backfills the CHANGELOG entry for 0.54.0 (T-0358's bump) that gate:REL
    flags as missing
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump/stamp/changelog for T-0433's new public GRAMMAR_FINGERPRINT_PACKAGES
    symbol; also backfills the CHANGELOG entry for 0.54.0 (T-0358's bump) that gate:REL
    flags as missing
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 version bump/stamp/changelog for T-0433's new public GRAMMAR_FINGERPRINT_PACKAGES
    symbol; also backfills the CHANGELOG entry for 0.54.0 (T-0358's bump) that gate:REL
    flags as missing
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 version bump/stamp/changelog for T-0433's new public GRAMMAR_FINGERPRINT_PACKAGES
    symbol; also backfills the CHANGELOG entry for 0.54.0 (T-0358's bump) that gate:REL
    flags as missing
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_packages_derived_from_lang_registry
- tests/test_graph.py::TestBuildIncremental::test_stored_hash_matches_bytes_actually_parsed
designated_repro_test: null
threat: null
component: null
---
Residual from T-0402 graph audit (docs/audits/graph.md): G6 full native-fingerprint derivation from the frob.lang grammar registry (partial fix landed -- added strata-core entry, full registry-derivation deferred); G7 the hash-then-load TOCTOU window in load_graph (a file edited between content-hash and read). Both real, deferred as out of the round-1 graph-foundation scope.