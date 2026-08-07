## Done report

**Round 1 REJECTED on review**: bare 3-segment path-suffix matching (no
scan-target check) closed the non-editable-install false positive but
opened a real evasion hole -- `is_self_pattern_path` is reached from
`scan_directory_capabilities`/`scan_directory_fingerprints`, the same
entrypoints `frob vet` uses to scan a vendored/third-party dependency
tree. A malicious dependency placing a file at a path ending in
`frob/vet/_capability.py` would have been silently excluded from
capability scanning. Round 2 (this version) fixes that.

Changed:
- src/frob/vet/_capability.py::is_self_pattern_path -- signature is now
  `(path: Path, root: Path | None = None) -> bool`. The suffix match
  (`_SELF_PATTERN_SUFFIXES`, unchanged from round 1) is now GATED on a new
  scan-target discriminator, `_is_frob_repo_root(root)`: True only when
  `root` itself (no ancestor search -- see below) has a `pyproject.toml`
  declaring `name = "frob"` AND `frob-core`/`strata-core` directories
  alongside it. `root=None` (the default) always fails the discriminator
  (fail-closed: never exclude, always scan), which keeps the function
  source-compatible with any caller written against the pre-T-0253
  one-argument form.
- src/frob/vet/_capability.py::_is_frob_repo_root (new, private,
  `lru_cache`d per resolved root) -- the discriminator itself. Deliberately
  checks `root` ONLY, never an ancestor: `frob vet` locates a Python
  dependency's source under `<project-root>/.venv/lib/*/site-packages/
  <name>` (`frob.vet._source.locate_pypi_source`), so when frob vets its
  OWN dependencies, every located dependency source is nested under
  frob's own repo root. Ancestor-walking would climb back to frob's own
  markers and wrongly classify every one of frob's own third-party
  dependencies as "self" -- a strictly worse, repo-wide scanner bypass.
  This is the honestly-considered and rejected alternative to the
  per-scan-root check actually shipped.
- src/frob/vet/_capability.py::_is_self_path -- the two existing private
  callers inside this module now thread `source_dir` through as `root`.
- src/frob/strata/_effects.py::_line_effects -- threads its existing
  `root` parameter through to `is_self_pattern_path(path, root)` (self-
  conformance always passes frob's own repo root here by construction, so
  this is a no-op for that caller, exactly preserving T-0201's prior
  behavior).
- src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node,
  _observed_all_kinds_by_node -- same threading, same no-op-for-this-
  caller reasoning.
- tests/test_vet.py -- reworked the T-0253 round-1 tests to account for
  the discriminator, and added the REQUIRED adversarial test:
  - `_make_fake_frob_repo_root` (module-level helper): builds a fixture
    directory carrying the pyproject-name + crate-dir markers plus a copy
    of the real `src/frob` tree, used by the foreign-install and
    self-scan tests.
  - `TestFingerprintScan.test_self_pattern_exclusion_survives_a_foreign_install_copy`
    -- rebuilt to scan starting AT a fake repo root (the discriminator's
    unit) rather than a bare subdirectory, still simulating the non-
    editable-install split.
  - `TestFingerprintScan.test_self_pattern_exclusion_does_not_match_unrelated_same_name_file`
    -- narrowness check (kept from round 1): an unrelated third-party
    `_capability.py` at a different package path, under a non-frob root,
    is not excluded.
  - `TestFingerprintScan.test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency`
    (NEW, the reviewer's required adversarial test): a file at
    `evil-pkg/frob/vet/_capability.py` (exact suffix match, real
    `os.system("evil")` payload) under a root with NO frob markers is
    confirmed to (a) genuinely carry a capability
    (`scan_file_capabilities` finds `exec`), (b) NOT be excluded by
    `is_self_pattern_path`, and (c) actually get scanned and flagged by
    `_aggregate_capabilities` end-to-end -- closing the exact hole the
    reviewer reproduced.
  - `TestCapabilityScan.test_scan_directory_capabilities_excludes_own_module`
    and `TestFingerprintScan.test_scan_directory_fingerprints_excludes_the_catalog_itself`
    -- updated to scan from a fake repo root (discriminator-satisfying)
    instead of a bare subdirectory; the capability-scan test additionally
    asserts that scanning the SUBDIRECTORY alone (discriminator-refusing)
    still shows the leak, demonstrating the narrowness is real, not
    accidental.

Discriminator decision (documented inline at `_is_frob_repo_root` and in
`is_self_pattern_path`'s docstring in `_capability.py`): gated on the
scanned tree's ROOT identity (`pyproject.toml` name + `frob-core`/
`strata-core` dirs), checked at exactly the directory the caller passes
in, never ascended to an ancestor. Self-conformance callers always pass
frob's own repo root by construction (audits its own tree), so the
discriminator is a no-op there and T-0201's prior exclusion behavior is
unchanged. `frob vet` scanning a dependency passes that dependency's own
located source root, which is never frob's repo, so the exclusion never
fires there and a mimicking file is scanned like any other -- this is
what the new adversarial test verifies directly. Residual, disclosed risk:
a PyPI package that typosquats the name `frob` AND additionally vendors
empty `frob-core`/`strata-core` directories purely to forge the
discriminator could still evade -- judged acceptable because (1) it
requires deliberately impersonating frob's own package identity plus its
specific Rust-crate layout, a much higher and more conspicuous bar than
"nest a file three levels deep", and (2) the primary threat model named
in review (arbitrary dependency mimicking the file path) is fully closed.

Evidence:
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
  (existing T-0201 drift-lock, still green, unmodified)
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_match_unrelated_same_name_file
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency
  (the reviewer-required adversarial test)
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself
- `uv run pytest tests/test_vet.py -o addopts="-v"` -- 100 passed
- `uv run pytest tests/test_vet.py tests/unit -k "strata or capability or fingerprint or selfconform or effects" -q` -- all green (no failures)
- Empirical verification, both ways, for REAL this time (round 1's report
  overclaimed here -- honestly correcting it): the round-1 Done report
  said the global `frob` binary was "a stale separately-installed version"
  and relied only on the simulated foreign-install test. That was true but
  insufficient per review. This round: ran `make install-tool` (`uv tool
  install --force --reinstall . --with ./strata-core --with ./frob-core`)
  to rebuild the actual global `~/.local/bin/frob` binary from THIS
  worktree's fixed source (non-editable, real site-packages install), then
  ran the bare global `frob sys audit` against this worktree's checkout:
  0 SYS100 gaps, self-conformance PROVED, only the same pre-existing
  unrelated LINT004 gap (see below). This is the actual non-editable-
  install reproduction the ticket asked for, not a simulation. Separately,
  `uv run frob sys audit` (editable) also stays at 0 SYS100 gaps.
  NOTE: this rebuilt the user's global `frob` tool in place from this
  worktree's source -- the global binary now reflects this fix rather
  than whatever it was built from before.

Not Filed: T-draft-2a3adb6d (never refiled) (finalizes to a real id on land) -- "bump version
+ frob release stamp for T-0253's is_self_pattern_path signature change".
`frob check --ticket T-0253` flags REL001 (public API changed, major,
since 0.2.0 -- the new optional `root` param still changes the recorded
signature digest even though it is backward-source-compatible). Fixing
REL001 means editing `pyproject.toml`/`.frob-release.json`, neither of
which is in T-0253's declared scope (`src/frob/vet/_capability.py`,
`src/frob/strata/**`, `tests/**`, `tickets.md`), so it could not be
absorbed into this ticket without a scope violation of its own. Disclosed
here rather than silently left dangling or force-fixed out of scope.

Gates: `uv run frob check --ticket T-0253` -- violations beyond REL001
(disclosed above) are: TEST006 (no coverage stamp; repo-wide,
pre-existing), PERF004 at `src/frob/tickets/_land.py:75` (pre-existing),
PERF003 at `src/frob/vet/_obfuscation.py:77` (pre-existing) -- all three
confirmed present identically on unmodified `main` via `git stash`
before/after comparison, so none are introduced by this diff. Two
SCOPE001 hits on `frob-core/Cargo.lock`/`strata-core/Cargo.lock` appeared
transiently and repeatedly from `make core`/`frob check`'s own build/
typecheck side effects during the session and were reverted (`git
checkout -- frob-core/Cargo.lock strata-core/Cargo.lock`) each time before
finishing; final `git status --short` shows only
`src/frob/strata/_effects.py`, `src/frob/strata/_selfconform.py`,
`src/frob/vet/_capability.py`, `tests/test_vet.py`, and `tickets.md`
modified. `git diff <merged-main-tip> --diff-filter=D --stat` is empty
(deletion-filter land rule, section 9 of the agent playbook) -- merged
`origin/main` (971a160) first, per coordinator instruction; the only
deletions relative to the OLD stale base (`99ec64c`) landed IN that merge
itself (`tests/unit/strata/litmus/waive_lint_store.strata` and its test),
not from this ticket's diff, confirmed by `git log --diff-filter=D` on
those paths pointing at commit 971a160.
