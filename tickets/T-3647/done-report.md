## Done report

Fixed the DRIFT002 regression T-1684's post-land sweep filed against
T-3593's land: 4 src/frob/vet/*.py files carried stale `frob:tests`
directive citations still naming `tests/test_vet.py::Class.method`
after that file was split into `tests/vet_suite/*.py` (the split
verb's reference scanner covers Python import/call sites, not
directive comments -- a known, documented gap). Repointed each
citation by class-name lookup against the real `tests/vet_suite/`
package layout: `TestNeedleMatchesResolvedTokenBoundary` and
`TestOperationEntryMatchesFallthrough` ->
`test_opaque_indirection.py`, `TestCapabilityScan` ->
`test_capability_scan_python.py`, `TestFingerprintBindingResolution`
-> `test_fingerprint.py`, `TestSupplyChain*` -> `test_supply_chain.py`
(`_capability_core.py`, `_capability_python.py`, `_capability_scan.py`,
`_supplychain.py`); also fixed one bare-path prose mention in
`_capability_scan.py`. The longer `tests/vet_suite/` paths pushed
several single-line `frob:tests` comments past E501's 88-column limit;
rewrapped using this codebase's existing backslash-continuation
convention.

Verified: `ruff check` clean on all 4 touched files. `pytest
tests/vet_suite -q` (the full destination suite these citations point
into) green, 463/463.

### Changed
src/frob/vet/{_capability_core,_capability_python,_capability_scan,_supplychain}.py
