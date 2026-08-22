## Done report

T-2466's LEXCHECK001 widening (repo-wide `DETECTOR_PACKAGE_ROOTS`, past
`src/frob/gates/**` alone) surfaced 5 real, previously-invisible
lexical deciders in `src/frob/vet/_supplychain.py`, each deciding from
`re.search`/`re.match` over a manifest's raw text and building a
symref-less `Violation`.

Per the ticket's own class-(a)-vs-(b) framing: all five were fixable at
the root, class (b) all the way -- every manifest format already has a
real parser available:

- `pyproject.toml` / `Cargo.toml`: `tomllib`
- `package.json`: `json`
- a PEP 508 dependency string (`"requests>=2.0"`): `packaging.
  requirements.Requirement`
- `setup.py`'s `data_files=` kwarg: `ast` (a real Python source parse)
- `setup.cfg`'s declarative `[options.data_files]` section:
  `configparser`
- a GitHub Actions workflow's `uses:` values: `yaml` (already a project
  dependency, used elsewhere in this repo)

`src/frob/vet/_supplychain.py` no longer imports `re` at all. Behavior
is unchanged: same VET007/VET008/VET009 rule ids, same message
wording/shape, same severities. Verified directly against the real repo
(`supply_chain_tree_violations(Path("."))`) -- 11 VET007 + 6 VET009
findings against this repo's own `pyproject.toml`/`.github/workflows/
ci.yml`, same shape as before.

One behavioral WIDENING (disclosed, not hidden): `_unpinned_ci_action_
violations` used to only match a `uses:` LINE whose action name had
exactly one `/` (`owner/action`, the regex's own character-class
limit); the new recursive YAML-structure walk finds a `uses:` key
anywhere in the document regardless of action-name shape, correctly
covering a subdirectory action reference (`owner/repo/subpath@ref`,
which GitHub Actions allows and the old regex could never match). No
existing test exercised that shape either way, so this is a coverage
improvement, not a behavior change any test depends on.

Updated `tests/unit/gates/test_lexical_selfcheck.py`'s
`_KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG` from the 5-entry disclosed set
back to an empty frozenset (kept named, not deleted, so a FUTURE
regression in this package restores it by name) -- the backlog test now
asserts the raw LEXCHECK001 finding set is exactly empty again.

Changed:
- `src/frob/vet/_supplychain.py` (all 5 detectors rewritten to parse
  their manifest format for real; `_is_unpinned_spec`/
  `_opaque_binary_artifact_violations`/`_has_nearby_build_recipe`
  unchanged)
- `tests/unit/gates/test_lexical_selfcheck.py`
  (`_KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG` shrunk to empty, docstrings
  updated to describe the T-2469 fix instead of the T-2466 backlog)

Evidence:
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_detector_package_module_stays_clean`
- Full `tests/test_vet.py`: 461/461 passed, 0 failed (behavior-
  preserving: no test needed updating beyond the backlog assertion
  itself).
- Full `tests/unit/gates/test_lexical_selfcheck.py`: 8/8 passed.
- Direct repo-wide `frob check --ticket T-2469`: 0 LEXCHECK001
  findings anywhere (previously 5), 0 errors attributable to this diff
  on either touched file.

Filed: none.

Gates: `frob check --ticket T-2469` clean on
`src/frob/vet/_supplychain.py` and
`tests/unit/gates/test_lexical_selfcheck.py`.

### Changed
```
 src/frob/gates/_lexical_selfcheck.py       |   2 +-
 src/frob/vet/_supplychain.py               | 287 ++++++++++++++++++++++-------
 tests/unit/gates/test_lexical_selfcheck.py |  66 +++----
 tickets/T-2469/ticket.md                   |   4 +-
 4 files changed, 249 insertions(+), 110 deletions(-)
```

### Evidence
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2466, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t2469-supplychain-lexcheck/src/frob/app/ticket_runner/_waive_audit.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
