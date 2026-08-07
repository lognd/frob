## Done report

Built a single shared, mode-qualified capability vocabulary
(`frob.vet._capability_modes`, new module) covering `family.mode` ids
(`fs.read`/`fs.write`/`net.connect`/`net.listen`/`env.read`/`env.write`/
`proc.spawn`/`ffi.call`, generated from one `FAMILY_MODES` table so the
vocabulary cannot fork), a `LEGACY_CAPABILITY_ALIASES` migration table
(`fs-write`/`fs-read` -> `fs.write`/`fs.read`) with T-0576-shaped
since/sunset/ticket metadata, and `resolve_capability_kind` (the
WARN-in-window / ERR-past-sunset gate decision, sunset 2026-10-20).
`expand_declared_kind` implements the design mandate: a precise
`family.mode` id covers only itself, a bare coarse family name covers the
UNION of that family's modes (a coarse declarer answers for everything);
only `fs` is exploded live this pass (`WIRED_MODE_FAMILIES`) since the vet
scanner has no connect/listen (or env/proc/ffi mode) distinction to
normalize observations against yet -- exploding an unwired family would
make every existing bare declaration spuriously go SYS101-stale.

Wired the vocabulary into `frob.strata._effects` (`_KIND_MAP` now maps
`fs-write`/`fs-read` scanner kinds to `fs.write`/`fs.read` instead of the
old ambiguous bare `fs`; `_declared_kinds` canonicalizes+expands every
`may` atom through the shared module; new `check_legacy_capability_aliases`
model-wide gate surface) and `frob.strata._selfconform` (`_EXTENDED_KINDS`
loses `fs-read`, now delegated to the core THREAT004 join like `fs-write`
always was; the old `_alias_legacy_fs_observations`/bare-`fs`-covers-
`fs-read` special cases are REMOVED -- `_stale_design_violations` now
judges SYS101 staleness per RAW DECLARED ATOM via `expand_declared_kind`,
so a precise `may "fs.read"` discharges narrowly while a coarse `may "fs"`
still discharges on either mode being observed, as a natural consequence
of the same generic join rather than fs-specific code).

Not done, filed as a follow-up (T-draft-3e4b416a, converts to a real
T-#### id at land): extending the live wiring to net/env/proc/ffi (needs a
real per-mode scanner needle split first) and the ESTATE sibling-repo
migration (mandate point 3) once those land. `design/frob.strata`'s own
`may "fs"`/`may "fs-read"` declarations were left untouched (out of this
ticket's file scope; every node that declares one already declares BOTH,
so no self-conformance behavior changed for them).

### Changed
- src/frob/vet/_capability_modes.py (new)
- src/frob/strata/_effects.py
- src/frob/strata/_selfconform.py
- src/frob/strata/__init__.py
- tests/unit/vet/test_capability_modes.py (new)
- tests/unit/strata/test_effects.py
- tests/unit/strata/test_selfconform.py

### Verification
- `uv run pytest tests/unit/vet/test_capability_modes.py
  tests/unit/strata/test_effects.py tests/unit/strata/test_selfconform.py
  tests/test_capability_registry.py -q` -- all pass (20 new node ids plus
  every pre-existing test in those files, 2 assertions updated for the
  new `fs.write` spelling per T-0717's rename).
- `uv run frob test --base main` -- PASS (touched-set selection, exit=0).
- `uv run frob check --ticket T-0717 --only lint/static/gates-fast/
  gates-native/gates-security` -- clean except REL001 (pyproject.toml
  version bump), which is land-owned per the agent playbook section 4b and
  deliberately untouched here.
- `git diff main --diff-filter=D --stat` -- empty (no out-of-scope
  deletions).

Pre-existing, unrelated: `tests/unit/strata/test_export_golden.py`'s
k8s/seccomp/iam golden fixtures are already stale against `design/
frob.strata` (a `fleet`-node addition from an earlier, unrelated landed
ticket) -- confirmed via `git diff --stat HEAD -- src/frob/strata/
_export.py design/frob.strata tests/unit/strata/test_export_golden.py`
(empty; none of these files are touched by this ticket).

Also pre-existing, surfaced by the required `git merge main` (deletion-
filter check, playbook section 9 -- T-0695 landed `src/frob/arch/
_concurrency.py` after this branch's original base):
`tests/unit/strata/test_selfconform.py::TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant` now fails with 4
SYS100 findings ("capability 'exec' observed ... but not declared" on
node `graphlang`, `src/frob/arch/_concurrency.py`) -- T-0695's new file
uses subprocess/fork without `design/frob.strata`'s `graphlang` node
declaring `may "exec"`. Confirmed unrelated to this ticket: `_KIND_MAP`'s
`exec` mapping is untouched by T-0717 (only `fs-write`/`fs-read` changed),
and neither `design/frob.strata` nor `src/frob/arch/_concurrency.py` are
touched here or in scope. `uv run frob check --ticket T-0717 --only
gates-fast/gates-security` both stay clean (REL001 aside) -- the gate
surface itself does not regress, only this one direct pytest exercise of
`check_self_conformance` against the live repo. Not fixed here (out of
scope); flagging for the coordinator/a follow-up ticket rather than
silently leaving it undocumented.

### Changed
```
 src/frob/strata/__init__.py             |   4 +
 src/frob/strata/_effects.py             | 115 +++++++++++-
 src/frob/strata/_selfconform.py         | 140 +++++++-------
 src/frob/vet/_capability_modes.py       | 311 ++++++++++++++++++++++++++++++++
 tests/unit/strata/test_effects.py       |  88 ++++++++-
 tests/unit/strata/test_selfconform.py   |  57 +++++-
 tests/unit/vet/__init__.py              |   0
 tests/unit/vet/test_capability_modes.py | 105 +++++++++++
 tickets.md                              | 198 +++++++++++++++++++-
 9 files changed, 937 insertions(+), 81 deletions(-)
```

### Evidence
- `tests/unit/vet/test_capability_modes.py::TestModeQualified::test_joins_family_and_mode` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestModeQualified::test_capability_mode_kinds_includes_fs_read_write` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_precise_kind_covers_only_itself` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_coarse_fs_covers_union_of_modes` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_unwired_family_stays_coarse` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestExpandDeclaredKind::test_kind_with_no_modes_defined_stays_itself` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_precise_kind_passes_through` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_coarse_family_is_never_deprecated` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_legacy_alias_in_window_resolves_and_warns` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_legacy_alias_past_sunset_is_gate_error` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestResolveCapabilityKind::test_sunset_date_itself_is_already_expired` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_canonical_declared_kind_resolves_alias_regardless_of_sunset` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_normalize_observed_kind_matches_canonical` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_discharges_read_only_code` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestModeQualifiedFsConformance::test_fs_read_declaration_fails_conformance_on_a_write` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_in_window_is_a_warning_not_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_legacy_alias_past_sunset_is_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases::test_non_legacy_declaration_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestModeQualifiedFsStaleDesign::test_fs_read_declaration_discharges_on_read_only_code` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestModeQualifiedFsStaleDesign::test_fs_read_declaration_stays_stale_when_only_writes_observed` (pytest node id, verified passing when recorded)
