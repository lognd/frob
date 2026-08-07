---
id: T-1082
title: 'arch: abstraction-opportunity gates package extraction (T-0393/T-1067 remainder,
  29 findings)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_spawn_error_yields_no_tracked_files
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_nonzero_exit_yields_no_tracked_files
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set
designated_repro_test: null
threat: null
component: null
---
Filed from T-1067 (T-0393's remainder, re-measured post T-1068). Of the
84 abstraction-opportunity findings remaining after T-1067 extracted the
gitio/testing._runners `_excerpt` duplicate and the vet package's
`_cache_get`/`_cache_set` TTL-cache duplicate, `src/frob/gates/**` alone
carries 29 (19 in `gates/__init__.py`, 1 each in `_baseline.py`,
`_cve_fingerprint_scan.py`, `_docblocks.py`, `_fmt_directives.py`,
`_gate_cache.py`, `_waive.py`, `invariants.py`, 3 in `_pii_structural.py`).

A cross-cutting genuine duplication spans well beyond this finding count:
at least 9 gates modules (`_cve_fingerprint_scan.py`, `_exclude_hazard.py`,
`_opaque.py`, `_refs.py`, `_secrets.py`, `_docblocks.py`, `_docptr.py`,
`_pii_structural.py`, `_walk_lint.py`) each define their own
`_tracked_files`/`_tracked_all_files`/`_tracked_source_files`/
`_tracked_files_by_pattern` -- a `git ls-files [pattern]` -> root-relative
POSIX path tuple/frozenset helper, near-identical error handling
(warn-and-empty-on-failure), reimplemented per gate instead of shared.
Consolidating into one `frob.gates`-level helper (parametrized by
pathspec, returning both tuple and frozenset call shapes as thin
wrappers) would collapse most of `_docblocks.py`/`_docptr.py`'s
`abstraction-opportunity` finding and a good chunk of the same
"tracked-files helper" duplication pattern likely undercounted by the
detector's per-file grouping (it does not always attribute a cross-file
group to every member file, per T-1067's `gitio.py`/`testing/_runners.py`
finding shape).

`gates/__init__.py` is ALSO the T-0395 large-file-residue candidate
(~15 of its own groups per T-1067's parent ticket T-0393) -- extracting
shared abstractions from it is likely to interact with T-0395's own
split plan; read T-0395 first and coordinate rather than duplicating
file-restructuring work.

Do not attempt all 29 (+ the wider tracked-files consolidation) in one
pass if it does not fit; a coherent partial (e.g. the tracked-files
helper consolidation alone, or just `_baseline.py`'s `_read_toml` x3
duplication) is fine, with the remainder re-filed with exact counts.
Re-measure `uv run frob check --only arch --json`, filter to
abstraction-opportunity + `src/frob/gates/`, before starting -- other
tickets may land in the interim and change the count.