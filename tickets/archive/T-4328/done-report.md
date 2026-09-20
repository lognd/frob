## Done report

Changed: frob.toml (severity of 11 rules)

Audit method: cross-referenced the full 308-rule list promoted by
f1ce94dfa0 (T-3844) against explicit contradictory-severity language in
`src/frob/gates/*.py` (git grep -niE for
"advisory|nudge|warn-only|stays warn|never a hard (build )?failure|never
fails `frob check`|permanently by design" etc.), then read each hit's
surrounding docstring/module comment in full to confirm intent before
touching anything. Also checked the 9 rules in `_UNWAIVABLE_RULES`
(TEST008/SEC003/TICK001/TICK002/EXCL001/COMPLIANCE006/REG012/DEC003/
WIRE002) that were promoted: all 9 are DELIBERATELY, explicitly
documented as unwaivable-by-design with a real, non-waiver remedy path
(fix the root cause) -- unlike SCOPE002's accidental unwaivability, these
are correctly left at error and NOT flagged.

Flagged and demoted (property 1: own docs contradict "error"):
- INV004 -- "Always WARN ... never fails `frob check`" (frob.gates._inv)
- PORT001-IDENT -- "stays WARN/advisory permanently by design, not as an
  intermediate state on the way to ERROR" (frob.gates._port_selfcheck).
  Note PORT001-PATH/PORT001-DEFAULT were correctly left at error: their
  own docstring names "zero findings after burn-down" as their actual,
  designed promotion trigger, so the ratchet's criterion matches their
  documented intent for those two ids.
- PROTO001 -- "stays WARN-only (advisory-but-tracked...)"
  (frob.gates._protocol_summary); PROTO002-005 correctly left at error
  (T-0746's own "enforceable, never fail-silent" mandate, per the same
  docstring).
- REF001 -- "all WARN severity -- this is an advisory-but-tracked family
  per the user ... never a hard build failure" (frob.gates._refs)
- REG008/REG009/REG010/REG011 -- module docstring: "REG008-REG011 are
  WARN/advisory (each an honest first-turn-on debt over this repo's own
  large pre-existing corpus, per their own docstrings -- not weaker
  checks, just not yet promotable to ERROR without immediately redding
  the build on old debt)" (frob.gates._registry_exhaustiveness). REG001-7
  correctly left at error per the same docstring.
- SYS107 -- property 1 in a different shape: the code implements a
  deliberate PER-CAPABILITY severity split (`_selfaudit_severity`):
  fail-closed atoms (exec/eval/install-hook/ffi) are unconditionally
  ERROR; every other capability is WARN unless the repo opts in via
  `[strata] require_may_scope`. `frob.toml`'s blanket `[gates.severity]`
  override (`_apply_severity_overrides`, unconditional rule-id match)
  collapses that opt-in gate for ALL capabilities, effectively making the
  opt-in decision for every repo without going through the actual opt-in
  mechanism.
- TEST011 -- "TEST011's OTHER signal (stale_by_mtime) stays WARN because
  routine editing makes coverage.xml stale constantly -- flipping that to
  ERROR would fail the gate on completely ordinary dev flow"
  (frob.gates.__init__); confirmed TEST011 has exactly one emission site,
  so the whole rule is this signal, not a mix.
- TICK009 -- property 1 AND 2 together: docstring says "one WARN per
  over-broad-scope nudge" and the code hardcodes `Severity.WARN`
  (overridden anyway by the blanket table). Also reports
  `file="tickets.md", line=0` -- that path does not exist under the
  per-ticket ledger layout (verified: `ls tickets.md` -> no such file),
  the same synthetic-unwaivable-finding shape T-4310 fixed for SCOPE002.
  A `scope_breadth_ack`'d ticket is exempt (T-1484), but any non-acked
  PLANNED/IN_PROGRESS ticket with a broad glob would trip an unclearable
  error the same way SCOPE002 did. Demoted pending a real fix (tracked
  in the follow-up ticket below rather than attempted here, since a
  proper fix needs the same kind of change T-4310 made and this ticket's
  scope is frob.toml only).

Left at error after reading their docstrings (explicitly confirmed
correct, not merely unexamined): REG001-007, PROTO002-005,
PORT001-PATH, PORT001-DEFAULT, all 9 `_UNWAIVABLE_RULES` members, and
VET-JS*/VET-PY*/VET-RS*/VET-SOURCE-UNAVAILABLE/VET-TIMEOUT/HOST-BLAST/
SEC-CVE-FINGERPRINT-001 (fail-closed, deliberately hard, no contradicting
language found).

NOT exhaustively audited: the remaining ~283 of the 308 rules. The
grep-based sweep covers property 1 (explicit contradictory language) with
reasonable confidence but does not systematically cover property 2
(does every rule's `Violation` carry a real, waiver-matchable file/line,
or a synthetic one like TICK009/SCOPE002) or property 3 (can the rule
currently fire at all, or is it structurally silent) across all 308.
Filed T-4331 to carry that remaining work with the method that worked
here plus the two properties this pass did not systematically check.

Evidence: `uv run frob check --ticket T-4328 --json` after the change --
SEVERITY {'warning': 4856, 'info': 91, 'note': 1832, 'error': 3}; all 3
errors are pre-existing and out of scope for T-4328: INV003/REF002 on
docs/modules/verify-rapid-debt-visibility.md (landed by T-4324, unrelated
file, confirmed via `git log -- <path>`), and SCOPE001 on
tickets/T-4331/ticket.md (this ticket's own filed follow-up; ticket-filing
commits on this branch are outside `scope=['frob.toml']` by construction).
Before this change (same --ticket run, before the frob.toml edit and
before filing T-4331): identical error set minus the SCOPE001 line --
confirms the frob.toml edit introduces zero new errors.

Filed: T-4331 (audit remaining ~283 rules for waivability + structural
silence)

Gates: `frob check --ticket T-4328` clean of new errors (3 pre-existing/
out-of-scope errors unchanged by this diff, itemized above).

### Changed
```
 tickets/T-4328/done-report.md | 110 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4328/ticket.md      |  12 +++++
 tickets/T-4331/ticket.md      |  61 +++++++++++++++++++++++
 3 files changed, 183 insertions(+)
```

### Evidence
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4694 warning(s), 954 waived
- error-findings: INV003@docs/modules/verify-rapid-debt-visibility.md, REF002@docs/modules/verify-rapid-debt-visibility.md
