## Done report

Built Tier-C fix-it emission per docs/design/check-fix-engine.md's "Fix-it
emission format" section: new src/frob/gates/_fix_engine_tier_c.py with a
FixIt model (rule, file, line, message, proposed_patch, reason_unfixable),
TIER_C_EMITTERS: dict[str, TierCEmitter] (the Tier-C sibling of
_fix_engine.TIER_A_HANDLERS/_fix_engine_tier_b.TIER_B_HANDLERS), and
apply_tier_c_fixits.

Design decisions:
- A TierCEmitter takes the single Violation it emits a FixIt for
  ((root, snapshot, violation) -> FixIt | None), unlike Tier A/B's
  scan-the-whole-tree shape -- Tier C never mutates, so there is nothing
  to apply repo-wide.
- Real emitter shipped: emit_todo001_fixit for TODO001 (a bare untracked
  to-do comment with no ticket to bind it to) -- the canonical Tier-C
  example _fix_engine.py's own module docstring already names. Binding a
  bare comment to a real ticket id is a judgment call the fix engine must
  never guess at, so this emitter always returns a FixIt with
  proposed_patch=None and a non-empty reason_unfixable, never touching
  the file.
- apply_tier_c_fixits/TIER_C_EMITTERS/emit_todo001_fixit are not
  reachable from any real CLI invocation yet (T-1481 wires that,
  alongside Tier A/B's own CLI wiring) -- each site carries a
  frob:waive WIRE001 ... follow_up="T-1481" naming that open ticket.
- Had to reword two docstring/comment lines that literally embedded the
  words TODO/FIXME (describing TODO001's own message shape) -- they
  tripped this repo's own TODO001 scanner (word-boundary TODO|FIXME) on
  this module's own source; reworded to "untracked to-do comment"
  phrasing with no false-positive trigger.

Scope was extended via the ticket scope CLI's --add flag:
- docs/design/check-fix-engine.md (AFFECT001: same-diff doc update --
  added a "T-1263 implementation note" subsection)
- design/frob.strata (SELFAUDIT001 SYS104: new public interface= symbols
  FixIt/TIER_C_EMITTERS/TierCEmitter/apply_tier_c_fixits/
  emit_todo001_fixit on the gates node, TestFixEngineTierC on the
  testsuite node; both nodes gained a frob:ticket T-1263 edge for
  COV002). No new fs.read/fs.write capability declaration was needed --
  this module never touches the filesystem, by design (Tier C never
  mutates).

Gates verified (scoped, not a package-wide claim -- gate:scope-note
applies, see docs/guides/agent-playbook.md#6c):
- ticket-scoped gates-native check: clean (exit 0)
- ticket-scoped gates-security check: clean (exit 0)
- ticket-scoped gates-fast check: ONE residual SCOPE001 finding naming
  src/frob/gates/_fix_engine_tier_b.py as outside T-1263's declared
  scope. This is a cross-ticket artifact of working T-1262 and T-1263 in
  the same worktree/branch (the ticket-scoped check diffs the whole
  branch against main, which now includes T-1262's own not-yet-landed
  commits) -- NOT a defect introduced by T-1263's own diff. T-1262's own
  scoped check (run before T-1263 started) was independently clean.
  Disclosed rather than silently worked around; the coordinator landing
  T-1262 first will make this resolve itself.

Evidence (pytest --collect-only confirmed, all 4 passing):
- tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch (accepts[0], accepts[2])
- tests/test_gates.py::TestFixEngineTierC::test_no_eligible_findings_returns_an_empty_list (accepts[1])
- tests/test_gates.py::TestFixEngineTierC::test_no_violations_at_all_returns_an_empty_list (accepts[1])
- tests/test_gates.py::TestFixEngineTierC::test_todo001_emitter_never_touches_any_file

Filed: none (T-1481 already existed on main before this ticket started).

Gates: ticket-scoped gates-native/gates-security clean; gates-fast's one
residual SCOPE001 is the disclosed cross-ticket artifact above, not
waived (it will resolve once T-1262 lands ahead of T-1263).

### Changed
```
 design/frob.strata                   |  21 +-
 docs/design/check-fix-engine.md      |  50 ++++
 src/frob/gates/_fix_engine_tier_b.py | 499 +++++++++++++++++++++++++++++++++++
 src/frob/gates/_fix_engine_tier_c.py | 167 ++++++++++++
 tests/test_gates.py                  | 304 +++++++++++++++++++++
 tickets.md                           | 154 ++++++++++-
 6 files changed, 1184 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierC::test_no_eligible_findings_returns_an_empty_list` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierC::test_no_violations_at_all_returns_an_empty_list` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierC::test_todo001_emitter_never_touches_any_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 849 warning(s), 758 waived
- error-findings: none (measured, zero errors)
