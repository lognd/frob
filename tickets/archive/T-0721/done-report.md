## Done report

T-0721 reconciled all 39 deferred:T-0721 SC-* supply-chain.yaml entries:

- 13 entries have a real, already-live enforcing detector in
  src/frob/vet/ (VET-JS003 typosquat distance, VET002 undeclared install-
  hook/network capability, VET004 obfuscation ensemble, VET005 osv-scanner
  adapter, VET011 quarantine window) or in src/frob/gates/_opaque.py
  (OPAQUE001's deny-by-default runtime-opacity check, which already covers
  native-extension imports and Rust proc-macro/build.rs constructs). None
  of these could be flipped to handled_by: here -- REG002 verifies
  handled_by against `_KNOWN_GATE_RULES | st.rule_ids`
  (src/frob/gates/__init__.py), which does not yet include the VET-family
  rule namespace, and widening it is src/frob/gates/** work outside this
  ticket's declared scope (src/frob/vet/**, docs/design/registry/
  supply-chain.yaml). Filed T-1087 (a real, queued, non-done
  ticket scoped to src/frob/gates/**) with the full 13-entry mapping
  already worked out, and left all 13 as
  deferred:T-1087 rather than a bare re-deferral to this
  ticket -- an honest "detector exists, wiring is the remaining step"
  disposition, not a re-punt.
- 5 entries (SC-ATTACK-UNPINNED-DEPENDENCIES, SC-DETECTION-PYTHON-
  INSTALL-ARTIFACTS, SC-DETECTION-NPM-NON-REGISTRY-SOURCE, SC-DETECTION-
  UNPINNED-CI-ACTION, SC-DETECTION-OPAQUE-BINARY-ARTIFACT) are tagged
  checkability:['statically-detectable'] ONLY (no requires-external-data,
  no process-only) but have no detector today -- genuinely buildable,
  filed as T-1088 (scope src/frob/vet/**) rather than
  dispositioned away.
- 21 entries get reasoned out_of_scope:none dispositions, each naming the
  specific missing external-data/live-fetch integration (registry-
  namespace authority, maintainer-account history, GitHub metadata,
  SLSA/Sigstore/in-toto attestation verification, live tarball/manifest
  diffing against the registry, CI-provider APIs) or, for
  SC-ATTACK-PROTESTWARE, the checkability tag's own 'advisory'/subjective-
  intent nature.
- 2 entries (SC-ATTACK-TRANSITIVE-BLINDNESS, SC-DEFENSE-CAPABILITY-
  SANDBOXING) already carried a reasoned out_of_scope disposition from a
  prior pass (process-only checkability) and were left untouched.

`frob check --only registry` is clean (0 errors, 0 REG002/REG008
warnings for supply-chain.yaml). No src/frob/vet/ code was changed -- this
ticket's actual deliverable is the registry disposition sweep plus the two
follow-up tickets that carry the real remaining work forward honestly
rather than silently dropping it.

### Changed
```
 tickets.md | 129 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 127 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 925 warning(s), 419 waived
- error-findings: none (measured, zero errors)
