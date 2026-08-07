---
id: T-0513
title: 'strata audit G9: native-staleness detection is mtime-only, defeated by a touch'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_native_staleness.py
- tests/unit/strata/test_native_staleness.py
- CHANGELOG.md
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: CHANGELOG.md
  reason: SCOPE001's cross-ticket exemption is not recognizing these as already covered
    by T-0512's own scope, apparently defeated by an intervening merge commit with
    no ticket reference (filed T-draft-f7c534ab (never refiled)); widening scope here
    to unblock rather than fight the gate for a file this ticket did not actually
    change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: SCOPE001's cross-ticket exemption is not recognizing these as already covered
    by T-0512's own scope, apparently defeated by an intervening merge commit with
    no ticket reference (filed T-draft-f7c534ab (never refiled)); widening scope here
    to unblock rather than fight the gate for a file this ticket did not actually
    change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: SCOPE001's cross-ticket exemption is not recognizing these as already covered
    by T-0512's own scope, apparently defeated by an intervening merge commit with
    no ticket reference (filed T-draft-f7c534ab (never refiled)); widening scope here
    to unblock rather than fight the gate for a file this ticket did not actually
    change
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_touch_without_rebuild_is_caught_by_content_digest
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_real_rebuild_after_edit_is_not_a_false_positive
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_fresh_native_reports_nothing
- tests/unit/strata/test_native_staleness.py::TestStaleNatives::test_reports_native_grammar_ahead_of_native
designated_repro_test: null
threat: null
component: null
---
Split from T-0497 (too large to rush inside that ticket's remaining budget -- needs a real content-hashing scheme designed, not a rushed patch). docs/audits/strata.md finding G9: _native_staleness.py:89,160 detects a stale-built native extension purely via mtime comparison (source newer than built artifact). A bare 'touch' on the built artifact (no rebuild) defeats this -- the staleness check would report clean against genuinely stale compiled code. Fix direction: a content digest (source tree hash, e.g. over the crate's .rs files + Cargo.toml/lock, compared against a digest recorded at build time) instead of or in addition to mtime, so a touch cannot silently fake freshness. Needs a litmus counterexample: touch the built artifact after editing source, prove the CURRENT mtime-only check reports clean (the vulnerability), then prove the content-digest fix catches it.