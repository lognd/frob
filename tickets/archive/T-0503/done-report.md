## Done report

COMPLIANCE_OUT_OF_SCOPE catalog added to src/frob/strata/_compliance.py and threaded into evaluate_compliance from _audit.py, closing the vacuous-in-production COMPLIANCE004 gap (the security/quality families had out-of-scope catalogs, compliance had none). Non-vacuous proof through the REAL evaluate_exhaustiveness production entrypoint: a fabricated caught_by fails the real audit path; the clean twin discharges. Implemented by the strata round-2 agent (branch worktree-agent-ae94a050b3ebea54f, commits d1e6f30..2c4a01f, landed at merge 37dc107); its in-worktree close was destroyed by the T-0505 ledger-corruption hazard, so this reconstructs the bookkeeping on main against the landed code.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)
