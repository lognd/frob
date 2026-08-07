---
id: T-1064
title: 'WAIVE004 false-positive: file-level/header-position waivers permanently zero-match
  despite suppressing live findings'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1072 split moved the WAIVE00x/_match_waiver/_apply_waivers family out
    of

    gates/__init__.py into gates/_waive.py; T-1064''s fix lives entirely in the

    new module, so the scope glob is updated to follow the code.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAIVE004''s fix needs its documented known-flaky-classes list updated to

    describe the new structurally-unverifiable-rules exemption (INV006

    self-suppression, DUP001/DUP002/AFFECT001/AFFECT002 diff-scoping).

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_gates.py
  reason: 'New WAIVE004 unit tests live in TestTestGate in tests/test_gates.py;

    scope coverage for the enclosing class (touched by adding two methods)

    needs the file in scope, not just a per-method frob:ticket directive.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_exempts_a_diff_scoped_rule
- tests/test_gates.py::TestTestGate::test_waive004_still_fires_for_a_non_exempt_rule_with_the_same_shape
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestTestGate::test_waive004_exempts_a_structurally_unverifiable_rule
  new_node: tests/test_gates.py::TestTestGate::test_waive004_exempts_a_diff_scoped_rule
  reason: 'T-1763 renamed this test in place (same file, same class): INV006 was the
    self-suppressing example this test used to construct, deleted for producing zero
    live findings across its whole lifetime; the test now exercises the diff-scoped
    exemption class instead, same _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES mechanism'
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
Found while working T-0874 (stale-waiver purge). WAIVE004's own zero-match
pre-check (`_waive004_violations` / `_match_waiver` in
src/frob/gates/__init__.py) systematically reports a FALSE zero-match for a
specific waiver shape: a standalone, module/function-header-position waiver
comment immediately preceding a chain of `frob:enforces`/`frob:tests`/other
directive lines and then the bound symbol (e.g. INV006's per-file
"first-turn-on pool" waivers at the top of ~209 source files, and three
freshly-landed T-0861 DUP001/AFFECT001 header waivers in
src/frob/gates/__init__.py and src/frob/vet/_capability_registry.py).

Empirically: `frob check --only invariant` (scoped) correctly reports these
INV006 findings as LIVE (not stale) at the exact same sites WAIVE004 (full,
unscoped run) reports as "matches 0 findings this run" for the identical
waiver. Deleting these waivers on the strength of the full-run WAIVE004
report resurfaced ~200 genuine INV006 errors; restoring them verbatim made
the errors disappear again (confirming the waivers DO correctly suppress
real findings via the real `_apply_waivers` pass) while WAIVE004's own
pre-check continues to flag them as zero-match, seemingly indefinitely, on
every full run.

Suspected root cause: `_waive004_violations` matches by
`_match_waiver(v, {rule: [edge]}) is edge`, i.e. it re-derives `edge.src`
per-violation; if the underlying finding is FILE-level (line 0, e.g.
INV006's whole-file exclusivity-claim scan) but violations_by_rule
population or edge-origin resolution disagrees with the real
`_apply_waivers` pass's own site derivation for this specific comment
shape, the two consumers can permanently disagree on the same site. This
needs an isolated repro (a minimal INV006-shaped file-level finding plus a
header waiver) and a fix or a documented is-this-really-flaky
determination -- WAIVE004's own gate:WAIVE never reaches zero while this
class exists, since these waivers are demonstrably still required.

## Done report

WAIVE004's own zero-match pre-check was reading `all_violations` as ground
truth for "does this rule fire anywhere right now", but two rule classes
never let their finding reach `all_violations` in the first place,
independent of whether the waiver covering them is genuinely still needed:

- INV006 self-suppresses inside `_inv006_src_violations` (`_inv006_waived`
  checks for a covering `frob:waive INV006` edge and returns `()` before a
  `Violation` is ever constructed) -- confirmed empirically in T-0874's
  investigation: deleting one of these waivers resurfaces the exact INV006
  error it was suppressing, restoring it verbatim makes the error vanish
  again, while WAIVE004 reported "matches 0" both before and after. This
  was ~209 of ~216 WAIVE004 findings in this repo's own full run.
- DUP001/DUP002/AFFECT001/AFFECT002 only ever emit a finding for a symbol
  in the diff's own touched-ref set; a full unscoped run's diff is almost
  never the exact diff that first triggered the waived finding, so they
  read as "0 findings" for reasons unrelated to staleness -- the same
  unreliability class the existing SCOPE001/COV002/TODO001
  SCOPED_RUN_FLAKY_RULE_IDS set already documents, just diff-content
  driven instead of --ticket base drift.

Fix: `_WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES` in
src/frob/gates/_waive.py names these five rule ids; `_waive004_violations`
skips them the same way it already skips WAIVE002's and the arch-category
cases, via a `continue` on the per-edge loop. `_match_waiver` itself is
untouched -- rule-id-exact matching is unchanged, so a file-level waiver
still cannot swallow a line-scoped finding of some OTHER rule; only these
five rule ids are exempted from WAIVE004's own zero-match check, nothing
else.

Measured: a full, unscoped `frob check --json` run went from 216 WAIVE004
findings before the fix (209 INV006 + 3 DUP001 + 3 AFFECT001 + 1 ARCH102)
to 1 after (the remaining ARCH102 finding is not diff-scoped and not
self-suppressing -- a genuinely stale waiver, correctly still flagged).
Re-verified with `--ticket T-1064 --json`: same 1-finding result, 0 errors
across every gate group.

### Changed
```
 docs/modules/gates.md    | 30 ++++++++++++++++++++++++
 src/frob/gates/_waive.py | 61 ++++++++++++++++++++++++++++++++++++++++++++----
 tests/test_gates.py      | 49 ++++++++++++++++++++++++++++++++++++++
 tickets.md               | 44 ++++++++++++++++++++++++++++++++--
 4 files changed, 178 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive004_exempts_a_structurally_unverifiable_rule` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive004_still_fires_for_a_non_exempt_rule_with_the_same_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 716 warning(s), 419 waived
- error-findings: none (measured, zero errors)
