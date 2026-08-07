## Done report

Audited EVERY built-in out-of-scope/benign-capability entry the repo ships
under `src/frob/strata/` -- not a sample. Enumerated the full universe by
grepping every `OutOfScopeEntry(`/`BenignCapability(`/`OutOfScopeRegulation(`
construction across `src/frob/strata/*.py` and reading each one's `reason`/
`caught_by` pair by hand:

- `_threat.py::CWE_TOP_25_OUT_OF_SCOPE` -- 16 `OutOfScopeEntry` rows
- `_threat.py::QUALITY_OUT_OF_SCOPE` -- 5 `OutOfScopeEntry` rows
- `_threat.py::DEFAULT_BENIGN_CAPABILITIES` -- 9 `BenignCapability` rows
- `_krb_movement.py::KRB_MOVEMENT_OUT_OF_SCOPE`,
  `_host_isolation.py::COMPROMISED_OWNER_OUT_OF_SCOPE` -- both empty
  tuples by design (module comments already explain why: no
  `OutOfScopeEntry` rows are needed for either class)
- `_compliance.py::COMPLIANCE_OUT_OF_SCOPE` -- 1 `OutOfScopeRegulation` row

Total audited: 31 entries (21 `OutOfScopeEntry` + 9 `BenignCapability` + 1
`OutOfScopeRegulation`). All 31 already carried a `caught_by` (mandatory
since T-0381/pydantic `Field(min_length=1)`); the audit's job was
confirming each is a REAL compensating-control reference or a
substantively reasoned `"none -- ..."` disclosure, not a placeholder --
7 name a real control (e.g. `CWE-78 in CWE_CATALOG`, `PII010`, `frob vet's
dependency-supply-chain scan`), 24 honestly disclose "none" with a
specific, non-generic reason (a named missing kernel primitive --
buffer/bounds model, endpoint/route + authz-boundary concept,
resource-budget model, etc -- never a bare "none" or "TODO"). Populated:
0 needed populating (already done by T-0381's authoring pass); reasoned-
none confirmed substantive: 24; real-control confirmed resolving: 7.

Checkable proof added (not a one-off manual read -- a test that re-runs
this audit mechanically and locks the count so a future add without a
real `caught_by` fails the build):
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive` -- two
  tests. `test_every_shipped_entry_has_a_substantive_caught_by` asserts
  the audited-entry count is exactly 21+9=30 (the security family) and
  that no entry's `caught_by` (normalized) is a bare placeholder
  (`_CAUGHT_BY_PLACEHOLDERS = {"none","todo","tbd","n/a","na","fixme",
  "unknown","?",""}`) and that every "none"-prefixed entry has text beyond
  the bare marker. `test_every_shipped_entry_passes_real_production_
  verification` runs the SAME corpus through `check_caught_by_integrity`
  with the REAL `frob.gates.known_gate_rule_ids()` (not the default-empty
  set the pre-existing `test_clean_default_catalogs_have_no_gaps` uses),
  proving it passes the actual production verification path.
- `tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive` --
  the compliance-family mirror: asserts `COMPLIANCE_OUT_OF_SCOPE` has
  exactly 1 entry, is not a placeholder, and passes
  `check_regulation_caught_by_integrity` with the real
  `known_gate_rule_ids()`.

Doc update (in scope, `docs/design/registry/`): `EXHAUSTIVENESS-GATE.md`'s
disposition-grammar section claimed T-0382's `caught_by` verification
mechanism "does not exist yet in this build" -- stale now that T-0382 is
done and this ticket audited it exhaustively. Corrected the text to say
what now exists (T-0382/T-0383) and to name, precisely, the ONE thing
still not wired: the registry YAML's own `out_of_scope:<reason>`
disposition string (a separate surface from `strata`'s model objects,
consumed by `frob.gates._registry_exhaustiveness`, outside this ticket's
declared scope) is not yet routed through that verification.

Filed rather than fixed (requires touching `src/frob/gates/
_registry_exhaustiveness.py`, outside this ticket's scope):
T-0680 (ex-draft, id lost at land) -- "registry: route out_of_scope disposition reason
through T-0382 caught_by verification".

Test results (measured):
- `uv run pytest tests/unit/strata/test_threat.py tests/unit/strata/
  test_compliance.py -n0` -> 158 passed.
- `uv run pytest tests/unit/strata/ -n0` -> all green except the single
  documented pre-existing failure
  `test_selfconform.py::TestRealGateGreen::
  test_repo_design_and_declarations_are_self_conformant` (SYS102
  unmodeled code `src/frob/registry`) -- called out as a known
  pre-existing failure in the dispatch, not caused by this change.

Gates: `uv run frob check --ticket T-0383` -> 0 errors, 395 warnings, 190
waived (clean; the one transient `gate:PRE` FAIL from adding scope after
`ticket start` was cleared by `frob ticket sweep T-0383` before this
final run).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_passes_real_production_verification` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_passes_real_production_verification` (pytest node id, verified passing when recorded)
