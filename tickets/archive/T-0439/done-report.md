## Done report

New gate src/frob/gates/_cve_fingerprint_scan.py (SEC-CVE-FINGERPRINT-001) + scan_text_for_fingerprints/FingerprintHit in src/frob/strata/_cve_fingerprint.py: needle/fingerprint pattern scan over the CVE code-smell corpus with per-language scoping and self-exclusion (a self-match FP where the module docstring contained needle literals was caught and fixed pre-land). Litmus pair: smelly fires, clean does not, wrong-language silent. Registry deferral staleness for 16 pre-existing weaknesses.yaml entries filed as T-0508. Implemented by the strata round-2 agent (commits f428da1..39a5ad8, landed at merge 37dc107); its in-worktree close was destroyed by the T-0505 hazard, so this reconstructs the bookkeeping on main against the landed code.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
