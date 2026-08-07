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
