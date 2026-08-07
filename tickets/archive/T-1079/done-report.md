## Done report

SYS103's unrestricted scan against design/frob.strata surfaced 264 real
unbound-but-capable findings under tests/**, scripts/**, frob-core/src/**,
strata-core/src/** (measured directly via a script that bypasses
_coverage_totality_scan_prefix's _PACKAGE_ROOT restriction -- 262 in
tests/**, 1 each in scripts/bump_version.py, frob-core/src/lib.rs,
strata-core/src/lib.rs).

Closed by modeling, not excluding: all four trees genuinely exercise real
capabilities, so a reasoned exclusion would have been dishonest. Added 4
nodes to design/frob.strata:

- testsuite (code "tests/**"): may env/eval/exec/fetch_url/ffi/fs/
  fs-read/install-hook/net/sql/deserialize -- the full observed kind set
  under tests/**, folding scanner-only hyphenated aliases (fs-write,
  env-read/env-write, net-connect) to the same bare kind every other node
  in this file already declares.
- scripts_ops (code "scripts/**"): may fs/fs-read (bump_version.py's
  pyproject.toml/CHANGELOG.md read-then-rewrite).
- strata_core_native (code "strata-core/src/**"): may ffi.
- frob_core_native (code "frob-core/src/**"): may ffi.

Re-ran the unrestricted SYS103 scan (script bypassing
_coverage_totality_scan_prefix) against the updated model: 0 violations
(was 265 before this ticket's own re-measurement -- the ticket's own
264-count plus 1 the T-0667 measurement rounded off). Same result
confirmed via check_self_conformance covering SYS100/SYS101/SYS102/SYS103
together, not just SYS103 in isolation.

Adding testsuite's exec/eval/sql/fetch_url/net/deserialize capabilities
drags in 4 THREAT003 owasp-top-10 discharge obligations (CWE-78/89/918/
502); discharged with `assume ... noflow registry -> testsuite` claims,
same shape vet's own CWE-89/CWE-918/CWE-502 claims already use -- verified
by direct grep that no test file feeds a registry-response byte directly
into subprocess/eval/sql/pickle.load without an intervening fixture/mock
boundary.

Scope note: tests/system/test_frob_self_model.py and
tests/golden/frob_export_{k8s.yaml,seccomp.json} are NOT in T-1079's
declared scope glob, but the dispatch instructions explicitly required
"Keep the self-model test suite (test_every_claim_proves + goldens)
green; regenerate goldens only for genuine model growth, never to paper
over a red" -- both files hardcode node/flow/claim counts and rendered
exports that mechanically move with any design/frob.strata node
addition (same pattern the file's own T-0440/T-0967 docstring history
already documents for prior node additions). Updated node/flow/claim
counts (16->20 nodes, 44 flows unchanged, 27->31 claims) and regenerated
the k8s netpol / seccomp goldens (iam golden unchanged) to match --
genuine model growth, not a red papered over (verified: the growth is
exactly the 4 new nodes and their 4 discharge claims, nothing else moved).

Live gate note: _coverage_totality_scan_prefix (src/frob/strata/
_selfconform.py) itself is unchanged and out of this ticket's scope --
the production SELFAUDIT001 gate still runs the _PACKAGE_ROOT-restricted
SYS103 scan. The model now covers the whole repo with zero findings
either way, but widening the LIVE gate to drop the restriction (so it
actually consults that coverage) is disclosed follow-up, filed as
T-1091.

Filed: T-1091 (drop SYS103's _PACKAGE_ROOT restriction now that
the self-model covers tests/scripts/native trees).

### Changed
```
 design/frob.strata                    | 120 ++++++++++++++++++++++++++++++++++
 docs/modules/strata.md                |  52 ++++++++++-----
 tests/golden/frob_export_k8s.yaml     |  56 ++++++++++++++++
 tests/golden/frob_export_seccomp.json |  88 +++++++++++++++++++++++++
 tests/system/test_frob_self_model.py  |  50 ++++++++++++--
 tests/unit/strata/test_selfconform.py |  36 ++++++++++
 tickets.md                            |  40 +++++++++++-
 7 files changed, 419 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 573 warning(s), 419 waived
- error-findings: PRE001@tickets/T-1079
