## Done report

The REG001 backlog is fully drained to ZERO (942 -> 0 across all four
registry files -- evasion, arch-checks, patterns, system-design -- every
entry now carries an honest handled_by / deferred / out_of_scope /
duplicate_of disposition, verified by the gate's own REG002-005 checks
finding no dangling references). With no legacy backlog left to hide a new
undispositioned entry in, all four Severity.WARN sites in
src/frob/gates/_registry_exhaustiveness.py::registry_gate are promoted back
to Severity.ERROR (REG001-005), and the interim frob:todo T-0426 debt-mark
comment block is removed. A new undispositioned entry, a dangling handled_by
(REG002), or a deferred-to-closed ticket (REG003) now HARD-FAILS the build --
the anti-lie core has teeth, as the drift-lock intended.

Verified: registry test suite green (17 tests), `frob check` shows 0 REG
findings on main (fully dispositioned) so the promotion adds zero errors --
main stays at its pre-promotion error count. The test that pinned WARN
(test_severity_is_warn) is renamed test_severity_is_error and asserts ERROR;
T-0343's evidence pointer updated to the renamed test.

Done at user request the moment the backlog hit zero (2026-07-20), exactly
per this ticket's acceptance ("after backlog==0, REG001-005 are ERROR").
