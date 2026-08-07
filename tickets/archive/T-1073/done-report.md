## Done report

Decision: FAMILY_MODES's "proc" family stays "proc" -- NOT renamed to
match the vet registry's pre-existing "exec" capability_kind.

Reasoning: the fs/net families already establish the precedent this
decision follows -- the vet registry's raw SCANNER kind is a DIFFERENT,
independently-registered spelling from the mode-qualified FAMILY_MODES
vocabulary (registry "fs-write"/"net-connect" vs FAMILY_MODES "fs"/"net"
family + "write"/"connect" mode), bridged only at the tier-2 join
(frob.strata._effects._KIND_MAP), never by making the strings equal.
proc/exec is the identical shape, just with a more divergent spelling
("exec" bears no textual relation to "proc" at all, unlike "fs-write" ->
"fs"). Renaming the registry's "exec" to "proc" in place would touch 14+
files (CWE_CATALOG, DEFAULT_BENIGN_CAPABILITIES, docs, every sibling-repo
.strata declaration already spelling the observed kind "exec") -- real
migration work that belongs to whichever ticket actually BUILDS proc's
tier-2 join, not a naming-decision ticket scoped to 2 files.

Implemented the decision as a statically-discoverable bridge rather than
just a comment: added `PROC_FAMILY_SCANNER_KIND: Final[str] = "exec"` to
_capability_modes.py (exported in __all__), cross-referenced from both
modules' docstrings/comments, so whichever ticket wires proc's tier-2
join has one named constant to join through instead of a bare "exec"
literal or a rename.

Also fixed an unrelated Edit mistake I introduced and caught myself: my
first insertion of the new test class accidentally split
TestModeQualified's second method (test_capability_mode_kinds_includes_
fs_read_write) into the new class -- corrected before running gates so
both classes' membership is unchanged except for the ONE new test method
this ticket adds.

frob:waive AFFECT001 on PROC_FAMILY_SCANNER_KIND matches the existing
T-1047 precedent on CAPABILITY_KINDS in the same file: no live wired-join
behavior changed, and docs/strata/selfconform.md is outside T-1073's
declared 2-file scope.

Ran tests/unit/vet/test_capability_modes.py + tests/test_capability_registry.py
(19 passed, 0 failed). gates-fast/gates-native/gates-security/ruff all
pass under --ticket T-1073 except the pre-existing TICK006 (T-0667's own
phantom-draft finding, unrelated, unchanged before/after -- same one
noted in T-1063's Done report).

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/vet/test_capability_modes.py::TestProcFamilyNamingReconciliation::test_proc_family_kept_distinct_from_registry_exec_kind` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
