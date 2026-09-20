---
id: T-0201
title: 'selfconform self-match: pattern-catalog data files observed as live capabilities
  -- main red'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_selfconform.py
- src/frob/strata/_effects.py
- src/frob/vet/_capability.py
- design/frob.strata
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_scan.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1197
  new_length: 4075
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_own_catalog_file_excluded_from_directory_aggregation
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0153+T-0181 interaction, invisible to both branches (TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant skips without strata_core natives, so it only runs on main): 5 SYS100 violations -- stratamod 'fs' x2 (_cve_fingerprint.py:120/:190 needle literals), stratamod 'deserialize'+'sql' (extended kinds from catalog needles), vet 'html_render' (T-0181 jinja2 needles in _capability_registry.py). Root cause: self-conformance scans pattern-catalog DATA files as if their needle literals exercise capabilities -- the exact T-0151 self-match class. Fix: a single shared self-match exclusion (registry + fingerprint catalog + any future pattern-table file) applied consistently in BOTH vet aggregation (_is_self_path, already done piecemeal) and the selfconform scan paths (THREAT004 core + extended kinds); one source of truth, not per-file patches. Drift-lock: a test asserting the exclusion list covers every module that defines needle tables (registry-of-pattern-files), plus the real-gate test back to green. Do NOT declare fake capabilities on stratamod/vet in design/frob.strata -- the nodes do not exercise these capabilities; excluding descriptive data is the honest fix.

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:681-730,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# True for this module's own source file, the T-0158 registry it compiles
# `_PATTERNS` from, or the T-0153 fingerprint catalog it matches
# `_scan_file_fingerprints` against (excluded from directory aggregation
# since all three contain every needle as literal data, guaranteeing a
# self-match unrelated to what the code does). Public (T-0201): the
# SINGLE shared self-match exclusion -- vet's own directory aggregation
# below AND every `frob.strata._selfconform`/`_effects` join path must
# call this same function rather than keep parallel private copies, or a
# future pattern-catalog file re-introduces the T-0151 self-match class
# in whichever join path forgot to exclude it. This was T-0201's root
# cause: `_selfconform.py`'s extended-kind/all-kind scans and
# `_effects.py`'s line-effect scan all predated this export and had no
# exclusion of their own.
#
# T-0253 round 1 (REJECTED): matched by `_SELF_PATTERN_SUFFIXES` (package-
# relative path suffix) alone, with no scan-target check. That closed the
# non-editable-install false positive but opened a real evasion hole: a
# malicious dependency placing a file at a path ending in
# `frob/vet/_capability.py` would be silently excluded from `frob vet`'s
# capability scan too, since suffix matching cannot distinguish "this is
# frob auditing itself" from "this is frob vetting someone else's tree
# that happens to mimic frob's layout."
#
# T-0253 round 2 (this version): `root` is now the caller's scan-target
# discriminator -- the suffix match only fires when `_is_frob_repo_root
# (root)` says `root` IS frob's own repository checkout (its own
# `pyproject.toml` name plus its `frob-core`/`strata-core` crate
# directories), never based on `path` alone and never based on where the
# RUNNING package's own files happen to live (round 0's bug, identity
# comparison against `_SELF_PATH` et al., which broke under a non-
# editable global install). `root` defaults to `None`, which ALWAYS
# fails the discriminator (fail-closed, deny-by-default, matching this
# codebase's charter posture elsewhere) -- a caller that omits `root`
# gets "never exclude, always scan" rather than a crash, so this stays
# source-compatible with any caller written against the pre-T-0253
# one-argument signature while still closing the evasion hole for every
# real caller in this repo (all of which pass `root` explicitly).
# Self-conformance callers (`_selfconform.py`/`_effects.py`) always pass
# frob's own repo root by construction, so this is a no-op there; `frob
# vet` scanning a dependency passes that dependency's own source root,
# which is never frob's repo, so the exclusion correctly never fires and
# the file is scanned like any other.