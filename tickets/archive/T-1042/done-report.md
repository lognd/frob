## Done report

Re-measured before touching anything: `frob check --only registry --json`
showed the live REG008 count had moved from the coordinator's cited ~134
to 136 (17 compliance.yaml, 4 system-design.yaml, 115 check-coverage.yaml)
at start of this ticket.

Worked in the ordered batches the dispatch specified:

1. system-design.yaml (4 findings, SDC-13 REL39x remainder): all 4
   verified as correct attributions against T-0960/T-0962's own module
   docstrings (which explicitly named these entries as the reconciliation
   target when those tickets were filed). Added frob:enforces edges to
   check_process_bounds_obligations (REL390/391/392/393) and
   check_supply_chain_boot_obligations (REL394/395/396/397). 0 flips.

2. check-coverage.yaml (115 findings, one CHK-GATE-<RULE> entry per known
   gate rule id): verified each by locating the real Violation-
   constructing site (or its public dispatch entrypoint, following this
   file's own established per-rule/per-entrypoint placement idiom) for
   every rule id -- REL2xx-REL39x families in src/frob/strata/*.py
   (mirroring T-0958's SDC-* placement precedent exactly), SYS100-102/
   SYS200-204 (_selfconform.py/_contention.py/_access.py), THREAT001-006/
   COMPLIANCE001-004/HOST001-002/HOST-BLAST/KRB001-004/LINT001-005/
   PII001-004/PII011-012/PARSE001-002/PERF008-009/RELWAIVE002/
   SYSWAIVE002 (strata), plus the gates/**.py-owned families (SEC004,
   DOC005/007, DEAD001, FMT001, AFFECT001/002, DEC000/003, EXHAUST001/002,
   PROTO004, TICK005, DUP003, COMPLIANCE005/006, REG012, REL002, SCOPE002,
   FFI001/002, ARCH101/102/103 -- this last one closing T-0728's own
   disclosed land obligation). All 115 verified as correctly attributed
   (each rule id's constructing code genuinely emits that literal rule) --
   0 flips/downgrades needed; this registry is a structural coverage
   denominator (one entry per real, live `_KNOWN_GATE_RULES` member), not
   a semantic-judgment mapping like arch-checks.yaml was in T-1020, so
   misattribution risk here was inherently low.

3. compliance.yaml (17 findings, all CMPL_REGISTRY_UNIT_IDS entries under
   handled_by:COMPLIANCE005): re-merged main immediately before this
   batch (T-1019's REG011-reason rewrite in the same file had already
   landed cleanly by then, no conflict). All 17 verified against T-0833's
   own re-disposition to COMPLIANCE005/compliance_gate -- correct
   attribution, 0 flips. Added frob:enforces edges to compliance_gate.

Real-repo-scan regression test per registry file added to
tests/test_registry_exhaustiveness.py (TestSystemDesignReg008BurnDown,
TestCheckCoverageReg008BurnDown, TestComplianceReg008BurnDown), same
shape as T-1020's TestArchChecksReg008BurnDown -- each runs registry_gate
over this repo's own live registry + graph and asserts zero REG008 for
that file.

Before: 136 live REG008 findings (17 + 4 + 115).
After: 0 live REG008 findings repo-wide (`frob check --only registry`
gate-summary: 0 errors).

Totals: 0 dispositions flipped/downgraded (every handled_by attribution
verified correct), ~140 frob:enforces edges added across
src/frob/gates/**, src/frob/strata/**, src/frob/perf/_loop_effects.py,
src/frob/perf/_ratchet.py.

A second `git merge main` right before landing (per playbook section 9's
deletion-filter check) picked up a concurrently-landed OPAQUE001 gate
(src/frob/gates/_opaque.py) whose check-coverage.yaml CHK-GATE-OPAQUE001
entry was already dispositioned handled_by:OPAQUE001 -- added its
frob:enforces edge too (1 more edge, 0 flips) so REG008 stayed at zero
against the final merged tree, not just the tree as of the compliance.yaml
batch.

Pre-existing, out-of-scope gate:COV/gate:ARCH/gate:PERF findings surfaced
by `frob check --ticket` (gitlog/arch/_models.py/render/process/parsers
COV001s, arch/_cpp_mayraise.py ARCH001/PERF003/004, several PERF005/008
recursion/loop findings) are present on a bare `frob check` with no
--ticket filter too, on this same merged tree -- confirmed unrelated to
this ticket's diff, left untouched (not this ticket's scope, filing a
cleanup ticket would need naming an owner and is out of this dispatch's
ask).

### Changed
```
 src/frob/gates/__init__.py                 |  32 +++++
 src/frob/gates/_arch.py                    |  11 +-
 src/frob/gates/_dead_symbols.py            |   1 +
 src/frob/gates/_docblocks.py               |   1 +
 src/frob/gates/_docptr.py                  |   1 +
 src/frob/gates/_exhaustive_handling.py     |   2 +
 src/frob/gates/_ffi_boundary.py            |   2 +
 src/frob/gates/_parse_failures.py          |   2 +
 src/frob/gates/_pii_structural.py          |   2 +
 src/frob/gates/_protocol_summary.py        |   1 +
 src/frob/gates/_registry_exhaustiveness.py |   1 +
 src/frob/gates/_secrets.py                 |   1 +
 src/frob/perf/_loop_effects.py             |   1 +
 src/frob/perf/_ratchet.py                  |   1 +
 src/frob/strata/_access.py                 |   1 +
 src/frob/strata/_audit.py                  |   1 +
 src/frob/strata/_backpressure.py           |   2 +
 src/frob/strata/_circuit_breaker.py        |   2 +
 src/frob/strata/_clock_ordering.py         |   3 +
 src/frob/strata/_compliance.py             |   4 +
 src/frob/strata/_contention.py             |   5 +
 src/frob/strata/_delivery_semantics.py     |   2 +
 src/frob/strata/_distributed_txn.py        |   2 +
 src/frob/strata/_fallback.py               |   2 +
 src/frob/strata/_host_isolation.py         |   2 +
 src/frob/strata/_interactive_cost.py       |   2 +
 src/frob/strata/_krb_movement.py           |   4 +
 src/frob/strata/_lint.py                   |   5 +
 src/frob/strata/_message_schema.py         |   2 +
 src/frob/strata/_observability.py          |   3 +
 src/frob/strata/_pii.py                    |   4 +
 src/frob/strata/_process_bounds.py         |   6 +
 src/frob/strata/_reliability.py            |   4 +
 src/frob/strata/_retry.py                  |   3 +
 src/frob/strata/_selfconform.py            |   3 +
 src/frob/strata/_shared_state.py           |   1 +
 src/frob/strata/_slo.py                    |   2 +
 src/frob/strata/_spof.py                   |   1 +
 src/frob/strata/_ssot.py                   |   2 +
 src/frob/strata/_starvation.py             |   4 +
 src/frob/strata/_supply_chain_boot.py      |   6 +
 src/frob/strata/_sync_depth.py             |   1 +
 src/frob/strata/_threat.py                 |   6 +
 src/frob/strata/_txn.py                    |   2 +
 src/frob/strata/_waive.py                  |   7 ++
 tests/test_registry_exhaustiveness.py      | 108 ++++++++++++++++
 tickets.md                                 | 192 +++++++++++++++++++++++++++++
 47 files changed, 448 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestSystemDesignReg008BurnDown::test_no_reg008_findings_for_system_design_yaml` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestComplianceReg008BurnDown::test_no_reg008_findings_for_compliance_yaml` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
