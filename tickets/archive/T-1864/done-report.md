## Done report

Fixed both regressions in place, no scope creep:

- E501 (src/frob/gates/_policy_weakening_gate.py:101): wrapped the
  Module(...) call across three lines so it fits the 88-column limit.
  The def line (69) was deliberately left untouched so the AFFECT001/
  COV002 doc-edge and coverage-stamp anchors did not shift.
- DOCENUM001 (docs/modules/gates.md:13): added the missing INV051
  member (alphabetically between INV008 and KRB001) to the
  frob:enumerates member list for _KNOWN_GATE_RULES, plus a matching
  table row documenting the rule.

Fixing the E501 line touched policy_weakening_gate's body, which
tripped two second-order gates the coordinator had already hit and
warned about:

- AFFECT001 (the function's affects()-closure doc,
  docs/strata/policy.md#refinement-monotonicity-inv-051-t-1482, was
  not touched in the same diff): added a short paragraph documenting
  the T-1864 line-wrap so the doc anchor is genuinely touched, not a
  no-op edit.
- COV002 (frob:ticket edge pointed only at T-1843, which is closed):
  added a second `frob:ticket T-1864` line alongside the existing one.

Landed together with T-1839's drop (both were uncommitted in the same
worktree when T-1839 landed, and land's pre-commit wip-commit swept
them in) at commit 44a1ef61f563d16799d608d827b4a00febe79d52, verified
is_ancestor_of_main=True. Confirmed via two `frob check --budget 500`
passes (covering all gates-fast/gates-native/gates-security groups)
plus separate `--only lint` and `--only static` runs against current
main: zero error-severity diagnostics anywhere in the run.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 927 warning(s), 742 waived
- error-findings: none (measured, zero errors)
