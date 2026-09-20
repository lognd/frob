---
id: T-0253
title: self-path exclusion breaks under non-editable installs -- global frob self-audit
  shows 36 false SYS100s
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
- src/frob/vet/_capability.py
- src/frob/strata/**
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
  old_length: 961
  new_length: 3996
evidence:
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0156 closing-review finding, now reproducible on main: is_self_pattern_path (T-0201) resolves the RUNNING package's module file paths, so the exclusion only matches when the scanned tree IS the running package (editable install). Under the uv-tool global binary, scanning frob's own checkout self-matches all pattern-catalog needle literals again: frob sys audit = 36 SYS100 false gaps; uv run frob sys audit = 0. Only affects auditing frob's own repo with a non-editable binary (sibling repos have no pattern files), but that is exactly what CI or a user would do. Fix: match by repo-relative path suffix of the KNOWN pattern files (src/frob/vet/_capability.py, _capability_registry.py, strata/_cve_fingerprint.py) against the SCANNED tree, not identity of the running package's files; keep the T-0201 drift-lock and extend it with a test that simulates a foreign-install scan (copy the tree to a tmp path, scan with the exclusion, assert zero self-matches).

T-4718 sweep (condensed from src/frob/vet/_capability_scan.py:100-143,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# T-0253: `_SELF_PATH`/`_REGISTRY_PATH`/`_FINGERPRINT_CATALOG_PATH` above are
# identity anchors for THIS running package's own files -- correct only when
# the scanned tree and the running package are the SAME checkout (editable
# install: `uv run frob ...`). Under a non-editable global install (`uv tool
# install frob`), the running package's files resolve to a `site-packages`
# copy, so identity comparison against a SCANNED tree that is frob's own
# repo checkout never matches and every pattern-catalog needle self-matches
# again (36 false SYS100s under `frob sys audit` vs. 0 under `uv run frob
# sys audit`).
#
# Round 1 fix (REJECTED on review): matching by bare PATH SUFFIX (the last
# three path components: package dir / subpackage / filename) with no
# further check. That closed the false-positive but opened a real hole:
# `is_self_pattern_path` is reached from `_scan_directory_capabilities`/
# `_scan_directory_fingerprints`, the SAME public entrypoints `frob vet` uses
# to scan a VENDORED/THIRD-PARTY dependency tree. A malicious dependency
# that places a file at a path ending in `frob/vet/_capability.py` (trivial:
# nest it under any vendor path, or name the package `frob` outright) would
# be silently excluded from capability scanning by suffix alone --
# `is_self_pattern_path` cannot tell "we are auditing frob's own checkout"
# from "we are vetting someone else's tree that happens to mimic frob's
# layout" using the scanned PATH alone.
#
# Round 2 fix (this one): the suffix match stays as the within-frob file
# check, but it is only REACHABLE when a separate SCAN-TARGET discriminator,
# `_is_frob_repo_root`, says the tree actually being scanned is frob's own
# repository -- not the running package's install location (round 1's
# mistake), not the scanned FILE's path alone (round 1 REJECT's mistake),
# but the scanned tree's ROOT identity: `root/pyproject.toml` declares
# `name = "frob"` AND the root also has the `frob-core`/`strata-core` Rust
# crate directories this monorepo actually ships. Requiring both the name
# and the crate directories raises the forgery bar well past "name a PyPI
# package frob" -- a typosquat sdist would also need to vendor two dummy
# top-level directories with those exact names purely to fool this check,
# and gains nothing from doing so since `frob vet`'s dependency scan target
# is the DEPENDENCY's own extracted source root, not frob's repo root,
# in every real invocation. Self-conformance (`_selfconform.py`/
# `_effects.py`) always passes frob's own repo root as `root` by
# construction (self-conformance audits ITS OWN tree), so the discriminator
# is a no-op there; `frob vet` scanning a dependency passes that
# dependency's own source root, which is never frob's repo, so the
# discriminator (correctly) refuses the exclusion and the file gets scanned
# like any other.