## Done report

Decision (ticket plan point 1): env gets its own THREAT004-delegated join
like net/fs, not a SYS100-extended-only kind. Matches the exact precedent
net just got in T-0771, and the ticket's own title says "wire" the join,
not merely decide about it.

Implementation (ticket plan points 2-3):
- _effects.py::_KIND_MAP gained env-read -> env.read, env-write ->
  env.write (same shape as fs-write/fs-read/net-connect/net-listen).
- _capability_modes.py::WIRED_MODE_FAMILIES gained "env" (FAMILY_MODES
  already defined env's read/write modes; only the wiring flag was
  missing).
- _selfconform.py::_UNWIRED_ENV_MODE_ALIASES (the transitional fold) is
  removed. Its two call sites (_extended_kinds_view, _all_kinds_view)
  simplified back to their fs/net shape. IMPORTANT CORRECTION mid-work:
  bare "env" could NOT be removed from _EXTENDED_KINDS wholesale --
  3 pre-existing registry entries (sys.exit/os._exit, signal.signal) are
  tagged capability_kind="env" despite being process-lifecycle/signal
  operations, not actual environment-variable access; only "env-read"/
  "env-write" moved out of _EXTENDED_KINDS into the _KIND_MAP join. Caught
  by the drift-lock test (TestExtendedKindsDriftLock.test_extended_kinds_
  is_disjoint_from_kind_map) failing on first attempt -- see that test's
  updated docstring for the disambiguation.
- _threat.py::DEFAULT_BENIGN_CAPABILITIES gained env.read/env.write
  BenignCapability entries (mirrors net.connect/net.listen's own T-0771
  addition) so THREAT005 does not fire on the newly-precise observed
  kinds. 13 entries now (was 11); TestCaughtByAuditExhaustive's count
  lock updated to match.
- _capability_registry.py::CAPABILITY_KINDS gained the dotted env.read/
  env.write spellings (registered so DEFAULT_BENIGN_CAPABILITIES's kind
  is known -- _validate_registry_kinds enforces this); CAPABILITY_MATRIX_
  EXCUSES gained 10 excuse entries (env.read/env.write x 5 languages,
  dotted spellings are never scanner-emitted directly, only produced by
  _KIND_MAP downstream -- same shape as net.connect/net.listen's own
  10-entry excuse block).

Real-code fallout: tests/unit/strata/test_effects.py's mutate fixture
started observing a real, previously-invisible env.read effect
(os.environ read building a subprocess env) once env's tier-2 join went
live -- added "env" to that test's declared may= set. The REAL repo
.strata model (design/frob.strata, node mutate) already declares `may
"env"` since T-0860, so this is a test-fixture-only fix, not a real
model gap.

Scope note: the ticket's declared scope named only _effects.py and
_capability_modes.py; the ticket's own body plan (points 2-3) requires
touching _selfconform.py, _threat.py, and _capability_registry.py plus
their test files to actually wire and verify the join -- extended scope
for all of these via `frob ticket scope --add` with reasons recorded in
tickets.md, same pattern T-1063/T-1073 used.

Ran tests/unit/strata/ + tests/unit/vet/ + tests/test_vet.py +
tests/test_capability_registry.py in full (all pass, no failures) after
the change. gates-fast/gates-native/gates-security/ruff all pass under
--ticket T-1075 except: the pre-existing TICK006 (T-0667's own
phantom-draft finding, unrelated, unchanged before/after -- same one
noted in T-1063/T-1073's Done reports), and REL002 (.frob-release.json
stale at 0.210.0 vs pyproject.toml's 0.211.0 -- confirmed pre-existing on
main itself, a land-owned-file artifact from T-1073's own land, not
something this worktree touched or can fix per the playbook's land-owned-
files rule).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_coarse_env_covers_union_of_modes` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestValidateRegistryKinds::test_every_threat_catalog_kind_is_registered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
