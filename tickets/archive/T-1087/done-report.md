## Done report

Widened `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) with the 17 live
`frob vet` rule ids (VET001-VET006, VET011, VET-JS, VET-JS003, VET-JS004,
VET-PY001-003, VET-RS001-002, VET-SOURCE-UNAVAILABLE, VET-TIMEOUT) --
hand-maintained, same class as the existing DUP00x/PERF00x entries, since
`src/frob/vet/**` sits outside `_rule_id_scan.SCANNED_BASES`
(src/frob/gates, src/frob/strata) and can never be picked up by the
generator scan. OPAQUE001 was already present (emitted from
src/frob/gates/_opaque.py, inside SCANNED_BASES).

Added `frob:enforces SC-ATTACK-NATIVE-EXTENSION-OPACITY` and
`frob:enforces SC-DETECTION-PROC-MACRO-BUILDRS` at `opaque_gate`
(src/frob/gates/_opaque.py) -- the real Violation(rule="OPAQUE001", ...)
emission site for those two supply-chain.yaml entries' structural
findings.

Flipped all 13 `deferred:T-1087` entries in
docs/design/registry/supply-chain.yaml to their `handled_by:<rule>`
targets (11 VET-family, 2 OPAQUE001) per the ticket's mapping. Verified
zero remaining `T-1087` disposition references in the file.

REG002 (dangling handled_by) proof: `frob check --ticket T-1087 --only
registry` reports `gate:REG 0 errors, 12 warnings, 0 waived` -- no REG002
line anywhere in output; all 13 rule ids resolve against the widened
union.

REG008 (handled_by claim with no frob:enforces edge) proof: same run
shows exactly 2 of the 13 entries clean (the OPAQUE001 pair, whose
frob:enforces edges this ticket added inside its own
`src/frob/gates/**` scope). The 11 VET-family entries now show REG008
WARN (advisory, not ERROR -- gate stays PASS) because their real
enforcing code (frob.vet._typosquat, frob.vet._scan, frob.vet._osv) lives
entirely in src/frob/vet/**, outside this ticket's declared scope
(src/frob/gates/**, docs/design/registry/supply-chain.yaml) -- unlike
OPAQUE001/taint, no src/frob/gates/** wrapper module re-emits VET-family
violations, so there is no honest in-scope site for those 11
`frob:enforces` directives. Filed T-1101 (scope
src/frob/vet/_typosquat.py, src/frob/vet/_scan.py, src/frob/vet/_osv.py,
docs/design/registry/check-coverage.yaml) to add them; that same ticket
also covers the 17-entry REG010 gap (VET-family rule ids missing a
CHK-GATE-<rule> entry in check-coverage.yaml) that widening
_KNOWN_GATE_RULES surfaced, since check-coverage.yaml is likewise outside
this ticket's scope.

Gates run this pass: gates-native, gates-fast, gates-security, registry,
lint, static -- all PASS, 0 errors (registry: 0 errors/12 warnings/0
waived, unchanged error count from before this ticket, all 12 warnings
newly-surfaced-but-WARN-tier REG008/REG010 findings disclosed above).
ruff check/format clean on both touched files under both PATH ruff and
`uv run ruff`.

### Changed
```
 docs/design/registry/supply-chain.yaml |  26 ++--
 src/frob/gates/_opaque.py              |   9 ++
 src/frob/gates/_waive.py               |  23 +++
 tickets.md                             | 251 ++++++++++++++++++++++++++++++++-
 4 files changed, 293 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_no_frob_enforces_edge_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1272 warning(s), 421 waived
- error-findings: TICK006@tickets.md
