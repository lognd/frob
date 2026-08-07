## Done report

Changed:
- src/frob/strata/_supply_chain_boot.py (new module: REL394/REL395 ABI/
  ISA compat-window pair, REL396/REL397 boot-chain-attestation pair,
  SupplyChainBootReport/SupplyChainBootViolation,
  check_supply_chain_boot_obligations -- rule ids continue the REL39x
  block T-0960 started rather than opening REL4xx)
- src/frob/strata/__init__.py (re-export the new module's public symbols)
- src/frob/gates/__init__.py (_KNOWN_GATE_RULES: added REL394/REL395/
  REL396/REL397 only)
- docs/strata/reliability.md (new "REL39y: ABI-COMPAT-WINDOW +
  BOOT-ATTESTATION (T-0962)" section: obligation description, surface
  vocabulary, grammar-data-ceiling honesty note, waiver channel, See-also
  entries for the module and its test file)
- tests/unit/strata/test_supply_chain_boot.py (new, 12 tests: missing/
  clean/waived per obligation pair, plus unproven/discharged/uncheckable
  per obligation pair)
- docs/design/registry/system-design.yaml (re-pointed both T-0962 rows'
  disposition from deferred:T-0962 to handled_by:REL394 and
  handled_by:REL396 respectively)

Scope was widened from the ticket's original two-path declaration
(src/frob/strata/_supply_chain_boot.py, docs/strata/reliability.md) via
`frob ticket scope --add`, same shape as T-0960's own widen, to also
cover src/frob/strata/__init__.py, tests/unit/strata/
test_supply_chain_boot.py, src/frob/gates/__init__.py, and
docs/design/registry/system-design.yaml.

Design note: both obligation pairs are declaration-and-proof checks over
strata's own host/deploy vocabulary (KernelModel.nodes / bound source
text), not runtime kernel/firmware introspection -- this cannot observe
an actual compiled artifact's real ABI surface or an actual boot chain's
real measurement log, only whether a Node attr declaration and its
bound-code evidence exist. Disclosed directly in the module and
doc-section GRAMMAR-DATA CEILING notes.

Evidence:
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_compiled_artifact_node_without_compat_window_fires
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_discharged_and_non_compiled_artifact_nodes_clean
- tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_waiver_discharges_finding
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_boot_chain_stage_node_without_attestation_fires
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_discharged_and_non_boot_chain_stage_nodes_clean
- tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_waiver_discharges_finding
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
All 12 observed passing: `uv run pytest tests/unit/strata/test_supply_chain_boot.py -p no:cacheprovider -q` -> "............ [100%]".

Filed: T-0965 "COV002 scope-coverage grace window missing for
same-diff closed ticket" (bug) -- disclosed below.

Gates: `uv run frob check --ticket T-0962` chunked loop (lint/static/
gates-native/gates-security) all pass with 0 errors. gates-fast reports
30 COV002 errors, but ALL 30 are against T-0960's already-closed files
(src/frob/strata/_process_bounds.py, tests/unit/strata/
test_process_bounds.py) -- NONE against this ticket's own
_supply_chain_boot.py/test_supply_chain_boot.py, confirmed by filtering
the `--json` gates-fast output. Root cause: T-0960 covered those symbols
by ticket SCOPE (one `frob:ticket T-0960` directive on the module's main
entrypoint, matching this repo's established one-directive-per-module
convention), and `_bound_to_open_ticket`'s T-0214/T-0320/T-0590 same-diff
grace window only covers a DIRECT `frob:ticket` edge closing in-diff --
there is no equivalent grace for SCOPE-based coverage
(`_open_scopes`/`_scope_covers`) when its covering ticket closes to DONE
within the same unlanded branch diff. This is a real gap in frob's own
COV002 gate, not something T-0962's own diff introduced or something in
T-0962's declared scope to fix -- filed as T-0965 rather than
silently worked around or fixed out-of-scope.

### Changed
```
 docs/design/registry/system-design.yaml  |   4 +-
 docs/strata/reliability.md               |  99 +++++++
 src/frob/gates/__init__.py               |  12 +
 src/frob/strata/__init__.py              |  18 ++
 src/frob/strata/_process_bounds.py       | 432 +++++++++++++++++++++++++++++++
 tests/unit/strata/test_process_bounds.py | 323 +++++++++++++++++++++++
 tickets.md                               | 206 ++++++++++++++-
 7 files changed, 1091 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_compiled_artifact_node_without_compat_window_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_discharged_and_non_compiled_artifact_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_boot_chain_stage_node_without_attestation_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_discharged_and_non_boot_chain_stage_nodes_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 5002 warning(s), 220 waived
- error-findings: none (measured, zero errors)
