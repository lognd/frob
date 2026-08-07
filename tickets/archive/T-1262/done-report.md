## Done report

Built the Tier-B transactional fix engine per docs/design/check-fix-engine.md's
"Transaction / rollback model" section: new src/frob/gates/_fix_engine_tier_b.py
with TierBFix/FixRolledBack models, TIER_B_HANDLERS: dict[str, TierBHandler]
(mirroring _fix_engine.TIER_A_HANDLERS's call shape), and apply_tier_b_fixes,
the apply-verify-commit-or-rollback engine.

Design decisions:
- Per-fix baseline: since a TierBHandler applies its own mutation before
  returning (same apply-then-report contract as Tier A), the engine cannot
  see a genuine pre-fix gate state directly. _pre_fix_baseline computes a
  TRUE pre-fix baseline via a temporary revert-measure-restore around the
  fix's own backup bytes (write backup, run gate_runner, restore post-fix
  bytes) rather than diffing two post-fix measurements, which would always
  read as clean by construction.
- gate_runner/test_runner are injectable, defaulting to the real
  run_gates/subprocess-pytest pair -- mirrors fix_fmt001_directive_wrap's
  only_paths "default preserves real behavior, override is test-only" shape.
  This lets this module's own tests prove the commit/rollback decision logic
  deterministically without spawning a real run_gates()/pytest per test.
- Reference handler: fix_tierbdemo001_marker_rewrite is a SYNTHETIC handler
  (per the ticket's own acceptance note permitting this) keyed to a
  placeholder "TIERBDEMO001" id that is deliberately never a real frob check
  rule -- proves the full snapshot-apply-verify-commit-or-rollback path
  end-to-end without depending on any real gate rule's shape. A real Tier-B
  handler is left as a follow-up, out of this ticket's declared scope
  (filed T-1643, T-1642's own follow-up; real id
  after land).
- Verification is sequential, one TierBFix at a time (never batched), per
  docs/design/check-fix-engine.md's own "a rollback never has to bisect more
  than one fix" rule -- test_multiple_fixes_verified_sequentially_not_batched
  asserts two separate before/after gate_runner call pairs for two fixes,
  never one shared call.
- apply_tier_b_fixes/TIER_B_HANDLERS/_real_gate_runner/_real_test_runner/
  fix_tierbdemo001_marker_rewrite are not reachable from any real --fix CLI
  invocation yet (T-1481 wires that, alongside Tier A's own CLI wiring, per
  T-1138/T-1260's precedent split) -- each site carries a
  frob:waive WIRE001 ... follow_up="T-1481" naming that open ticket.

Scope was extended twice via frob ticket scope T-1262 --add:
- docs/design/check-fix-engine.md (AFFECT001: the frob:doc anchor this
  module's symbols point to needed a same-diff update -- added a
  "T-1262 implementation note" subsection describing what was actually built)
- design/frob.strata (SELFAUDIT001 SYS100/SYS104: the new module's fs.read/
  fs.write capability effects and public interface= symbols needed declaring
  on the gates node; the new TestFixEngineTierB class needed declaring on the
  testsuite node; both nodes also needed a frob:ticket T-1262 edge for COV002)

Gates verified (scoped, not a package-wide claim -- gate:scope-note applies,
see docs/guides/agent-playbook.md#6c):
- frob check --ticket T-1262 --only gates-fast: clean (exit 0)
- frob check --ticket T-1262 --only gates-native: clean (exit 0)
- frob check --ticket T-1262 --only gates-security: clean (exit 0)

Evidence (pytest --collect-only confirmed, all 5 passing):
- tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed (accepts[0])
- tests/test_gates.py::TestFixEngineTierB::test_regressing_fix_is_rolled_back_byte_for_byte (accepts[1])
- tests/test_gates.py::TestFixEngineTierB::test_new_error_violation_after_fix_rolls_back (accepts[1])
- tests/test_gates.py::TestFixEngineTierB::test_multiple_fixes_verified_sequentially_not_batched (accepts[2])
- tests/test_gates.py::TestFixEngineTierB::test_no_marker_files_is_a_no_op

Filed: none (T-1481, the CLI-wiring follow-up, already existed on main before
this ticket started -- cited via frob:waive WIRE001 follow_up, not newly
filed).

Gates: frob check --ticket T-1262 --only gates-fast/gates-native/gates-security
all clean; no waives left un-reasoned.

### Changed
```
 design/frob.strata                   |  13 +-
 docs/design/check-fix-engine.md      |  31 +++
 src/frob/gates/_fix_engine_tier_b.py | 499 +++++++++++++++++++++++++++++++++++
 tests/test_gates.py                  | 206 +++++++++++++++
 tickets.md                           |  34 ++-
 5 files changed, 776 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_regressing_fix_is_rolled_back_byte_for_byte` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_new_error_violation_after_fix_rolls_back` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_multiple_fixes_verified_sequentially_not_batched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_no_marker_files_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 836 warning(s), 756 waived
- error-findings: none (measured, zero errors)
