## Done report

Added load_arch_config(root) in src/frob/app/config.py (reads frob.toml's
[arch] table, falls back to new ARCH_DEFAULT_MAX_* constants
60/12/8/4/800), following the existing _dup_config per-section-loader
idiom. src/frob/gates/_arch.py::arch_gate now calls analyze_project(root,
**load_arch_config(root)) -- confirmed by the reviewer to actually reach
the analysis (not a dormant/loaded-then-ignored config). Added an explicit
[arch] table to frob.toml disclosing the calibration, and a Configuration
section to docs/modules/arch.md with frob:describes anchors.

REL001: new public surface (load_arch_config + 5 ARCH_DEFAULT_MAX_*
constants) -> minor bump pyproject/uv.lock 0.32.0 -> 0.33.0 + CHANGELOG
entry; `frob release check` green at 0.33.0.

Evidence (4 ids, all pass): test_config.py override/default/missing/partial/
malformed paths; test_arch.py proves a 600-line file fires large-file at the
500 default but NOT at the calibrated 800; test_gates.py TestArchGateThresholds
proves the GATE (not just the analyzer) honors the calibrated default and an
explicit frob.toml override. Reviewer APPROVED.

Follow-up filed (T-0442 below, renumbered from the implementer's draft):
frob check's non-gate _run_arch tool-summary stage in src/frob/check/_python.py
still uses default thresholds, not load_arch_config -- a genuine remaining
inconsistency, correctly scoped out of this ticket.

Landed via 3-way patch apply onto current main (worktree was stale;
tests/test_gates.py was also touched by the already-landed T-0415, and the
3-way merge preserved both T-0415's process-pool tests and this ticket's
TestArchGateThresholds -- verified both suites pass).
