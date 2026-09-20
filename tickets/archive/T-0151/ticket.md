---
id: T-0151
title: vet capability scanner self-matches its own pattern-table literals
state: done
kind: bug
origin: human
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
- tests/test_vet.py
- design/frob.strata
- docs/modules/vet.md
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
  old_length: 1137
  new_length: 4015
evidence:
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_re_compile_alone_does_not_report_eval
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_bare_compile_call_still_reports_eval
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_genuine_eval_still_detected
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/vet_suite/test_capability_scan_python.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while measuring real capabilities for T-0150's design/frob.strata may declarations: scan_file_capabilities/scan_directory_capabilities substring-matches _PATTERNS' own needle literals (e.g. "subprocess.", "compile(", "cmdclass") when scanning src/frob/vet/_capability.py itself, since those needles are stored as plain string data in that same file. This inflates vet's own observed capability set (T-0150 measured vet as declaring eval/exec/ffi/install-hook/env/net almost entirely from this one file matching itself) and would similarly inflate the scan of any OTHER file that happens to embed one of these substrings in a comment/string/docstring (T-0150's own _threat.py DEFAULT_BENIGN_CAPABILITIES reason strings tripped this exact false-positive during T-0150's rework, before rewording). Needs either: excluding the pattern-table-defining file itself from self-scanning, or a smarter match (e.g. AST-based real call-site detection instead of raw substring match), or a documented/accepted false-positive-rate note in docs/modules/vet.md. Out of scope for T-0150 (scope excludes src/frob/vet -- T-0147 concurrently edits it).

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