# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0153 -->
```yaml
id: T-0153
title: 'std.cve fingerprints: pattern catalog for known vulnerable-usage classes'
state: done
kind: security
origin: human
created: '2026-07-18'
blocked_by:
- T-0158
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py
- tests/unit/strata/**
- tests/test_vet.py
- docs/strata/threat.md
- docs/modules/vet.md
- tickets.md
evidence:
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_has_at_least_one_cve_citation
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_has_at_least_one_needle
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_language_is_a_scanned_bucket
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_fingerprint_ids_are_unique
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_view_membership_matches_the_catalog_exactly
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_default_catalog_is_drift_clean
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_every_fingerprint_cwe_id_resolves_against_the_joined_catalog
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_unknown_cwe_id_fails_loudly
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_a_removed_cwe_entry_is_detected_against_a_narrowed_catalog
- tests/test_vet.py::TestFingerprintScan::test_matches_a_known_fingerprint
- tests/test_vet.py::TestFingerprintScan::test_no_match_on_clean_source
- tests/test_vet.py::TestFingerprintScan::test_no_language_returns_empty
- tests/test_vet.py::TestFingerprintScan::test_unreadable_file_returns_empty
- tests/test_vet.py::TestFingerprintScan::test_language_mismatch_does_not_match
- tests/test_vet.py::TestFingerprintScan::test_own_catalog_file_excluded_from_directory_aggregation
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_surfaces_a_cve_fingerprint_finding
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_cve_fingerprint_catalog_checked_every_call
attachments: []
acceptance: []
threat: null
```
Extend the standard library beyond CWE entries with CVE FINGERPRINTS: code-level patterns for canonical vulnerable-usage classes, so the scanner can flag the pattern in our own code and in vetted dependency source -- not just match dependency versions against the mirror (T-0146/T-0147 handle that). Model: CveFingerprint entries (id, title, cve cite(s), linked cwe id joining the existing catalogs, language, detection needles following vet _capability's recall-over-precision substring philosophy including the T-0151 dot-exclusion lessons, remediation guidance). Curated starter set of 10-15 canonical classes with REAL citations, e.g.: pickle.loads on untrusted data, yaml.load without SafeLoader, subprocess shell=True with interpolation, requests verify=False, weak-hash password storage, jndi-style lookup injection (Log4Shell class), eval on request data, tarfile extractall path traversal, xml external entities. Each fingerprint drift-locked to the CWE catalog (unknown cwe id fails loudly) and exercised by fire/discharge fixtures in the litmus style. Wire into vet scan output and into the threat catalog views as a separate table following the CWE_TOP_25_VIEWS precedent (do not silently widen default views). Honest limits documented: substring fingerprints have false-positive classes -- document them per T-0151's precedent rather than half-building AST precision.

## Done report

Changed:
- src/frob/strata/_cve_fingerprint.py (new) -- `CveFingerprint` model,
  `CVE_FINGERPRINTS` (9 entries), `CVE_FINGERPRINT_VIEWS`,
  `FingerprintViolation`, `check_fingerprint_catalog_drift` (CVEFP001)
- src/frob/strata/__init__.py -- exports the five new public symbols above
- src/frob/vet/_capability.py -- `scan_file_fingerprints` (lazy
  `frob.strata` import to break the `_effects.py` <-> `_capability.py`
  import cycle); `_FINGERPRINT_CATALOG_PATH` self-match exclusion added to
  `_is_self_path`
- docs/strata/threat.md -- new "CVE fingerprints: code-level pattern
  catalog (T-0153)" section, `<a id="cve-fingerprints-code-level-pattern-
  catalog-t-0153">` anchor
- docs/modules/vet.md -- `scan_file_fingerprints` added to the Public API
  describes-anchor list and prose list
- tests/unit/strata/test_cve_fingerprint.py (new)
- tests/test_vet.py -- `TestFingerprintScan` class added

Curated set is NINE fingerprints, not the ticket's illustrative "10-15":
every `cve` citation was independently web-searched and verified against a
primary/vendor/NVD source at authoring time (never hand-guessed from
memory) -- CVE-2014-6271 (Shellshock, CWE-78), CVE-2015-9251 (jQuery
cross-domain XSS, CWE-79), CVE-2007-4559 (Python tarfile traversal,
CWE-22), CVE-2017-18342 (PyYAML unsafe load, CWE-502), CVE-2025-32444
(vLLM pickle.loads RCE, CWE-502), CVE-2012-2661 (Rails SQLi, CWE-89,
disclosed cross-ecosystem exemplar), CVE-2021-21973 (VMware vCenter SSRF,
CWE-918, disclosed cross-ecosystem exemplar), CVE-2021-23358
(underscore.js template code injection, CWE-94), CVE-2015-7755 (Juniper
ScreenOS hardcoded backdoor password, CWE-798, disclosed cross-ecosystem
exemplar). Three ticket-suggested classes (TLS verify=False/CWE-295,
weak-hash password storage/CWE-916, XXE/CWE-611) are deliberately NOT
shipped: no `WeaknessEntry` for any of the three CWE ids exists in ANY
catalog tuple, so a fingerprint citing any of them would fail this
ticket's OWN CVEFP001 drift-lock -- disclosed consistently in both the
module docstring and docs/strata/threat.md as a gap needing a
catalog-scoped follow-up ticket, not forced around the drift-lock.
JNDI/Log4Shell-class lookup injection is also omitted: it is Java/JNDI-
specific with no equivalent construct in any of the four languages
`frob.vet._capability` scans (python/typescript/rust/c-cpp), so a
fingerprint for it would be undetectable data, not a real pattern-match
capability.

"Litmus-style fire/discharge fixtures" (ticket text) are NOT `.strata`
kernel-model fixtures: `CveFingerprint` is a source-code substring scan
over real files (`scan_file_fingerprints`), not a `WeaknessEntry`-shaped
kernel precondition with a `may` capability join -- there is no
`_fired_obligations`/THREAT003 discharge concept for a fingerprint to
fire/discharge against. The litmus-equivalent proof implemented instead:
`TestFingerprintScan` in tests/test_vet.py exercises each fingerprint's
needle against a real source snippet (positive: `FP-DESERIALIZE-YAML-001`
matches `yaml.load(...)`; negative: clean source and cross-language
needle-text produce zero matches), and `TestCatalogDrift` in
tests/unit/strata/test_cve_fingerprint.py proves the CVEFP001 drift-lock
fires on an unjoined/removed cwe_id and stays clean against the shipped
catalog. Filed a design finding in docs/strata/threat.md rather than
silently reinterpreting the ticket's fixture-format request.

Evidence: 19 test node ids recorded via `frob ticket evidence T-0153`
(tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape/
TestCatalogDrift, tests/test_vet.py::TestFingerprintScan/
TestScanTreeWithLocalSource, tests/unit/strata/test_audit.py::
TestExhaustiveness -- full list in this ticket's `evidence:` yaml block
above).

Filed: none -- the disclosed gaps above (CWE-295/CWE-916/CWE-611 catalog
entries; Log4Shell-class fingerprint) are documented in-repo rather than
filed as new tickets, since closing them requires a catalog-scoped
decision (adding `WeaknessEntry` rows) out of this ticket's own scope
(`src/frob/strata/**` includes `_threat.py`, but widening `CWE_CATALOG`/
`QUALITY_CATALOG` itself is a separate, catalog-owning decision this
ticket's scope note did not request); coordinator files these serially,
not this ticket.

### Fix round (reviewer REJECT -> addressed)

Round 1 reviewer verdict: catalog/model/drift-lock logic, docs, self-match
exclusion, import-cycle handling, and all 9 CVE citations verified solid,
but REJECTED on one real gap -- `scan_file_fingerprints` was wired as a
detector but never CALLED by the real `frob vet` pipeline
(`_scan_source` only aggregated `scan_directory_capabilities`/
`decode_to_exec_signal`), so a dependency containing e.g.
`yaml.load(data)` produced zero fingerprint signal in
`PackageVerdict`/`Violation` output; `check_fingerprint_catalog_drift`
also ran test-only, with no operational path mirroring THREAT002/003's
`evaluate_exhaustiveness` wiring; and the module docstring named CWE-916
in a sentence without it appearing in the cut-class list above it.

Addressed:
1. `frob.vet._capability.scan_directory_fingerprints` (new) -- the
   aggregation sibling of `scan_directory_capabilities`, same walk/
   test-path/self-path exclusion shape. Called from `_scan.py::
   _scan_source` (extending T-0153's scope to include
   `src/frob/vet/_scan.py`, recorded in `scope:` above -- required to
   wire the call site the ticket's own text asked for, a cascading
   scope-by-necessity consequence, not silently absorbed). A match now
   surfaces a `VET006` `Violation` and a `"cve-fingerprint"` signal
   persisted onto the stored `PackageVerdict`. Proven end to end via
   `tests/test_vet.py::TestScanTreeWithLocalSource::
   test_scan_tree_surfaces_a_cve_fingerprint_finding` -- a real `uv.lock`
   + on-disk `.venv/lib/*/site-packages/` dependency source through the
   REAL `scan_tree` pipeline, not a direct `scan_file_fingerprints`
   import -- asserting a `VET006` violation citing the matched
   fingerprint id AND the `"cve-fingerprint"` signal on the returned
   `PackageVerdict`.
2. `frob.strata._audit.evaluate_exhaustiveness` now runs
   `check_fingerprint_catalog_drift` every call under a fixed
   `"cve-fingerprint:catalog"` pseudo-view (model-independent -- mirrors
   `_pii_gaps`'s fixed `"pii:model"` view precedent exactly, since a
   catalog-join property has no per-model baseline-view concept), so
   `frob sys audit` fails closed on a drifted `cwe_id` the same way
   THREAT001-003 already do. Proven by
   `tests/unit/strata/test_audit.py::TestExhaustiveness::
   test_cve_fingerprint_catalog_checked_every_call` (asserts
   `"cve-fingerprint:catalog"` in `views_checked` and zero
   `family="cve-fingerprint"` gaps against the shipped, drift-clean
   catalog -- the drift-DETECTION logic itself stays covered by
   `test_cve_fingerprint.py::TestCatalogDrift`, this test proves only
   that the operational path calls it).
3. Reconciled the CWE-916 docstring/list mismatch: both the module
   docstring and docs/strata/threat.md now list all THREE deliberately
   cut classes together (CWE-295, CWE-916, CWE-611) consistently, instead
   of naming CWE-916 in one sentence without it appearing in the cut list
   above.

Gates: `uv run frob check --ticket T-0153` clean of ticket-attributable
findings after both fix rounds (COV001 doc edge on
`CVE_FINGERPRINT_VIEWS`; PERF004 sort-in-loop waived in
`scan_file_fingerprints`; PERF001 waived in the new `scan_tree`-level
test; SCOPE001 resolved by extending `scope:` to include
`src/frob/vet/_scan.py`; TEST001 resolved by adding
`scan_directory_fingerprints` unit tests; ruff-check/ruff-format/ty all
clean). Remaining `frob check` output after the round-2 fix (TEST006 no
coverage stamp; COV003 on unrelated ticket T-0168's evidence, picked up
by the main merge) is campaign-wide/pre-existing, not attributable to
this ticket's diff. `uv run frob test --base main`: touched=49, selected
python suite exit=0 (4.84s), including the full `tests/test_vet.py`,
`tests/unit/strata/test_cve_fingerprint.py`, and
`tests/unit/strata/test_audit.py`.

<!-- ticket:T-0156 -->
```yaml
id: T-0156
title: 'release readiness: version, changelog, packaging, and the release gate'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0148
- T-0153
- T-0154
- T-0155
- T-0157
- T-0158
- T-0159
- T-0162
parent: null
scope:
- pyproject.toml
- CHANGELOG.md
- README.md
- docs/**
- strata-core/Cargo.toml
- frob-core/Cargo.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Get frob into a releasable state once the gates-zero sweep and the three feature tickets land. Deliverables: (1) version bump decision (current 0.1.0 line -- pick the next version honestly against the scale of what shipped) stamped via frob release stamp, with frob release check green as the gate; (2) CHANGELOG.md generated from the ticket archive + git history since the last release, grouped by area (strata, threat/CVE, vet, check/gates, tickets, editors), human-readable, every T-#### referenced; (3) README refresh: current subcommand table, strata overview with the self-model/self-conformance story, editors support, CVE mirror workflow, install paths (uv tool install, bare pip, dev) each verified by actually running them; (4) docs/index.md completeness pass -- every docs/ page linked, every public module documented; (5) packaging: uv build the wheel, decide and document the native-crate strategy (strata-core/frob_core: bundled, separate wheels, or optional with the T-0133-135 degrade contract -- verify the degrade contract works from the actual built wheel in a bare venv, and verify the T-0142/T-0152 dependency completeness holds there too); (6) final release gate: frob check exit 0 with gates at zero, frob sys audit fully PROVED, full pytest suite green, drift-locks all live. Do not tag or publish -- leave the repo in a provably releasable state and report what the release command sequence would be.

<!-- ticket:T-0159 -->
```yaml
id: T-0159
title: 'extending frob: developer guides for every registry and extension point'
state: queued
kind: docs
origin: human
created: '2026-07-18'
blocked_by:
- T-0153
- T-0154
- T-0155
- T-0157
- T-0158
parent: null
scope:
- docs/guides/**
- docs/index.md
- src/frob/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
A guide series under docs/guides/extending/ making every registry trivially extendable. INVENTORY FIRST: enumerate every registry/extension point in the codebase -- at minimum: gate rule families and their registration (COV/TEST/DRIFT/SCOPE/PRE/DOC/PERF/SYS/THREAT/COMPLIANCE/WAIVE), comment DSL directives (frob:ticket/tests/doc/waive/todo/invariant/channel/boundary/secret), threat catalog (WeaknessEntry/OutOfScopeEntry/views incl. the separate-views precedent), compliance regulations/views, capability registry + pattern tables + per-language matrix cells (T-0158), CVE fingerprints (T-0153), PII categories (T-0154), design-lint rules (T-0155), secrets-scan providers (T-0157), prover claim kinds, scenario kinds, strata surface grammar keywords (and the tmLanguage drift-lock), [[test.runner]] entries, language grammar handlers, sys export formats, litmus fixture mappings, benign capabilities, ticket kinds/states. ONE GUIDE PER REGISTRY on a common template: what it is and where it lives (file paths + symbol names); step-by-step 'add a new entry' recipe; WHICH DRIFT-LOCKS WILL FIRE when you add one and exactly what each demands (fixture, test, excuse entry, doc anchor, golden regen); a worked example diff; common mistakes (cite real session incidents where instructive, e.g. separate-views vs widening defaults, self-match false positives, stale-comment traps). ANTI-ROT MECHANISM (the point of doing this in frob): every guide is bound to its registry's code symbol with frob:doc anchors so the DOC gates flag drift when the registry changes; plus a completeness drift-lock test -- a machine-readable registry-of-registries (the inventory above) asserting every entry has a guide file and a live anchor, so ADDING A NEW REGISTRY without a guide fails the build. docs/index.md gains an Extending section linking every guide. Writing guides will require reading each registry's code carefully -- fix nothing beyond doc anchors; file tickets for any defect discovered while documenting.

<!-- ticket:T-0160 -->
```yaml
id: T-0160
title: burn down TEST005 module-line-coverage backlog (~78 modules below 85% floor)
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
evidence: []
attachments: []
acceptance: []
threat: null
```
TEST005 module-line-coverage floor (frob.toml [testing].module_line_cov=85) reports ~78 src/frob/** modules below threshold, from 0.0% (never-exercised runners like app/ack_runner.py, app/arch_runner.py, and most other app/*_runner.py CLI entry points) up to modules a few points shy of the floor (e.g. tickets/_store.py at 84.8%, strata/_claims.py at 84.7%). This backlog was invisible during T-0148's original scope (a fresh worktree has no .frob/coverage-stamp, and TEST005 silently produces no findings without one) -- it surfaced only after T-0148 regenerated the stamp to clear its own TEST006 finding ("no coverage stamp found"). It is pre-existing, repo-wide coverage debt, not something T-0148's edits introduced, and burning it down to the 85% floor across ~78 modules (many CLI app/*_runner.py entry points at literal 0%, needing new system/integration tests, not just unit tests) is a dedicated, multi-session effort far outside a gates-sweep ticket. Full per-module list captured via: uv run frob check --only test (TEST005 lines), 2026-07-18.

Acceptance: every src/frob/** module at or above module_line_cov=85 (or system_line_cov=80 in aggregate where a narrower per-module floor is not achievable), OR a specific, reasoned frob.toml override for modules that cannot reasonably reach the floor (e.g. thin CLI entry-point shims exercised only via subprocess system tests). Start with the 0.0%-covered app/*_runner.py entry points -- each is a CLI command's runner with no direct unit/integration test at all, the single highest-leverage slice of this backlog.

Scope correction (2026-07-18, same T-0148 sweep): `src/frob/gates/_coverage.py::_parse_classes` had a path-prefix bug -- Cobertura `filename` attrs are relative to the `--cov=src/frob` root (e.g. `app/ack_runner.py`), but every other path in `frob.graph` is repo-relative (`src/frob/app/ack_runner.py`); the two never matched, so BOTH `module_line` (this ticket's original ~78-module estimate) AND `symbol_branch` (per-symbol TEST005 branch-coverage, `unit_branch_cov=90`) silently mapped zero symbols this whole time. T-0148 fixed the prefix join. Re-running with the fix (and after excluding `src/frob/scaffold/data/**` template files, a separate genuine rule misfire fixed in the same sweep) shows the true backlog is far larger than originally scoped here: 197 unwaived TEST005 findings (up from ~78), most now per-symbol branch-coverage misses across `src/frob/**`, not just the module-line floor. This ticket's acceptance criteria and estimate above are superseded by that number -- treat "~78 modules" as the historical (and wrong, pre-fix) figure; the real acceptance criterion is 0 unwaived TEST005 findings from a fresh `uv run frob check --only test` after `make coverage`, both per-module and per-symbol. This is now unambiguously a dedicated, multi-session effort, not a gates-sweep add-on. (Renumbered from T-0157 to T-0160 on 2026-07-18: the original local allocation collided with main's real T-0157 (secrets-scan gate) landing concurrently; every `frob:waive TEST005` directive this ticket's sweep added under `src/frob/**` was updated in lockstep.)

<!-- ticket:T-0161 -->
```yaml
id: T-0161
title: 'PERF001-004 lexical heuristic: false-positive classes need real fixes, not
  permanent waivers'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**,tests/**,docs/**
evidence: []
attachments: []
acceptance: []
threat: null
```
found while working T-0148: the gates sweep waived 93 PERF001-004 sites (14 PERF001, 8 PERF002, 52 PERF003, 19 PERF004) as false positives of src/frob/perf/_rules.py's documented 'lexical, one-token-stream-deep linear-scan' heuristic. Every waived site fell into one of a small number of misfire classes, each fixable without a full AST/control-flow rewrite: (1) PERF003 'nested loop join' fires on ANY function body containing 2+ 'for' headers plus an '==' comparison ANYWHERE in the body, even when the two loops are separate siblings (a setup loop then an unrelated assertion loop) rather than actually nested -- needs real nesting-depth tracking, not a flat token count over the whole function. (2) PERF004 'sorted()/.sort() in a loop' fires on any sorted()/.sort() call that is lexically inside an enclosing for/while, even when it executes exactly once per function call (e.g. sorting a small already-collected result list right before returning) -- needs to distinguish 're-sorted every outer iteration' from 'lexically nested but reached once'. (3) PERF001 'membership test in a loop' (confirmed in strata-core/src/lib.rs) fires on 'x in <name>' with zero awareness of the collection's actual type -- a HashSet/HashMap membership test is O(1) and not a smell at all, but the heuristic cannot tell a HashSet from a Vec since it never sees types. (4) PERF002 similarly flags any .index()/.count() call lexically inside a loop regardless of whether it runs once per call. Deliverables: either (a) add lightweight scope/nesting tracking to the existing token-stream scanner (track brace/indent depth per 'for' header, require the '==' to be textually inside the INNER loop's body, not just anywhere after the outer loop opens; require sorted()/.sort()/.index()/.count() calls to be inside the loop body they are nested under AND for that enclosing loop to actually repeat the call across iterations rather than short-circuiting via return/break), or (b) for languages with type info available (Rust via the existing AST, TypeScript via its checker) consult the declared/inferred type of the container before firing PERF001/PERF002. Re-run the current 93 waived sites (grep 'frob:waive PERF00' across the repo for the exact list, dated 2026-07-18, T-0148) against the improved rules and either remove now-unnecessary waivers or downgrade them to genuinely-irreducible cases. Acceptance: fewer than half of the current 93 waivers remain necessary, and no new false-positive class is introduced (verified against this repo's own PERF-clean modules).

<!-- ticket:T-0166 -->
```yaml
id: T-0166
title: store grammar rejects code/may despite surface.md implying support
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs
- docs/strata/surface.md
- src/frob/strata/**
- tests/**
- design/frob.strata
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Confirmed twice (T-0150 review read parse_store directly: no code/may branch, falls through to unknown-store-property; typani pilot reconfirmed): stores cannot carry code/may declarations though docs/strata/surface.md implies they can. T-0150 worked around it by folding tickets_ledger's code into the core node. Fix properly: implement code/may on store_prop in strata-core (mirroring parse_node), elaborate into the kernel, un-fold frob's own tickets_ledger workaround in design/frob.strata, and correct surface.md either way so doc and grammar agree.

<!-- ticket:T-0169 -->
```yaml
id: T-0169
title: capability conformance did not scan TS/JS in the logand.app pilot -- verify
  per-language wiring
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/vet/_capability.py
- tests/**
- tickets.md
evidence:
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_typescript_core_net_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_undeclared_fires
- tests/unit/strata/test_selfconform.py::TestCoreUndeclaredInterfaceNonPython::test_rust_core_exec_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestLanguageCoverageDriftLock::test_scanned_languages_equals_registry_languages
attachments: []
acceptance: []
threat: null
```
logand.app pilot reports browser-side capabilities could not be auto-verified, leaving permanent SYS101 warnings -- yet vet _capability HAS a typescript pattern table (.ts/.tsx/.js in _EXT_LANGUAGE). Investigate whether the conformance path (scan_directory_capabilities via _selfconform / sys audit) actually walks TS/JS files or silently skips them (wiring bug), or whether the pilot's code globs missed the frontend tree (doc/UX gap). Either way the fix must make TS scanning provably active -- this feeds directly into T-0158's coverage matrix, which should gain a live wiring assertion (language column proven active end-to-end through sys audit, not just patterns existing).

## Done report

Root cause: WIRING BUG, confirmed by repro. `_selfconform.py::check_self_conformance`
handed `bind_code`'s Python-only `CodeBinding` (`_code_binding.py::_sorted_py_files`
walks only `*.py`, by design -- it also backs Python-import conformance) straight to
EVERY join that reconciles observed vs. declared capabilities. A `.ts`/`.js`/`.rs`/
`.c-cpp` file was therefore never even a KEY in `binding.owner`, so neither
`scan_file_capabilities` (extended kinds/SYS101) NOR `check_capability_conformance`
(core net/fs-write/exec kinds/SYS100) was ever called on it -- and the empty
directory-ownership set also produced a spurious SYS102 "unmodeled code" for any
directory whose only files were non-Python.

FIX ROUND 1 (extended kinds + SYS101 only): added `_capability_binding`, a superset
of `bind_code`'s binding covering every `language_for`-recognized extension, and
wired it into `_extended_kind_violations`/`_stale_design_violations`. Repro at the
time: a `.ts` file with `fetch(...)` + `localStorage.setItem(...)` went from 0
violations to correctly firing SYS100 for `fetch_url`/`client_storage`.

REVIEWER REJECT (round 1): correctly caught that `_core_undeclared_violations`
(net/fs-write/exec, delegated to THREAT004's `check_capability_conformance`) and
`_unmodeled_violations` (SYS102) were STILL being handed the raw Python-only
`binding`, not the `_capability_binding` superset -- so a `.ts` `axios.get(...)`
or `.rs` `Command::new(...).spawn()` still produced ZERO SYS100 and a SPURIOUS
SYS102, i.e. the exact same class of bug survived for the raw net/exec/fs-write
kinds the logand.app pilot most needs caught. My round-1 rationale ("Python-
import-syntax-specific by design") was WRONG for this delegate: verified by
reading `_effects.py::_line_effects`, which calls `language_for`/`_PATTERNS`
directly -- there is no Python-specific parsing anywhere in
`check_capability_conformance`'s path; only `bind_code` itself (the binding step,
not the capability-conformance check) needs Python's import syntax specifically.

FIX ROUND 2 (this round): `check_self_conformance` now passes `capability_binding`
(the superset) to ALL FOUR joins -- `_core_undeclared_violations`,
`_extended_kind_violations`, `_stale_design_violations`, AND `_unmodeled_violations`.
`bind_code`'s raw Python-only binding is still computed and is still the ONLY input
to `bind_code` itself (unrelated to this fix, stays Python-import-syntax-specific
by design) and to `_capability_binding`'s own construction (it extends that binding,
doesn't replace its Python-file entries). Repro confirmed both new cases: a `.ts`
`axios.get(...)` fires SYS100 `net` with no spurious SYS102; a `.rs`
`Command::new("ls").spawn()` fires SYS100 `exec` with no spurious SYS102. Design
choices reconfirmed unchanged: `_PACKAGE_ROOT = "src/frob"` (SYS102 scope, still
correct -- unrelated to language), and deny-by-default `AmbiguousCodeBinding` on a
multi-node glob match (unchanged in `_capability_binding`).

Fix (both files in scope):
- `src/frob/vet/_capability.py`: added public `SCANNED_LANGUAGES` (frozenset of
  every language `_EXT_LANGUAGE` maps at least one extension to) so a drift-lock
  test can assert self-conformance's scanned-language set equals
  `_capability_registry.LANGUAGES` without hand-duplicating either list.
- `src/frob/strata/_selfconform.py`: added `_sorted_capability_files` (walks every
  file under root with a `language_for`-recognized extension) and
  `_capability_binding` (extends `bind_code`'s Python-only `CodeBinding` with every
  OTHER capability-scannable-language file, bound by the SAME `code=` glob
  convention via `_node_code_globs`, reused not reimplemented; deny-by-default
  `AmbiguousCodeBinding` on a multi-node glob match, same as `bind_code`).
  `check_self_conformance` builds this superset binding once and passes it to ALL
  FOUR violation-collecting functions (`_core_undeclared_violations`,
  `_extended_kind_violations`, `_stale_design_violations`, `_unmodeled_violations`),
  so every registry-covered language is reconciled by every rule, not just
  Python by some of them.

Changed:
  src/frob/vet/_capability.py::SCANNED_LANGUAGES
  src/frob/strata/_selfconform.py::_sorted_capability_files
  src/frob/strata/_selfconform.py::_capability_binding
  src/frob/strata/_selfconform.py::_core_undeclared_violations (binding source changed, round 2)
  src/frob/strata/_selfconform.py::_observed_extended_kinds_by_node (binding source changed, round 1)
  src/frob/strata/_selfconform.py::_observed_all_kinds_by_node (binding source changed, round 1)
  src/frob/strata/_selfconform.py::_unmodeled_violations (binding source changed, round 2)
  src/frob/strata/_selfconform.py::check_self_conformance (wires _capability_binding into all four joins)

Evidence (frob:tests-bound, tests/unit/strata/test_selfconform.py, 20 tests total):
  TestNonPythonLanguageWiring.test_typescript_undeclared_capability_fires
  TestNonPythonLanguageWiring.test_typescript_undeclared_capability_discharges_once_declared
  TestNonPythonLanguageWiring.test_typescript_stale_design_fires
  TestNonPythonLanguageWiring.test_sorted_capability_files_includes_typescript
  TestCoreUndeclaredInterfaceNonPython.test_typescript_core_net_undeclared_fires
  TestCoreUndeclaredInterfaceNonPython.test_typescript_core_net_discharges_once_declared
  TestCoreUndeclaredInterfaceNonPython.test_rust_core_exec_undeclared_fires
  TestCoreUndeclaredInterfaceNonPython.test_rust_core_exec_discharges_once_declared
  TestLanguageCoverageDriftLock.test_scanned_languages_equals_registry_languages
  TestLanguageCoverageDriftLock.test_language_for_is_consistent_with_scanned_languages
The four new round-2 tests each assert both the SYS100 fire AND the absence of a
SYS102 for the same directory (the spurious-misreport the reviewer flagged). All
prior SYS100/SYS101/SYS102/drift-lock/real-gate-green tests in the same file still
pass unmodified.

POST-MERGE UPDATE (merging main a second time, after T-0181 closed): re-ran the
full verification pass. `TestRealGateGreen::test_repo_design_and_declarations_are_
self_conformant` (the real-repo-tree assertion) now FAILS: `SYS100 'html_render'
observed but not declared` on the `vet` node. Root-caused and DELIBERATELY NOT
fixed here: T-0181 added new `html_render` needles (`innerHTML`,
`dangerouslySetInnerHTML`) as literal string DATA inside
`src/frob/vet/_capability_registry.py` itself, so scanning that file's own text
self-matches `html_render` -- the exact documented self-match false-positive class
`vet.scan_directory_capabilities` already excludes via a private path check, but
`_selfconform.py`'s file-level SYS100/SYS101 joins scan node-owned files directly
and never got that exclusion. I prototyped exposing the exclusion to
`_selfconform.py` and REVERTED it: doing so correctly kills the false SYS100, but
then produces four NEW SYS101 "stale design" findings (eval/exec/deserialize/sql
on `vet`) -- proving `design/frob.strata`'s `vet` node `may` list was silently
calibrated against this same self-match noise as if it were real signal. Properly
fixing this needs `design/frob.strata` changes (recalibrating `may` against
genuine, non-self-match usage), which T-0169's `scope` explicitly excludes.
CONFIRMED this failure is 100% pre-existing and independent of every change in
this ticket: `git fetch`+checkout of unmodified `main` tip (3135c5c) and running
`TestRealGateGreen` there directly reproduces the identical failure with zero of
my changes present. Filed T-draft-e1beb2a8 (self-match + design recalibration)
and T-draft-e1beb2a8's sibling T-draft-a8e0354d (the tickets-archive.md splice,
below) to track both discoveries; this ticket's own diff does not touch
`design/frob.strata` or the self-match exclusion.

Filed:
- T-draft-a8e0354d: `tickets-archive.md` stale T-0169 duplicate from an unrelated
  ledger-conflict splice on `main` (see NOTE below).
- T-draft-e1beb2a8: self-conformance `TestRealGateGreen` red on the real repo tree
  (html_render self-match on `_capability_registry.py`; needs both a
  `_selfconform.py`/`_capability.py` exclusion AND a `design/frob.strata` `may`
  recalibration for the `vet` node).
(fix itself stayed inside declared scope; T-0158's own coverage matrix and
T-0181's `_capability_registry.py` were not touched by me.)

Gates: `uv run frob check` -- the only non-waived findings are a pre-existing
campaign-wide TEST006 coverage-stamp warning (never run `make coverage` per
standing instruction) and a pre-existing COV003 on ticket T-0168's evidence id,
confirmed present on merged `main` BEFORE this ticket's changes via `git stash`
(unrelated to this ticket's scope). `uv run frob test --base main`: the python
suite is RED specifically on `TestRealGateGreen`, confirmed pre-existing on
unmodified `main` tip (see POST-MERGE UPDATE above) and NOT a regression from
this ticket's diff -- every other selected test (all 20 in
`test_selfconform.py` plus the vet hook-mode smoke test) passes, including all
four round-2 core-path regression tests. `ruff format --check .` clean.

Not closing this ticket per workflow instructions (implementer records evidence and
Done report; closing/verification is a separate step).

NOTE (ledger integrity, found while merging main, out of scope to fix here): `tickets-archive.md` on `main` (post-merge, unmodified by me -- outside this ticket's `scope`) contains a STALE, INCORRECT duplicate of this exact T-0169 block (`state: queued`, no Done report, no evidence) -- it was silently spliced into the archive by an unrelated ledger-conflict merge (same incident class the agent playbook's "ledger-conflict splice guidance" warns about), NOT a real close. This live `tickets.md` entry (in-progress, with the Done report above) is the authoritative one; the archive's stray copy needs a follow-up ticket (scope: tickets-archive.md) to delete it so a future `frob ticket` listing doesn't show two T-0169 records in conflicting states.

<!-- ticket:T-0170 -->
```yaml
id: T-0170
title: kotlin capability-scanner column for android nodes
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- tests/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app has an android node; no Kotlin pattern table exists, so its capabilities cannot be verified. Add kotlin as a language column per the T-0158 matrix discipline: pattern tables for the reserved kinds where Kotlin idioms exist (net: OkHttp/HttpURLConnection/Retrofit; exec: Runtime.exec/ProcessBuilder; client_storage: SharedPreferences/Room; fs; eval: unusual -- excuse honestly), per-cell fire fixtures, .kt/.kts extension mapping. Sequence after T-0158 lands the matrix.

<!-- ticket:T-0171 -->
```yaml
id: T-0171
title: THREAT002 fires in quality views lacking the sink taxonomy security views have
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: THREAT002 (capability kind matches no sink taxonomy entry) fires against quality-family audit views because views do not share the capability-to-CWE mapping the security views carry -- the same signal that hit frob's own T-0150 work (DEFAULT_BENIGN_CAPABILITIES was the frob-repo patch, but external repos hit the raw gap). Decide the principled fix: the sink taxonomy and benign-capability excuse table should be single-sourced across view families, not re-declared per view; a capability genuinely irrelevant to a quality view must not demand a per-repo excuse. Regression-test against a fixture reproducing the pilot's shape.

<!-- ticket:T-0172 -->
```yaml
id: T-0172
title: managed marker for config-only infra nodes promised in surface.md but unimplemented
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs
- src/frob/strata/**
- docs/strata/surface.md
- tests/**
- tickets.md
evidence:
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_node_without_managed_is_not_managed
- tests/unit/strata/test_managed.py::TestManagedGrammar::test_store_managed_marker_elaborates_to_attr
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_non_managed_node_with_mismatched_boundary_still_fires
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_with_same_shape_discharges
- tests/unit/strata/test_managed.py::TestManagedDischargeFromParsedSurfaceSource::test_managed_node_still_requires_a_discharging_claim
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_managed_node_owned_files_produce_no_violation
- tests/unit/strata/test_managed.py::TestManagedTier2ImportConformance::test_non_managed_node_with_same_shape_still_violates
attachments: []
acceptance: []
threat: null
```
logand.app pilot: docs/strata/surface.md names a planned managed marker for pure-config infrastructure nodes (e.g. a Caddyfile-configured edge) but the grammar does not implement it, so config-only nodes cannot be honestly modeled without fake code bindings. Same doc-grammar drift class as T-0166. Either implement managed (parse -> elaborate -> conformance treats the node as having no scannable code by declaration, with the audit reporting it as managed rather than unmodeled) or correct surface.md; doc and grammar must agree.

## Done report

Changed:
- strata-core/src/parse.rs::Parser::parse_node (managed bare marker, node_prop)
- strata-core/src/parse.rs::Parser::parse_store (managed bare marker, store_prop -- store is a node too per surface.md#key-construct-semantics)
- src/frob/strata/_ast.py::NodeDecl.is_managed
- src/frob/strata/_ast.py::StoreDecl.is_managed
- src/frob/strata/_elaborate.py::_elaborate_node (managed -> "managed" node attr, mirrors _ABSTRACT_ATTR)
- src/frob/strata/_infra.py::_elaborate_store (managed -> "managed" node attr)
- src/frob/strata/_code_binding.py::is_managed (new public helper)
- src/frob/strata/_code_binding.py::check_import_conformance (skips a managed node's owned files, same as FOREIGN)
- src/frob/strata/_threat.py::_check_one_discharge (managed node skips the boundary-KIND `_mitigation_is_chokepoint` proof, same exemption an assumed claim already gets -- the claim still has to exist and prove a chokepoint shape)
- docs/strata/surface.md (node_prop/store_prop grammar gains `managed`; added `<a id="key-construct-semantics">` anchor -- was referenced nowhere before, so no `frob:doc` pointed at it validly until now)
- editors/vscode-strata/syntaxes/strata.tmLanguage.json (clause-keywords gains `managed` -- tmLanguage drift-lock test caught the omission on first run, fixed per its own failure message)

Resolution of ambiguity: surface.md's only normative sentence on `managed` was "marks external infrastructure (no tier-2 conformance; obligations shift to config evidence or assumes)". Interpreted minimally and operationally: (1) tier-2 code-binding conformance (`check_import_conformance`) treats a managed node's owned files like `FOREIGN` -- no crossing-import violation can fire against them; (2) THREAT003 discharge for a fired obligation on a managed node still requires an existing claim proving a chokepoint shape (`_discharges_as_chokepoint`) at or above the catalog rung, but is exempted from the stricter boundary-KIND match (`_mitigation_is_chokepoint`) a code-modeled node needs -- the SAME exemption an `assume` claim already gets, operationalizing "obligations shift to config evidence or assumes" without inventing a new claim form. This was disclosed as part of implementing rather than left ambiguous.

Evidence: fresh `pytest tests/unit/strata/test_managed.py --collect-only` (8 collected) confirms every id above resolves; `uv run pytest tests/unit/strata/test_managed.py -q` -> 8 passed; `uv run pytest tests/unit/test_strata_tmlanguage.py -q` -> 12 passed (drift-lock, confirms the tmLanguage sync).

Filed: none -- no out-of-scope work discovered. (An earlier round filed a draft ticket for the SYS100 finding below; superseded by main's own T-0201, filed independently while this ticket was in flight -- dropped my duplicate during the tickets.md merge per the ledger-conflict splice rule, kept T-0201.)

REVIEWER REJECT ROUND 1 fixes, final re-verification at delivered HEAD (commit 41d1729, main@63ba545 -- main moved four times total during this session; merged forward each time per the deletion-filter land rule):
1. E501: the `frob:waive PERF003` comment on `check_import_conformance` was 90 chars, failing ruff-check. Shortened to `# frob:waive PERF003 reason="dict-comp build plus owned-files loop, not nested"`. Re-verified clean under BOTH `uv run ruff check .` (All checks passed!) and bare `ruff check .` (All checks passed!), and BOTH `uv run ruff format --check` and bare `ruff format --check` on every file this ticket touched (7 files already formatted, both invocations) -- re-run after each subsequent merge, still clean.
2. Evidence re-run at final HEAD, exact numbers:
   - `uv run frob check`: `FAIL gates 2 violation(s), 186 waived`. The 2 unwaived: `COV003` on `tickets/T-0168:0` (a stale evidence id on unrelated ticket T-0168, not touched by T-0172) and `TEST006` (`.frob/coverage-stamp:0`, no coverage stamp -- campaign-wide pre-existing, standing instruction is never to run `make coverage`). Zero violations attributable to T-0172's diff.
   - `uv run frob test --base main`: `[PASS] python exit=0`, `[FAIL] strata exit=1` -- the strata-language suite fails ONLY on `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (5 SYS100 violations: stratamod 'fs' x2, stratamod 'deserialize'+'sql', vet 'html_render'). This is T-0201's finding ("selfconform self-match: pattern-catalog data files observed as live capabilities -- main red"). A partial T-0201 fix landed in this session's later main merges (`_selfconform.py`/`_capability.py` changed) but the test still fails with the identical 5 violations post-merge. Re-verified it reproduces on UNMODIFIED main at its CURRENT tip (worktree `/home/logan/projects/frob`, commit 63ba545, clean working tree): `cd /home/logan/projects/frob && uv run pytest tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant -q` -> same `FAILED`, same 5 SYS100 violations logged. T-0172 touches none of T-0201's scope (`_selfconform.py`, `_effects.py`, `_capability.py`) and this failure is not new, not caused by, and not fixable within T-0172's declared scope -- NOT mine to fix here.
   - `git diff main --diff-filter=D --stat` -> empty at final HEAD.

NOT closing this ticket per workflow instruction (review-gated; leave for reviewer/closer).

<!-- ticket:T-0173 -->
```yaml
id: T-0173
title: sys audit output repeats identical WARNING blocks across all views
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/sys_runner.py
- src/frob/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: the same WARNING blocks print once per configured view (8x duplication), burying the per-view differences that matter. Deduplicate: print shared findings once with a views-affected annotation, keep per-view sections for view-specific results only. Snapshot-test the output shape.

<!-- ticket:T-0174 -->
```yaml
id: T-0174
title: waiver mechanism for sys-audit findings (SYS/THREAT rules) analogous to frob:waive
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- design/**
- docs/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: check-gate violations have frob:waive with written reasons, but sys-audit findings (SYS100-102, THREAT002/003) have no waiver channel -- external repos must either fix immediately or live with permanent red, which pushes toward gaming the model instead of honest debt. Design the analog: an in-design waive/accept declaration (surface syntax on the node/claim, e.g. an accept clause with a mandatory reason string and optional ticket ref -- reuse the assume claim machinery where it already fits rather than a parallel channel), surfaced in audit output as WAIVED with the reason, counted separately, drift-locked so reasonless or stale waivers fail. Must satisfy the same discipline as frob:waive: narrowly scoped, reason mandatory, loud in output.

<!-- ticket:T-0176 -->
```yaml
id: T-0176
title: 'frob ticket land: one-command landing (merge-check-splice-close-commit)'
state: in-progress
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0162
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- docs/modules/tickets.md
- tickets.md
evidence:
- tests/test_ticket_land.py::TestSpliceLedger::test_disjoint_ids_both_kept
- tests/test_ticket_land.py::TestSpliceLedger::test_same_id_newer_state_wins
- tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
- tests/test_ticket_land.py::TestLand::test_real_land_lands
- tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main
- tests/test_ticket_land.py::TestLand::test_refuses_without_evidence_or_done_report
- tests/test_ticket_land.py::TestStaleBaseDeletion::test_unowned_deletion_aborts_loudly
- tests/test_ticket_land.py::TestStaleBaseDeletion::test_scoped_deletion_is_allowed
- tests/test_ticket_land.py::TestLedgerBothSidesAppend::test_both_sides_append_merges_cleanly
- tests/test_ticket_land.py::TestDraftIdFinalization::test_draft_id_finalized_on_land
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
- tests/test_ticket_land.py::TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean::test_code_directive_rewritten_and_worktree_clean_after_land
- tests/test_ticket_land.py::TestArchiveResurrection::test_archived_id_never_resurrected
attachments: []
acceptance: []
threat: null
```
The landing procedure is manual coordinator surgery repeated per ticket: wip-commit in the worktree, merge main, deletion-filter check (git diff main --diff-filter=D must be empty of unowned files), squash-apply, ledger splice on conflict, close with evidence validation, conventional commit. Implement frob ticket land <id> --worktree <path> doing the whole chain atomically with a dry-run mode: refuses on a dirty main, runs the deletion check and ABORTS loudly listing unowned deletions (the stale-base guard), auto-splices tickets.md keeping newest state per ticket section, finalizes provisional ids via the T-0162 mechanism (hence blocked_by), closes the ticket (evidence+done-report validation as today), and commits with a message template. Every abort path must name the exact manual remedy. Tests: fixture repo with a worktree simulating the real incident classes from this session (stale base deleting landed features, ledger both-sides-append conflict, id finalize).

## Done report

Changed:
- src/frob/tickets/_land.py (new): `land()`, `splice_ledger()`, plus private
  helpers (`_newer`, `_porcelain_dirty`, `_conflicted_files`, `_in_scope`,
  `_validate_closeable`, `_abort_merge`, `_splice_and_stage`,
  `_merge_main_into_worktree`, `_unowned_deletions`, `_wip_commit`,
  `_commit_message`).
- src/frob/tickets/_models.py: added `LandError` (ErrorSet), `LandReport`
  (BaseModel).
- src/frob/tickets/__init__.py: exported `land`, `splice_ledger`,
  `LandError`, `LandReport`.
- src/frob/app/ticket_runner.py: `_land` CLI handler, dispatch table entry,
  usage string, module docstring.
- src/frob/app/config.py: `AppConfig.ticket_worktree` field, wired through
  `from_external`'s path-field list.
- src/frob/__main__.py: `frob ticket land <id> --worktree <path>
  [--dry-run]` argparse registration (outside T-0176's declared scope --
  see Filed below; SCOPE001 waived there with a named remedy).
- docs/modules/tickets.md: new "## `frob ticket land`" section (full
  step-by-step order-of-operations rationale, why validation runs before
  any git mutation, why tickets.md is always resolved via `splice_ledger`
  rather than git's textual merge) plus updated the provisional-ids
  section's "not wired up yet" language now that T-0176 wires it.
- tests/test_ticket_land.py (new): `TestSpliceLedger` (id-level merge:
  disjoint ids both kept, same-id newest-state-wins), `TestLand` (dry-run
  leaves zero trace on both checkouts, real land merges+closes+commits,
  refuses on dirty main, refuses without evidence/Done report before any
  git mutation), `TestStaleBaseDeletion` (unowned deletion aborts loudly
  and unwinds the merge; scoped deletion is allowed), `TestLedgerBothSidesAppend`
  (main and the worktree each independently append a new ticket --
  resolves as keep-both, not a conflict), `TestDraftIdFinalization` (a
  T-draft-* id filed off-branch is finalized to a real sequential id at
  land time). All against real git fixture repos (subprocess `git
  worktree add`), not mocks.
- tests/system/test_cli_ticket_land.py (new): `TestLandCLI` -- the real
  `frob ticket land ... --dry-run` subprocess entrypoint end to end.

Verification performed manually beyond the automated suite: a live
`/tmp` smoke test creating a real worktree, filing a draft-id ticket,
running `frob ticket land <draft-id> --worktree <wt> --path <main>`
(no --dry-run) and confirming the draft finalized to T-0001, the file
landed, the ticket closed to `done`, and a `feat(tickets): land T-0001 ...`
commit was created on main -- matches the automated
`TestLand::test_real_land_lands` coverage.

Design notes on the three named incident classes:
- Stale-base deletion: `land` merges main into the worktree FIRST (so the
  worktree's tree already reflects main's current state), then diffs the
  worktree against main with `--diff-filter=D`; any deleted path outside
  the ticket's declared `scope` aborts loudly and unwinds the staged
  merge (`git merge --abort`), naming the exact restore command.
- Ledger both-sides-append: `tickets.md` is NEVER resolved via git's
  line-level merge. Every merge/squash step (main-into-worktree,
  worktree-into-main) always recomputes `tickets.md` via `splice_ledger`,
  an id-level union that keeps a ticket present on only one side
  unconditionally and picks the newer state (state-machine rank, then
  Done-report presence, then evidence count) on a genuine same-id
  divergence.
- Id finalization: `finalize_draft` (T-0162's mechanism, previously
  wired to nothing) is now called automatically inside `land`, against
  the worktree's post-merge view, before close.

Ordering (why close-validation runs first): `_validate_closeable` checks
evidence + Done report BEFORE any git mutation. This matters because
`frob ticket close` (`transition(..., DONE)`) enforces the same
precondition -- if `land` merged first and validated last, a missing
Done report would be discovered only after main-affecting state had
already changed, forcing a manual unwind. Checking first means a failed
precondition is always a no-op abort. `--dry-run` runs every check AND
every git mutation the real run would (staged merge, real deletion diff,
real splice) then unwinds it (`git merge --abort` / `git reset --hard`),
so a clean dry run is a guarantee, not a simulation that could diverge
from reality.

Evidence: 11 pytest node ids (see evidence: list above), all collected
fresh via `frob ticket evidence T-0176 ...` against a live `frob test`
collection. Full suite (`uv run frob test . --all`) and
`uv run frob test . --base main` both pass; `uv run frob check
--ticket T-0176` is 0 errors (269 pre-existing warnings, unrelated to
this ticket's scope).

Filed: T-draft-4032e080 ("T-0176 scope gap: src/frob/__main__.py missing
from declared scope") -- T-0176's declared scope omitted
`src/frob/__main__.py`, but the CLI argparse registration for any new
`frob ticket` subcommand lives there (as it did for T-0162, whose scope
explicitly included it). `land` could not be invoked from the CLI without
that file's change, so the addition was made and waived (`frob:waive
SCOPE001` at src/frob/__main__.py:2, reason names the filed ticket)
rather than expanding T-0176's scope unilaterally.

Gates: `uv run frob check --ticket T-0176` clean (0 errors); no other
waivers introduced beyond the one SCOPE001 waiver named above.

## Fix round (reviewer REJECT, addressed)

Reviewer found two reproducible CRITICAL bugs, both fixed in
src/frob/tickets/_land.py (commit 6aaa0e1):

1. Draft-id finalization losing code rewrites. `finalize_draft` ->
   `renumber_one` rewrites tickets.md AND every source file carrying a
   `frob:ticket <draft-id>` directive, uncommitted, directly on the
   worktree's working tree. The old `land` squashed onto main from the
   worktree branch's LAST COMMIT, which predated those uncommitted
   writes -- the ledger recovered only because `_splice_and_stage`
   re-reads tickets.md off disk, but every OTHER rewritten code file
   never reached main, and the worktree was left dirty even after a
   "successful" land. Fix: `land` now commits finalize_draft's and
   close's working-tree changes in the worktree (one
   "finalize and close <id> for landing" commit) BEFORE the squash-apply,
   so the squash's source (the branch's now-current tip) actually
   contains everything, and the worktree ends up clean.
2. Archive resurrection. `splice_ledger` only ever parsed the two active
   `tickets.md` texts handed to it, never `tickets-archive.md` -- an id
   main had already archived (moved out of the active ledger) after the
   worktree's branch point would survive the ours/theirs union (present
   on the worktree's still-active, stale side) and land straight back
   into main's active ledger, resurrecting the exact active+archive
   duplicate-id class this ticket's own 0bb02cf merge had to be
   hand-resolved for. Fix: `splice_ledger` takes an `archived_ids`
   parameter and drops any id in it from the merged result
   unconditionally, from either side; `land` sources `archived_ids` from
   main's `tickets-archive.md` (via the new `_archived_ids` helper) at
   BOTH splice points (main-into-worktree, and the final squash-apply
   splice onto main).

New evidence (2 fixture tests, both reproduce the reviewer's exact repro
before failing without the fix, and pass with it):
- `TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean::test_code_directive_rewritten_and_worktree_clean_after_land`
  -- a draft-id ticket with a `frob:ticket <draft-id>` directive in a
  real code file; asserts the landed file on main carries the FINAL id
  (never the draft), and that both the worktree and its own copy of the
  file are left completely clean/rewritten after land.
- `TestArchiveResurrection::test_archived_id_never_resurrected` -- a
  ticket archived on main strictly after the worktree branched (so the
  worktree's own ledger still has it active); asserts land never
  reintroduces it into main's active ledger and it remains present
  exactly once, in the archive.

Re-verification after the fix: full `uv run frob test . --all` passes
except one PRE-EXISTING failure unrelated to this ticket
(`tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`,
five SYS100 capability-declaration violations all against
`src/frob/strata/_cve_fingerprint.py` and `vet`'s `sql`/`html_render`
capabilities -- files this ticket never touches; confirmed present on
main after merge, not introduced here). `uv run frob test . --base main`
(touched-set) is clean. `uv run frob check --ticket T-0176` is 0 errors
in-scope (the same pre-existing T-0168 COV003 as before the fix round,
confirmed present before this ticket's changes too). Deletion-filter
check against main (`git diff main --diff-filter=D --name-only`) is
empty.

Merged main four times total during this fix round as it kept moving
(T-0153/T-0181/T-0205, an archive rotation, T-0208..T-0219 filing, and
T-0172's managed-marker feature); every `tickets.md` conflict was
resolved by hand using the now-archive-aware `splice_ledger` itself
(dogfooding the fix), confirmed no active/archive duplicate ids resulted
each time (`frob ticket show T-0176` and the full ledger load both
clean). Final state re-verified against main tip 47ce4e3: deletion-filter
check empty, `frob test --base main` clean, `frob check --ticket T-0176`
0 errors in-scope (same pre-existing T-0168 COV003, unrelated).

<!-- ticket:T-0177 -->
```yaml
id: T-0177
title: 'frob serve daemon: incremental gate evaluation over the warm obligation graph'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/serve/**
- src/frob/gates/**
- src/frob/graph/**
- src/frob/app/**
- pyproject.toml
- Makefile
- tests/**
- docs/modules/serve.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
frob serve is already a FastMCP stdio server with 5 read-only tools (doable tickets, stale docs, graph query, doc-for, check-scope) and is now wired into the coordinator's MCP config. Grow it into the structural fix for test-wait latency: the obligation graph knows exactly which obligations a diff can invalidate (frob test --base already proves the touched-set concept for tests) -- exploit it for gates. Deliverables: (1) warm state: the daemon holds the parsed graph snapshot, collected test ids, and the stamped violation baseline, refreshing incrementally on file-change (mtime/content-hash walk, reuse the .frob sqlite cache) instead of cold-parsing per invocation; (2) frob_check_delta MCP tool: given a base ref or dirty set, evaluate ONLY the obligations whose inputs changed and return the violation delta against the stamped baseline, in seconds; (3) frob_run_touched_tests tool wrapping the existing touched-set selection; (4) correctness guarantee: incremental results must provably match a cold frob check -- add a verification mode that runs both and diffs, plus property tests for the invalidation logic (an obligation NOT re-evaluated must have had no changed inputs -- vacuous-pass doctrine applies to the cache); (5) packaging: mcp becomes a proper [serve] extra in pyproject (mirroring [smt]) with _require_mcp's remedy message updated; Makefile install-tool already passes --with mcp -- reconcile with the extra; (6) docs/modules/serve.md updated with the daemon lifecycle and the staleness/correctness contract. Sequence AFTER the T-0148 sweep lands (gates code moves under it).

<!-- ticket:T-0178 -->
```yaml
id: T-0178
title: 'agentic time profiling: non-gated breakdown of where development time goes'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/tickets/**
- src/frob/stats/**
- scripts/**
- docs/modules/stats.md
- docs/guides/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Diagnostics ONLY -- explicitly NOT a gate family: no rule ids, nothing fails on these numbers, report-only (user directive: for designing tooling around, never for gating). Deliverables: (1) frob CLI entry timing hook -- every frob invocation appends {iso_ts, subcommand, args_head, duration_ms, exit, tree_hash} to .frob/telemetry.jsonl (local-only, already gitignored via .frob/, opt-out env var FROB_NO_TELEMETRY); reuse the per-gate timing frob check already computes by logging it structured instead of display-only. (2) ISO timestamps on ticket state transitions (created/started/done currently date-only) so per-ticket cycle time is computable. (3) EXTERNAL TOOL COVERAGE: ship a Claude Code PostToolUse hook script (scripts/frob-telemetry-hook + docs/guides page with the settings.json snippet) that appends every harness tool invocation -- Bash command head, duration, exit -- to the same telemetry stream; hooks fire for subagents too, so implementer/reviewer runs are covered without per-tool shims; document an optional PATH-shim mode for profiling outside the harness. (4) frob stats --agentic report over the merged stream: per-ticket cycle time and review-round count (parse Done-report addenda), command-time breakdown by category (frob-check / test-suite / native-build / vcs / other), top wall-clock sinks, and RETREAD DETECTION -- identical command+tree_hash re-runs counted as cache-hit candidates, which directly quantifies the T-0177 daemon payoff before it is built. (5) coordinator flow: document attaching the harness usage block (tokens, tool_uses, duration per dispatch role) at ticket close via the existing frob ticket attach, so cost history survives sessions. Privacy: telemetry never committed, never networked, redact anything matching the T-0157 secrets patterns before writing the command head. Tests: hook script emits valid JSONL under fake invocations; stats aggregation over a fixture stream; redaction case.

Addendum (user, 2026-07-18) -- TOKENS as a first-class dimension beside
time: (a) per-tool-call token cost -- the PostToolUse hook also records
an output-size token estimate (len/4 heuristic is fine; note the method)
for every tool result, since tool OUTPUT is what silently consumes agent
context: the report must rank tools by cumulative output tokens (e.g.
'frob check dumps cost N tokens/run x M runs') to identify which tools
need quieter output modes or pagination; (b) per-development-stage
attribution -- bucket both time and tokens by lifecycle stage, using the
telemetry markers already present in the stream (frob ticket start ->
first edit -> first test run -> evidence recording -> done report) and
by dispatch role (implement / review / rework round N / land), so the
report answers 'what does a REJECT round cost in tokens and minutes'
with measured numbers; (c) the coordinator-attached harness usage block
(subagent_tokens, tool_uses, duration per dispatch) is the ground truth
to reconcile the per-call estimates against -- report both and the
discrepancy.

Addendum 2 (user, 2026-07-18) -- PER-TEST TIMING ANNOTATIONS: track
per-test wall-clock as a Gaussian running estimate (Welford mean/sd/n,
persisted in .frob telemetry keyed by pytest node id, fed by the
existing test-run machinery). Write the estimate as a comment annotation
on the test itself (e.g. `# frob:perf mean=12.4s sd=1.1 n=9` above the
test def), updated ONLY when the new mean shifts beyond 2 sigma from
the annotated value -- statistical update to avoid diff churn, never
per-run rewrites. Consumption: frob test / frob check gain a fast mode
that SKIPS tests whose annotated mean exceeds a configured threshold,
and skipping is LOUD (summary names every skipped-slow test and its
annotated cost); the full check always runs everything -- fast mode is
an explicit opt-in, never the default for release/CI gates (vacuous-pass
doctrine: a skipped test must be visible, and the full gate is the
authority).

<!-- ticket:T-0179 -->
```yaml
id: T-0179
title: 'TTY-aware pretty output: colors and formatting across all frob commands'
state: queued
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Bake consistent pretty formatting and color into frob's terminal output for TTYs, skipped cleanly when non-TTY. Build on the existing src/frob/logging/color.py should_color machinery -- single source of truth, honoring isatty, NO_COLOR, FORCE_COLOR, and a [tool.frob] override. Apply across the surfaces users actually read: frob check tool/gates summary (pass/fail coloring, aligned columns, per-gate timing dimmed), frob sys audit (PROVED green, GAP red, view sections), frob ticket list/doable (state-colored ids), frob vet reports (severity coloring), frob stats. HARD CONSTRAINT: non-TTY output must remain byte-stable plain text -- agents, CI, and this repo's own snapshot tests parse it; add tests locking both modes (force-color golden and plain golden) so pretty mode can never leak ANSI into piped output. No new heavyweight dependency without written justification (prefer hand-rolled ANSI via the existing color module over adding rich).

<!-- ticket:T-0180 -->
```yaml
id: T-0180
title: 'closed-world unknown-import accounting: vetted-library cache engine (T-0158
  addendum 2 remainder)'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**,tests/**,docs/modules/vet.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0158 shipped the single-source dangerous-operations registry, the (kind x language) coverage matrix with 0 unexcused cells, and the sys-audit matrix-verdict proof line. NOT shipped (too large for one pass, explicitly deferred per T-0158's own escape valve): addendum 2 deliverable (2), full CLOSED WORLD accounting -- resolving every third-party import in a vetted dependency's source to (a) a registry entry, (b) a VETTED library (same scanner engine run over the installed third-party source, cached per package+version, e.g. reusing the frob.vet._cache.py sqlite pattern), or (c) a LOUD 'unknown, unvetted, uninspected' failure -- with the audit accounting line (N registry ops, M vetted libraries, K explicit no-capability entries, 0 unknown) T-0158's addendum 2 describes. T-0158's sys-audit line covers the (kind x language) MATRIX proof only, not this import-resolution closed-world proof. Needs: an import-graph walk per vetted package (python ast.parse imports at minimum), a resolution function classifying each imported name against DANGEROUS_OPERATIONS/registry libraries vs NO_CAPABILITY_MODULES vs unresolved, and a persistent per-package+version cache keyed like _cache.py's verdict cache.

<!-- ticket:T-0181 -->
```yaml
id: T-0181
title: survey-prioritized third-party python/npm/cargo dangerous-surface registry
  entries (T-0158 addendum 2 remainder)
state: done
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability_registry.py
- tests/**
- docs/modules/vet.md
- tickets.md
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_operations
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_absent_from_benign_source
attachments: []
acceptance: []
threat: null
```
T-0158 shipped python stdlib coverage (subprocess/os/pickle/marshal/shelve/ctypes/importlib/eval+compile/socket+http+urllib+requests/httpx/aiohttp/sqlite3/asyncio/pty/multiprocessing) plus the common third-party python net clients (requests/aiohttp/httpx) already folded into the base table. NOT shipped: the addendum 2 (3) REAL-WORLD PRIORITY list's remaining survey items -- pydantic, fastapi, numpy, cryptography, jinja2, python-dotenv, uvicorn, sqlalchemy, asyncpg, alembic, redis, boto3, stripe, anthropic, argon2-cffi, aiosmtpd, playwright, Pillow (python); react/react-dom, vite/vitest, playwright, openapi-typescript, eslint tooling (npm); pyo3, serde/serde_json, tracing, libloading, wasm-bindgen, crossbeam, thiserror (cargo). Each needs its own DangerousOperation entries (or an explicit 'no dangerous surface, pure library' NO_CAPABILITY-style entry) surveyed against its actual API surface, not guessed. Left for a dedicated per-library-survey pass; T-0158's Done report has the full reasoning for why this was cut, not silently dropped.

## Done report

Changed:
- src/frob/vet/_capability_registry.py::DANGEROUS_OPERATIONS (17 new entries)
- src/frob/vet/_capability_registry.py::CAPABILITY_MATRIX_EXCUSES (removed the
  now-stale python/html_render excuse: jinja2's autoescape=False entry
  patterns that cell)
- docs/modules/vet.md (new "Third-party library survey (T-0181)" section)
- tickets.md::T-0181 (scope field fixed twice: first the ticket was filed
  with the three scope globs joined into one comma-separated string element
  instead of three list items, which SCOPE001 could not parse as separate
  globs -- corrected to a 3-item YAML list. A reviewer then caught that
  tickets.md itself (this Done report, the scope edit) is edited by every
  ticket in this workflow but was never in T-0181's own declared scope,
  so SCOPE001 still fired on tickets.md -- added tickets.md as a fourth
  scope entry, then re-ran `frob ticket sweep T-0181` so PRE001's recorded
  sweep covers the corrected scope)

Every T-0158-addendum-2 library disposed of (full table in
docs/modules/vet.md "Third-party library survey (T-0181)"):
- patterned (new DangerousOperation entries): numpy (allow_pickle
  deserialize), jinja2 (SSTI eval + autoescape=False html_render),
  python-dotenv (env), uvicorn (net), sqlalchemy (text() sql), asyncpg
  (net), boto3 (net), stripe (net), anthropic (net), aiosmtpd (net),
  playwright python+npm (exec browser-launch + eval page.evaluate),
  Pillow (ImageMath.eval, eval), pyo3 (ffi), wasm-bindgen (ffi)
- pure / no dangerous surface (documented, not silently dropped): pydantic,
  fastapi, cryptography, alembic, argon2-cffi (python); react/react-dom,
  vite/vitest, openapi-typescript, eslint tooling (npm); serde/serde_json,
  tracing, crossbeam, thiserror (cargo)
- already covered pre-T-0181: libloading (rust/ffi, T-0158)
- honest gap (tracked, not claimed covered): redis's EVAL Lua-script
  idiom has no client-name-independent literal substring pattern without
  unacceptable false-positive risk; redis's connection surface is not
  separately patterned (subsumed by the same net reasoning as
  requests/httpx/asyncpg -- no dedicated redis entry added since it adds
  no new detection over the existing net cell); Pillow's decompression-bomb
  DoS has no matching capability_kind in this registry

Evidence:
- tests/test_capability_registry.py (all 200 tests, incl. the T-0182
  per-operation fire+negative parametrization over every DANGEROUS_OPERATIONS
  entry including the 17 new ones -- their needles[0] genuinely fire
  scan_file_operations/scan_file_capabilities and are absent from the
  language's benign-source negative fixture)
- tests/test_vet.py (full pass, no regression)
- `uv run frob test --base main` touched-set selection: python exit=0
  (tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes,
  tests/test_capability_registry.py::TestMatrixExhaustiveness::test_every_operation_kind_and_language_registered,
  tests/test_capability_registry.py::TestNoSilentNeedleRegression -- all 3)
- `uv run frob check --ticket T-0181` (fresh run after the 4-item scope
  fix + `frob ticket sweep T-0181` re-sweep, main re-merged first): grep
  over the full output for `SCOPE001` and `PRE001` returns zero hits --
  both gates the reviewer flagged are confirmed clear, not merely claimed.
  ruff-check/ruff-format clean.

Filed: none (redis EVAL and Pillow decompression-bomb gaps recorded above
as honest limits in docs/modules/vet.md, not filed as separate tickets --
consistent with T-0158's own "Honest limits" documentation style)

Gates: `frob check --ticket T-0181` -- SCOPE001 and PRE001 both absent
from the fresh run (verified by direct grep, not inference). The 14
residual `[gates]` violations plus `ty`'s "Found 2 diagnostics" are ALL
pre-existing and outside this ticket's scope/diff:
  - COV003 x13 on tickets/T-0065, T-0148, T-0168 (stale test-collection
    ids on unrelated closed tickets; "run: frob test --collect to
    refresh" per the gate's own message -- not caused by this change,
    and `make coverage`/collect-refresh is explicitly out of scope per
    instructions)
  - TEST006 x1 on .frob/coverage-stamp (no coverage stamp; `make
    coverage` intentionally never run per instructions)
  - `ty`: 2 diagnostics, both `frob_core` unresolved-import in
    tests/unit/test_dup_core.py -- native-extension worktree
    artifact, not touched by this ticket's files
None of the above name `_capability_registry.py`, `docs/modules/vet.md`,
or `tickets.md`.
(Coordinator note at landing: the review's second round found one stale
"SYS004 x1" line in this enumeration -- absent from the fresh run; removed
here per the reviewer's named remedy. Enumeration now matches the tool
output the reviewer independently verified: COV003 x13 + TEST006 x1 + ty x2.)

<!-- ticket:T-0187 -->
```yaml
id: T-0187
title: 'frob dup bleeding-edge: algorithm survey, reverse-templating abstraction,
  exhaustiveness meta-test'
state: in-progress
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/dup/**
- frob-core/**
- tests/**
- docs/modules/**
- docs/index.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User mandate 2026-07-18: frob dup does the basics (R1-R6 rungs: winnow, WL-hash, candidate_pairs, tree_edit in frob-core; statement-Levenshtein; co-occurrence CFG/DFG proxy) but must be bleeding-edge. Phase 1 RESEARCH (exhaustive-researcher): map the clone-detection state of the art against our implementation -- APTED exact tree edit distance, SourcererCC bag-of-tokens overlap, Oreo metrics-based type-3/4, NiCad normalization+abstraction, DECKARD characteristic vectors, learning-based (ASTNN, FA-AST GNN, CCLearner) with honest feasibility calls for a no-model-dependency tool, cross-language clone detection, and ANTI-UNIFICATION / reverse templating: report each clone group with its abstracted template plus per-instance bindings (the shared skeleton with holes), so the fix suggestion is the extracted function signature, not just 'these are similar'. Phase 2 DESIGN+TICKETS: planner converts the survey into an implementation ticket tree (rust-kernel work vs python orchestration split explicit). Phase 3 META-TEST: exhaustiveness drift-lock in the T-0158/T-0182 mold -- a registry of detectors/rungs/clone-types, parametrized litmus fixtures proving every (clone type 1-4 x supported language x rung) cell either fires on a minimal fixture pair or carries a written exclusion; adding a detector or claiming a clone type without a firing fixture fails the suite. Acceptance: survey doc committed, ticket tree filed, meta-test green over the CURRENT detector set before any new detector lands.

<!-- ticket:T-0188 -->
```yaml
id: T-0188
title: 'catalog: add CWE-295 (improper cert validation) WeaknessEntry to unblock TLS
  verify=False fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: spoofing
```
T-0153 review follow-up: the TLS verify=False fingerprint class was correctly cut because no CWE-295 WeaknessEntry exists in CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG and the CVEFP001 drift-lock (rightly) refuses fingerprints citing absent CWEs. Add the catalog row (with honest views placement), then the fingerprint entry (requests/httpx/aiohttp verify=False, node tls rejectUnauthorized false, rust danger_accept_invalid_certs), litmus positive/negative source tests per T-0153's pattern. Also reconcile CWE-916 (mentioned in _cve_fingerprint.py docstring but in neither catalog nor cut-class list) -- add it or fix the docstring.

<!-- ticket:T-0189 -->
```yaml
id: T-0189
title: 'catalog: add CWE-611 (XXE) WeaknessEntry to unblock XML external-entity fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
T-0153 review follow-up: XXE fingerprint class cut because no CWE-611 WeaknessEntry exists and CVEFP001 refuses fingerprints citing absent CWEs. Add the catalog row, then the fingerprint entry (python lxml etree.parse with resolve_entities, xml.sax without feature_external_ges disabled, java-style patterns out of scope -- only supported languages), litmus positive/negative tests per T-0153's pattern.

<!-- ticket:T-0190 -->
```yaml
id: T-0190
title: secrets-gate fixtures trip GitHub push protection -- main is unpushable
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/test_secrets_gate.py
- src/frob/gates/_secrets.py
- docs/modules/gates.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
GH013 push protection rejects main: the Stripe fixture at tests/test_secrets_gate.py:49 (landed in 48aeed1, T-0157) is realistic enough for GitHub secret scanning despite T-0157's clearly-fake requirement. Every push of main is blocked until resolved. Fix has two parts: (1) make every fixture structurally un-flaggable by GitHub (pattern-invalid tail: wrong length/charset/checksum for the provider) while still firing frob's own gate -- if frob's format constraint is currently so strict that only GitHub-flaggable strings can fire it, LOOSEN the fixture-facing constraint or add a test-only needle path, disclosed; (2) meta-test: fixtures must not match GitHub's published secret-scanning patterns (encode the Stripe/AWS/GitHub-token formats we know) so a future fixture cannot re-trip push protection. REMEDIATION for the already-flagged blob (coordinator step, not this ticket): after all in-flight branches merge, rewrite the unpushed range to replace the flagged fixture in 48aeed1 itself (remote tip predates it, so no force-push needed), or the user may use the GitHub unblock URL instead. This ticket only makes the CURRENT tree safe and drift-locked.

<!-- ticket:T-0191 -->
```yaml
id: T-0191
title: wire DUP001/DUP002 smart-dup rules into frob check gates -- pipeline currently
  inert
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/gates/**
- src/frob/dup/**
- frob.toml
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey finding (dup-sota-survey.md sec 0/3.1): DUP001/DUP002 are pure rule functions never invoked from frob.gates.__init__; frob check still runs only the legacy Type-1/2 scanner, so the whole R1-R5 smart pipeline never gates a build. Wire the clones gate to the smart pipeline behind the existing opt-in leaf, fixture tests proving a planted R3/R4 clone fails check when enabled and passes when waived. Highest priority of the T-0187 tree: everything else is inert until this lands.

<!-- ticket:T-0192 -->
```yaml
id: T-0192
title: frob dup --probe CLI flag reaching probe_equivalence (R6) -- closes T-0041
  debt
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- src/frob/app/**
- src/frob/__main__.py
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
R6 probe_equivalence is fully implemented and unreachable (no --probe string anywhere under the CLI, confirmed by survey). Wire the flag, document the workload contract, CLI-level test.

<!-- ticket:T-0193 -->
```yaml
id: T-0193
title: 'R1.5 exact-region kernel: generalized suffix automaton over normalized token
  stream'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey item 16 ADOPT: R1/R2 hash whole symbol bodies only, so partial copy-paste regions inside otherwise-different functions are invisible today. New frob-core kernel; region output feeds the existing CloneRegion model; cargo tests + python-side fixtures.

<!-- ticket:T-0194 -->
```yaml
id: T-0194
title: 'anti_unify kernel: Plotkin lgg over (labels,parents) node arrays'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: lockstep top-down walk emitting shared nodes and $hole_N at divergence, returning template arrays + binding index pairs; reuses the node-array representation apted_similarity already consumes. Cargo tests incl. hole-ceiling sanity (>50 pct holes = Err back to plain pair).

<!-- ticket:T-0195 -->
```yaml
id: T-0195
title: 'reverse-templating report: CloneTemplate/CloneBinding models, extraction-signature
  synthesis in DUP001 messages'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by:
- T-0194
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: frozen pydantic CloneTemplate/CloneBinding, CloneReport.groups[].template optional, signature synthesis one param per distinct hole (reuse identifier when both instances agree), DUP001 violation message gains the suggested extraction. The violation hands you the fix, not a percentage.

<!-- ticket:T-0196 -->
```yaml
id: T-0196
title: 'R5 fidelity: real control-flow edges from frob.lang where available, proxy
  demoted to true fallback'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- src/frob/lang/**
- frob-core/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 7/8 ADAPT: verify frob.lang actual CFG-edge coverage FIRST (the survey flags this VERIFY), then follow R4 established two-tier pattern (real primary, proxy fallback for unparseable symbols). Disclose per-language coverage honestly in dup.md.

<!-- ticket:T-0197 -->
```yaml
id: T-0197
title: 'candidate prefilters: DECKARD characteristic vectors + Oreo metric ratios
  + NiCad size ratio'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 2/4/6 (non-ML halves): three additive candidate-pruning stages before APTED/WL verification; prefilters only prune pairs, never add false positives -- test that enabling them never changes the verified-clone set on fixtures, only the pair count examined.

<!-- ticket:T-0198 -->
```yaml
id: T-0198
title: 'cross-language clone litmus: same logic in two grammars through the real pipeline'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- tests/**
- src/frob/dup/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey item 13: the cross-language claim rests on shared node vocabulary between frob.lang grammars but no fixture proves it. One fixture pair (python+ts same algorithm) through the REAL pipeline; if vocabulary does not align, that is the finding -- document and file rather than force.

<!-- ticket:T-0199 -->
```yaml
id: T-0199
title: 'dup exhaustiveness meta-test: (clone-type 1-4 x language x rung) matrix registry
  + litmus fixtures'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 5, user mandate: registry of detectors/rungs/claimed clone types; parametrized fixture pairs per claimed cell (fire + negative); unclaimed cells need written exclusions; a detector or clone-type claim added without a fixture fails the suite -- T-0158 capability-matrix mold. Meta-test must be green over the CURRENT detector set before any new detector lands (acceptance from T-0187).

<!-- ticket:T-0200 -->
```yaml
id: T-0200
title: add real kill-switch/feature-flag mechanism for exec/net capabilities (checker/core/stratamod/vet)
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/process/**
- src/frob/check/**
- src/frob/strata/**
- design/frob.strata
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0155's LINT004 rule (design lint family) fires honestly on design/frob.strata's checker/core/stratamod/vet nodes: each holds a risky (exec/net) may capability with no real, checked-in kill switch (env var / feature flag) an operator can flip live to disable it. T-0155 deliberately did not fabricate a flag=<id> attr naming a mechanism that does not exist (declare real facts or waive with reasons, T-0150/T-0151 precedent) -- this ticket is the follow-on product work to build the actual mechanism and then discharge LINT004 for real on design/frob.strata.

<!-- ticket:T-0201 -->
```yaml
id: T-0201
title: 'selfconform self-match: pattern-catalog data files observed as live capabilities
  -- main red'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_effects.py
- src/frob/vet/_capability.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0153+T-0181 interaction, invisible to both branches (TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant skips without strata_core natives, so it only runs on main): 5 SYS100 violations -- stratamod 'fs' x2 (_cve_fingerprint.py:120/:190 needle literals), stratamod 'deserialize'+'sql' (extended kinds from catalog needles), vet 'html_render' (T-0181 jinja2 needles in _capability_registry.py). Root cause: self-conformance scans pattern-catalog DATA files as if their needle literals exercise capabilities -- the exact T-0151 self-match class. Fix: a single shared self-match exclusion (registry + fingerprint catalog + any future pattern-table file) applied consistently in BOTH vet aggregation (_is_self_path, already done piecemeal) and the selfconform scan paths (THREAT004 core + extended kinds); one source of truth, not per-file patches. Drift-lock: a test asserting the exclusion list covers every module that defines needle tables (registry-of-pattern-files), plus the real-gate test back to green. Do NOT declare fake capabilities on stratamod/vet in design/frob.strata -- the nodes do not exercise these capabilities; excluding descriptive data is the honest fix.

<!-- ticket:T-0202 -->
```yaml
id: T-0202
title: 'frob check default output: stats summary, gate chatter to DEBUG, standardized
  log format'
state: in-progress
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- src/frob/graph/**
- src/frob/gates/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User report 2026-07-18: default frob check output is ~6K lines, mostly per-file/per-symbol debug chatter ('dispatching path=... to grammar=python', 'extracted 17 symbols...', 'digested TestGrammarRoundTrip: sig=... body=...', per-gate run_gates timing lines). These are DEBUG-level diagnostics printed at default verbosity. Fix: (1) audit every log call in graph build/digest/dispatch/gate-run paths and set honest levels -- per-file and per-symbol lines to DEBUG, per-stage one-line summaries to INFO; (2) default (non-verbose) output = the tool summary table plus violations only; -v restores current firehose, -vv adds true debug; (3) standardize the logging format across all modules per ~/.claude/refs/logging.md conventions (module logger + one formatter -- no mixed bare-print/log styles between gates, graph, vet, sys); (4) keep --json machine output untouched and clean (quiet_stdout_logs already guards it -- extend coverage if any new chatter leaks). Acceptance: default frob check on this repo emits under ~200 lines; every line above INFO is actionable.

<!-- ticket:T-0203 -->
```yaml
id: T-0203
title: 'perf_gate: silence UnsupportedLanguage skips for non-code files'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User report 2026-07-18: 'perf_gate: skipping unparsed docs/guides/agent-playbook.md: UnsupportedLanguage: File extension has no registered grammar' -- perf gate walks non-code files (markdown/json/toml) and logs a WARN-looking skip for each. Files with no registered grammar are not perf-scannable BY DESIGN: filter them out before the scan by extension (reuse the canonical language registry extension table from T-0129), log nothing at default verbosity (a single DEBUG-level count line at most). A skip message should be reserved for files that SHOULD parse but failed. Test: perf gate over a fixture tree with md/toml/json emits zero skip lines and scans only registered-grammar files.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0205 -->
```yaml
id: T-0205
title: pytest collects Test*-prefixed product classes -- set __test__ = False
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/_models.py
- src/frob/testing/_models.py
- src/frob/testing/_runners.py
- tickets.md
evidence:
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_gates.py::TestCoverageGate::test_waive002_honors_loaded_policy_rule_ids
attachments: []
acceptance: []
threat: null
```
User report 2026-07-18 (CI warnings summary): PytestCollectionWarning for gates/_models.py::TestPolicy and testing/_runners.py::TestingError -- pytest matches the Test* class-name prefix and tries to collect product classes. Fix: annotated __test__: bool = False on TestPolicy, TestingError, and TestRunReport (testing/_models.py), matching the existing precedent on process/parsers/common.py::TestCase. Verified: pytest --collect-only over tests/test_gates.py + tests/test_testing.py emits zero PytestCollectionWarning; both suites still pass.

## Done report

Changed: src/frob/gates/_models.py::TestPolicy,
src/frob/testing/_models.py::TestRunReport,
src/frob/testing/_runners.py::TestingError -- each gains
`__test__: bool = False` matching the TestCase precedent in
process/parsers/common.py. Coordinator-applied direct user request
(exact locations user-supplied); swept via frob ticket start before close.

Evidence: tests/test_testing.py::TestSelect::test_direct_hit and
tests/test_gates.py::TestCoverageGate::test_waive002_honors_loaded_policy_rule_ids
(both suites collect warning-free and pass; verified
`pytest --collect-only` emits zero PytestCollectionWarning across
tests/test_gates.py + tests/test_testing.py).

Filed: none. Gates: ruff format stable on all three files.

<!-- ticket:T-0206 -->
```yaml
id: T-0206
title: tickets-archive.md has a stale duplicate T-0169 entry from a ledger-conflict
  splice
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tickets-archive.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while merging main into the T-0169 worktree: tickets-archive.md on main contains a T-0169 block with state=queued and no Done report/evidence, silently spliced in by an unrelated ledger-conflict merge (same incident class the agent playbook's ledger-conflict splice guidance warns about) -- NOT a real close. The authoritative T-0169 record is in tickets.md (in-progress, with a full Done report). Delete the stray tickets-archive.md duplicate so frob ticket listings don't show two T-0169 records in conflicting states. Also check tickets-archive.md for other stray splices from the same merge incident. (The branch's second draft, e1beb2a8 covering the html_render self-match, was dropped at landing as a duplicate of T-0201, which carries the same analysis and is already dispatched.)

## Failure log
- 2026-07-18 attempt 1: Premise stale on main: the stray queued-state T-0169 archive duplicate existed only in the T-0169 worktree's pre-archive ledger copy (branched at 1101c3e). Current main archive (rebuilt at 0b4ff16) has zero T-0169 entries and a cross-ledger id-duplicate grep is clean. Nothing to delete.

<!-- ticket:T-0207 -->
```yaml
id: T-0207
title: 'structural PII/secrets detection: waivable checks over data structures, schemas,
  and env access'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- src/frob/vet/**
- src/frob/lang/**
- design/frob.strata
- tests/**
- docs/**
- frob.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
User mandate 2026-07-18 ('if it passes, it's safe'): extend T-0154 (PII flow proofs) and T-0157 (secrets token scan) with STRUCTURAL detection over data surfaces, every rule waivable via frob:waive with a written reason so zero-unwaived means every PII/secret surface is either declared or consciously waived. Detector families: (1) DATA-STRUCTURE FIELDS: pydantic/dataclass/TypedDict/attrs field names and types across supported languages (name keyword table: email, phone, ssn, dob, address, ip, password, token, api_key, secret, salt, card/pan/cvv...; type-based: EmailStr, SecretStr, and TS/rust equivalents) -- a detected PII-shaped field on a node without a matching T-0154 PII category declaration (or waiver) fires; declared-but-never-observed goes stale like SYS101. (2) DATABASE SCHEMA: CREATE TABLE / column DDL in migrations (alembic, raw SQL) and ORM models (sqlalchemy columns) scanned with the same keyword+type tables -- schema headers are the highest-value PII surface. (3) ENV/SECRET SOURCES: os.environ[...]/os.getenv/load_dotenv() call sites (and process.env, std::env::var) are secret-source observations that must map to declared strata secret nodes (T-0082 std.secrets) or be waived -- an unmapped env read fires. (4) EMAIL-SHAPE VALUES: detect email-shaped string literals in code/fixtures WITHOUT naive regex (user explicit: regex is bad for email matching) -- use a structural parse (local@domain.tld via a real address parser, e.g. email.utils/parseaddr semantics or the WHATWG algorithm) with the T-0157 fake-marker escape (frob:secret fake / placeholder shapes stay writable). (5) KEYWORD SWEEP: identifier/comment keyword hits at suggestion severity only (no hard fail on names alone). DISCIPLINE (non-negotiable, per registry precedent): single-source keyword/type registry (no duplication between detectors); litmus fire+discharge fixtures per detector (T-0145 style); per-entry parametrized drift-lock (T-0182 style) so a registry keyword without a firing fixture fails; exhaustiveness matrix (detector x language) with written exclusions for unpatterned cells (T-0158 style); self-match exclusion for the registry file itself designed in from day one (T-0201 lesson -- the keyword table must not detect itself); wire into frob check as a new gate family (PII0xx/SEC1xx) default-on at WARN for adoption, severity dial in frob.toml; sys audit gains the joined view (structural observations vs declared PII/secret model). Split into child tickets per detector family at plan time if needed; this is the umbrella.

<!-- ticket:T-0208 -->
```yaml
id: T-0208
title: vet obfuscation scan pathologically slow -- high_entropy_strings dominates,
  no progress/timeout
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): frob vet unusable -- lograder killed at 11m47s with 15/30 packages (101MB venv); aprog-public stuck on numpy at 120s. cProfile+SIGALRM around scan_tree(fetch=False): _obfuscation.py:70 high_entropy_strings consumed 82 of 120 profiled seconds (785 calls); tree-sitter/capability scans fine. Fix: cap candidate string count/length per file, skip literal-table files over a size threshold, optimize the entropy loop, add per-package progress lines and --timeout/--jobs. Acceptance: frob vet completes on lograder's venv under 2 minutes with progress output.

<!-- ticket:T-0209 -->
```yaml
id: T-0209
title: capability scanner matches needles inside comments and strings
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- src/frob/lang/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: SYS100 reported capability net observed at assignments/api-harvester/assets/starter.py:22 -- that line is COMMENT text describing requests.get; the assignment forbids real network imports. Forced a false may declaration dragging bogus CWE-918 obligations -- corrupts the security posture the model attests (medium-high). Fix: consult tree-sitter comment/string spans (already produced by frob.lang) before substring matching; needle hits fully inside comment spans are dropped (string literals are subtler -- keep string hits for languages where code-in-string is an exec vector, e.g. eval payloads, but drop pure-comment hits everywhere). Litmus: comment-only fixture must NOT fire; code fixture still fires; the T-0151/T-0201 self-match tests stay green. Note duplicate-line issue too: the same site was reported twice (pilot gap 12) -- dedupe observations by (file,line,kind) while in there.

<!-- ticket:T-0210 -->
```yaml
id: T-0210
title: frob test package-fallback treats pytest exit 5 (no tests collected) as FAIL
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: editing a file in a package with no tests (activities/git-heist/) makes frob test --base HEAD~1 report [FAIL] python exit=5. pytest exit 5 = collected 0 tests; the package fallback should degrade to the same neutral nothing-touched-selects-any-test outcome the empty-selection path prints. Regression test: fixture package with a source edit and zero tests -> PASS/neutral, not FAIL.

<!-- ticket:T-0211 -->
```yaml
id: T-0211
title: selfconform warns '<repo>/src/frob does not exist' in every non-frob repo
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/_selfconform.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): the warning prints in every sibling repo while self-conformance PROVED still appears; the checks DO run (verified by falsifiability probes) but the stale frob-self path assumption reads as 'this proof is vacuous' -- trust-eroding. The SYS102 unmodeled join is frob-self-specific (_PACKAGE_ROOT); it should detect it is not in the frob repo and skip silently (one DEBUG line), not warn.

<!-- ticket:T-0212 -->
```yaml
id: T-0212
title: DOC002 slugger disagrees with GitHub anchor algorithm in both directions
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/docs/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder (7 DOC002 errors, most error-prone adoption step): 'Output & layouts' -> GitHub #output--layouts vs frob #output-layouts; 'Public/Private Boundary' -> GitHub #publicprivate-boundary vs frob #public-private-boundary. Punctuation runs collapse differently, so anchors satisfying DOC002 can 404 on GitHub and vice versa. Fix: implement GitHub's slug algorithm exactly (test against a table of tricky headings) or accept both forms; T-0165's nearest-anchor suggestions must use the corrected slugs.

<!-- ticket:T-0213 -->
```yaml
id: T-0213
title: COV001 short message says 'undocumented' for symbols that have docstrings
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder: COV001 flags DeveloperException/StaffException which HAVE docstrings -- rule means 'no frob:doc edge'; long-form message is correct, short line is wrong and misleads adopters into thinking docstrings satisfy it. Align the short message with the long form.

<!-- ticket:T-0214 -->
```yaml
id: T-0214
title: COV002 close-before-commit catch-22 turns covered changes into hard errors
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: closing the covering ticket while its strata file is still uncommitted turned every symbol in the file into 'changed with no open ticket' (30 hard errors) which vanish after commit. Either honor recently-done tickets' frob:ticket references for working-tree changes (grace window until commit) or make frob ticket close warn when the covering scope still has uncommitted changes, and document commit-then-close ordering in the playbook. Relates to T-0176 land (which enforces the safe order mechanically).

<!-- ticket:T-0215 -->
```yaml
id: T-0215
title: non-pytest evidence channel for docs/design tickets + close-from-queued hint
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- docs/modules/tickets.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 10) + coordinator experience this session (T-0167/T-0185/T-0186 all needed drift-lock tests written solely to satisfy close): frob ticket close accepts only pytest node ids. Add a vetted evidence alternative for docs/design tickets -- e.g. --evidence-cmd 'command' whose exit 0 is recorded with its output digest, or gate-based evidence referencing a rule that must be absent/present -- WITHOUT weakening code tickets (kind-gated: only docs/design kinds may use it). Also: close on a queued ticket errors InvalidTransition with no hint -- name the remedy (frob ticket start) in the message. And frob ticket start on an in-progress ticket errors InvalidTransition too -- make it idempotent or hint that it is already started (coordinator hit this on T-0169).

<!-- ticket:T-0216 -->
```yaml
id: T-0216
title: graph build never names the malformed file
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: malformed=1 in build output, persists across cache flush, no way to find WHICH file (no verbosity flag on the subcommand). Print path + parse error at WARN when malformed>0. Trivial but blocks users from fixing their own files.

<!-- ticket:T-0217 -->
```yaml
id: T-0217
title: sys plan/doc log raw pre-discharge threat counts that contradict the PROVED
  verdict
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 13): 'threat: evaluated ... -> 13 violation(s)' logs right before '0 obligation tickets / PROVED' -- the 13 is the pre-discharge obligation count, not live violations. Rename the log line (obligations evaluated, N discharged, 0 residual) or demote to DEBUG; contradictory-looking output erodes trust in PROVED.

<!-- ticket:T-0218 -->
```yaml
id: T-0218
title: graph build reports edges=0 on cache-hit runs while the loaded graph has edges
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 14): build counter means newly-parsed edges, so cache-hit runs print edges=0 followed later by load_graph: ... 60 edges. Rename the counter (new_edges=) or report total after load.

<!-- ticket:T-0219 -->
```yaml
id: T-0219
title: secrets scan misses adjacent sk-live key and placeholder-phrase fakes
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/_secrets.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private (gap 15): SEC001 flagged a fake Slack token but MISSED the sk-live-... key on the adjacent line (detection gap -- the miss matters more than any false positive), and the fake-marker heuristics missed obvious placeholder phrasing ('real-slack-token-here' contains no recognized fake word). Fix both directions: audit the provider table against the fixture file that produced the miss (why did sk-live- not match -- prefix table or format constraint?), and extend placeholder recognition ('...-here', 'your-', 'insert-', 'changeme') with fixtures. Coordinate with T-0190 (GitHub-unflaggable fixtures) so new fixtures satisfy both constraints.

<!-- ticket:T-draft-4032e080 -->
```yaml
id: T-draft-4032e080
title: 'T-0176 scope gap: src/frob/__main__.py missing from declared scope'
state: queued
kind: docs
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0176's scope listed src/frob/tickets/**, src/frob/app/**, tests/**, docs/modules/tickets.md, tickets.md but omitted src/frob/__main__.py -- every prior ticket-subcommand-adding ticket (e.g. T-0162) explicitly included src/frob/__main__.py in scope, since the ticket subcommand argparse wiring lives there, not under src/frob/app/. T-0176 needed exactly that (frob ticket land's --worktree/--dry-run argparse registration) and could not deliver a usable CLI command without it. Waived SCOPE001 at src/frob/__main__.py in T-0176's commit rather than expanding scope unilaterally; this ticket exists to note the gap for future ticket-scope authoring (mechanically: any ticket adding a new frob subcommand should include src/frob/__main__.py in scope up front).
