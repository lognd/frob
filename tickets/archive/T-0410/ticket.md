---
id: T-0410
title: 'Performance audit: frob check hotpaths (archgate 153s + sys 145s dominate),
  redundant full-repo parsing, Rust-lowering, parallelism, daemon caching'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/
- frob-core/
- strata-core/
- tests/unit/test_memo.py
- tests/test_excludes.py
- docs/audits/perf.md
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_memo.py
  reason: add regression test for parse_file per-run memoization landed for this ticket's
    cheap win
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_excludes.py
  reason: add regression coverage for M6 skip-dir fix (BUILTIN_SKIP_DIRS .hypothesis/.serena)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/audits/perf.md
  reason: re-measurement update for the audit doc this ticket's own findings/fix belong
    in
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 version bump + changelog entry for parse_file's public-API-visible
    memoization behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 version bump + changelog entry for parse_file's public-API-visible
    memoization behavior change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 stamp artifact (.frob-release.json) + lockfile version sync from
    the pyproject.toml bump
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 stamp artifact (.frob-release.json) + lockfile version sync from
    the pyproject.toml bump
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_memo.py::test_parse_file_second_call_is_memo_hit
- tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
- tests/test_excludes.py::test_builtin_skip_dirs
designated_repro_test: null
threat: null
component: null
---
User directive (2026-07-20): frob check takes forever; do a PERF audit -- measure where hotpaths ACTUALLY are, lower into native Rust where it helps, review the architecture for stupidity (and note that frob SHOULD have detected its own perf issues -- meta-gap), and think through parallelism/concurrency/multiprocessing. Plus: audit the daemon to ensure we cache what we are supposed to. Grounding measurements (this repo, latest full frob check): archgate=153.6s and sys=145.3s DOMINATE; every other stage is <6s (perf 5.4, pii 1.7, secrets 1.4, test 1.4, tickets 0.27, rest ~0). Strong hypothesis (auditor must MEASURE to confirm/refute via profiling): the repo is tree-sitter-parsed MULTIPLE times per check -- build_graph parses everything, then arch/analyze_project re-parses everything, then strata selfconform (sys) re-parses everything, plus vet/secrets/dup each parse; check/_python.py::_cached_snapshot only memoizes the GRAPH build, NOT arch/sys parses, so trees are not shared across stages. Confound: /mnt/c mount tax (13-60x slower I/O per T-0245) -- the audit MUST distinguish I/O-bound (reading every file N times) from CPU-bound (parsing/walking N times). Deliverables to docs/audits/perf.md (auditor writes it): (A) real profile of a full frob check -- top hotpaths by cumulative time, per stage, with the redundant-parse count actually measured; (B) architecture review: how many times each file is read+parsed, where a single shared parse pass / warm snapshot would collapse work, sqlite connection/contention patterns, any O(n^2) or per-file-stat storms; (C) parallelism/concurrency: are stages actually parallel or serialized? where is the serialization? would a process/thread pool or a shared-parse-then-fan-out help? what belongs in frob-core Rust (hot tree walks: arch complexity, capability scan, hashing -- dup is already Rust)? (D) DAEMON/caching audit: is the warm-graph incremental daemon (T-0177) actually built, and does serve/ cache the parsed graph across requests + invalidate correctly, or re-build/re-parse per call? is the .frob cache doing incremental (only re-parse changed files) or full rebuilds? (E) META-GAP: why did PERF001-004 NOT flag the redundant full-repo parsing / missing shared cache -- what class of architectural/cross-stage perf antipattern is the PERF gate blind to, and what enforcement would catch it (this becomes its own ticket). >=10 concrete findings with measured impact + severity + file:line. REPORT ONLY (auditor). Then remediation children per finding.