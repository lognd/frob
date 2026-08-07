## Done report

Implemented KRB001-004 in a new `src/frob/strata/_krb_movement.py`
(mirroring `_host_isolation.py`'s HOST001/HOST002 shape) plus
`_scenarios.py::build_compromised_krb_scenario` (reuses the T-0073
engine, `SetTrust`/`AddFlow`/`NoFlow`, exactly like
`build_compromised_user_scenario`).

Proof design (non-vacuous, per the family's review-round warning):
- KRB001 (unconstrained delegation): fires unconditionally per node
  declaring `delegation unconstrained` -- deny-by-default, waivable
  with `KRB001:unconstrained-delegation`.
- KRB002 (Kerberoasting): every declared `spn` fires -- an honest gap
  (no gMSA/machine-account vocabulary exists in `std.krb`'s grammar,
  which lives in `strata-core/` outside this ticket's scope, the same
  cut T-0256 hit before T-0272), waivable per-SPN with a written
  gMSA/machine-account attestation (`KRB002:<spn>`).
- KRB003 (constrained-delegation blast radius): a REAL BFS
  (`_delegation_reach_higher_trust`) over the SPN-ownership graph
  built from every constrained-delegation node's own `target`s
  (S4U2Proxy chaining) -- proved/refuted against the model's trust
  lattice, not just the immediate target list, with a full witness
  path per finding. Unit test `TestKrb003.test_chains` covers a real
  2-hop chain (svc -> mid -> vault) that only a transitive closure
  catches.
- KRB004 (cross-realm containment): uses `_facts.py::build_facts`/
  `FactBase.reachable` -- the SAME closure every `NoFlow` claim uses,
  walking `model.flows` (which already include `_krb.py::
  krb_trust_flows`'s elaboration-time-synthesized trust edges) -- and
  only fires when the reaching path actually transits a
  `krb_trust`-tagged flow AND lands on strictly higher trust.
- `build_compromised_krb_scenario`: unconstrained delegation
  materializes a synthetic edge to EVERY other node (worst-case reach);
  constrained delegation materializes edges only to resolved targets.
  `TestKrbScen.test_all` proves the closure REFUTES the
  no-flow-to-everywhere claim for an unconstrained node (not vacuously
  PROVED); `TestKrbScen.test_constrained_bounded_to_targets` proves an
  unrelated third node stays outside a constrained node's blast
  radius.

Litmus (`tests/unit/strata/litmus/krb_movement_{vuln,hardened}.strata`,
round-tripped through the real `strata_core` parser):
- VULN model: `app` (unconstrained delegation), `mid`
  (constrained-delegation chain mid -> vault escalating trust
  authenticated -> trusted), `low_kdc` (one-way transitive trust into
  higher-trust `high_kdc`) -- fires all four rules
  (`TestKrbMovementVulnLitmus::test_vuln_model_fires_all_four_rules`).
- HARDENED model: constrained delegation bounded to a same-trust
  target, two-way trust between two SAME-trust realms (no escalation),
  roastable-SPN honest gap discharged via two explicit gMSA-attestation
  waivers -- KRB001/003/004 discharge with zero waivers needed;
  KRB002 discharges via the waivers
  (`TestKrbMovementHardenedLitmus::test_hardened_model_discharges`).

Test results (measured, this worktree, natives built via `make core`):
- `uv run pytest tests/unit/strata/test_krb_movement.py
  tests/unit/strata/test_litmus_krb_movement.py -q` -> 15 passed.
- `uv run pytest tests/unit/strata -q` -> 786 passed (no regressions).
- `uv run ruff check` / `ruff check` (PATH) / `uv run ruff format
  --check` / `ruff format --check` (PATH) all clean on every changed
  file.
- `uv run ty check src/frob/strata/` -> All checks passed.
- `uv run frob test --base main` -> `[PASS] python` / `[PASS] strata`.
- `git diff main --diff-filter=D --stat` -> empty (no unintended
  deletions).

Evidence:
- tests/unit/strata/test_krb_movement.py::TestKrb001.test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb001.test_skips_constrained
- tests/unit/strata/test_krb_movement.py::TestKrb002.test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb002.test_no_spn_no_finding
- tests/unit/strata/test_krb_movement.py::TestKrb002.test_waivable_with_gmsa_reason
- tests/unit/strata/test_krb_movement.py::TestKrb003.test_chains
- tests/unit/strata/test_krb_movement.py::TestKrb003.test_non_chaining_same_trust_discharges
- tests/unit/strata/test_krb_movement.py::TestKrb004.test_fires
- tests/unit/strata/test_krb_movement.py::TestKrb004.test_same_trust_realms_discharge
- tests/unit/strata/test_krb_movement.py::TestKrbScen.test_all
- tests/unit/strata/test_krb_movement.py::TestKrbScen.test_constrained_bounded_to_targets
- tests/unit/strata/test_krb_movement.py::TestKrbScen.test_unknown_node_fails_closed
- tests/unit/strata/test_krb_movement.py::TestKrbCatalog.test_catalog_completeness_over_own_view
- tests/unit/strata/test_litmus_krb_movement.py::TestKrbMovementVulnLitmus::test_vuln_model_fires_all_four_rules
- tests/unit/strata/test_litmus_krb_movement.py::TestKrbMovementHardenedLitmus::test_hardened_model_discharges

Not Filed: T-draft-30d66138 (never refiled) (release: bump version + CHANGELOG entry for
T-0263's new public API -- REL001 gate fires but T-0263's own scope
glob excludes pyproject.toml/CHANGELOG.md/.frob-release.json, so the
bump is filed as separate release-management follow-on rather than
widening this ticket's scope).

Disclosed cuts (documented in docs/strata/krb.md's Scope boundary
section, not filed as tickets, mirroring how T-0262's own scope
boundary disclosed this ticket before it existed):
- No RBCD-chain-vs-trust-boundary cross-check: `delegation rbcd` is
  read as a typed value but no rule examines an RBCD node's blast
  radius against declared trust boundaries the way KRB003 examines
  `constrained`.
- No `frob sys audit` wiring: `evaluate_krb_movement_waived`/
  `build_compromised_krb_scenario` have no caller reaching them from
  `_audit.py::evaluate_exhaustiveness` yet -- mirrors T-0280's staged
  rollout for HOST001/HOST002 after T-0256 landed.

Gates: `uv run frob check` -- 2 errors remain, both pre-existing/
out-of-scope, not introduced by this change: REL001 (version bump,
not filed T-draft-30d66138 (never refiled) above, files out of scope) and TEST006 (no
coverage stamp in this fresh worktree -- `make coverage` was not run;
per the worktree-natives-artifact precedent this is an environment
gap in a fresh worktree, not a regression from this ticket's diff).
All COV001/DOC002/PERF004 findings this diff introduced were fixed
in-line (docs/strata/krb.md's new "Movement proofs" section supplies
the `#movement-proofs`/`#compromised-domain-principal-threat-catalog`
anchors; the flagged `sorted()` call is waived with a reason).
