## Done report

Found on ticket-start that the ticket's own premise was partly stale:
Tier-A (apply_tier_a_fixes) already HAD a CLI entry point -- T-1260 wired
it (--fix flag in _cli_parsers/_check.py, _apply_tier_a_and_reverify in
check_runner.py, both confirmed present and working before this ticket
touched anything). The doc's "Status quo" section still claimed
otherwise, with a `frob:until T-1481` binding -- stale prose the doc's
own deeper implementation-note sections (T-1262/T-1263 notes) already
contradicted: those sections were explicit that Tier-B (apply_tier_b_
fixes, T-1262) and Tier-C (apply_tier_c_fixits, T-1263) were the actually
unwired engines, both carrying `frob:waive WIRE001 ... follow_up="T-1481"`
markers naming this exact ticket as their wiring follow-up.

So the real, still-live work was: wire Tier-B and Tier-C into --fix, not
Tier-A (already done). Did that:

- `_apply_tier_a_and_reverify` (src/frob/app/check_runner.py) now also
  calls `apply_tier_b_fixes` (folding committed fixes into the same
  `fixed` list Tier-A populates, per the design doc's own "a committed
  Tier-B fix reports identically to Tier A" contract, and rolled-back
  fixes into `fix_report["rolled_back"]`) and `apply_tier_c_fixits`
  (always run over the post-Tier-A/B gates state -- a second raw
  `frob.gates.run_gates` call, since Tier C's `TierCEmitter` dispatches
  on `Violation.rule`, a shape `_run_gates`'s own `Diagnostic`/`ToolResult`
  conversion does not carry -- into `fix_report["fixits"]`).
- Removed seven now-stale `frob:waive WIRE001 ... follow_up="T-1481"`
  waivers on `apply_tier_b_fixes`/`apply_tier_c_fixits`'s own entry
  points and their `_real_gate_runner`/`_real_test_runner`/`emit_todo001_
  fixit` private helpers -- all now genuinely reachable from a real
  `frob check --fix` invocation, not just from each module's own tests.
- `_fix_report_text` (human-readable summary) now renders real
  rolled-back/fix-it lines instead of the two fields always being empty.
- docs/design/check-fix-engine.md: removed the stale "not yet wired"
  Status-quo claim and its `frob:until T-1481` marker (replaced with a
  factual "is a runnable command" summary of all three tiers), and
  updated the T-1260/T-1262/T-1263 implementation notes to describe the
  now-real Tier-B/C CLI wiring instead of "not wired here."

Safety check before wiring Tier B for real: `TIER_B_HANDLERS` currently
holds only the SYNTHETIC `TIERBDEMO001` reference handler (no real
production Tier-B handler exists yet, per the doc's own disclosure) --
confirmed its trigger (`# frob:tierbdemo <replacement>` marker text)
never appears anywhere in this repo's own source, so wiring it live is a
verified no-op on every real `--fix` run today, not a live handler
silently mutating something unexpected. Proved this directly rather than
assuming it via `test_tierbdemo_marker_is_committed_via_tier_b_and_
reported_fixed` (a real end-to-end marker-rewrite-and-commit test, not a
mock).

New tests (tests/test_check_runner.py): a Tier-B marker fix committed and
reported end-to-end (real rewrite, no mocking of apply_tier_b_fixes
itself), and a Tier-C TODO001 fixit included in fix_report["fixits"]
(frob.gates.run_gates stubbed to return a canned Violation, since TODO001
itself is diff-driven and needs a git base ref this unit-level test does
not set up -- the CLI-wiring reachability is what this test proves, not
emit_todo001_fixit's own rewrite logic, which tests/test_gates.py::
TestFixEngineTierC already covers directly).

### Changed
```
 docs/design/check-fix-engine.md      | 50 +++++++++++--------
 src/frob/app/check_runner.py         | 86 +++++++++++++++++++++++---------
 src/frob/gates/_fix_engine_tier_b.py | 15 ++----
 src/frob/gates/_fix_engine_tier_c.py | 12 +----
 tests/test_check_runner.py           | 97 +++++++++++++++++++++++++++++++++---
 tickets/T-1481/done-report.md        | 79 +++++++++++++++++++++++++++++
 tickets/T-1481/ticket.md             | 42 +++++++++++++++-
 7 files changed, 308 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_no_tier_a_findings_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_finding_with_no_tier_a_handler_is_never_mutated_or_claimed` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_tierbdemo_marker_is_committed_via_tier_b_and_reported_fixed` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_tier_c_fixit_from_a_todo001_violation_is_included` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestResultAsJsonWithFix::test_fix_report_adds_fix_key_with_fixits_and_rolled_back_present` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestResultAsJsonWithFix::test_no_fix_report_is_byte_identical_to_plain_as_json` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestFixReportText::test_summary_line_reports_three_counts` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 1 error(s), 620 warning(s), 731 waived
- error-findings: PRE001@tickets/T-1481
