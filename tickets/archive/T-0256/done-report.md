## Done report

**Round 2 (reviewer REJECT fix).** Round 1's Done report below is kept
for the file list; this preamble records what round 2 actually changed
and why, since it is the security-relevant part.

Round 1 REJECTED on two grounds:

1. CRITICAL VACUITY: `build_compromised_user_scenario`'s blast-radius
   `NoFlow` claims were proved purely over `_facts.py::FactBase.
   reachable`'s DECLARED-`Flow` closure, with no dependency on
   `HostManifest` ownership. Two users sharing a writable path with no
   declared app `Flow` between them made HOST001 correctly fire
   (`shared-writable-path`) while the SAME model's blast-radius claim
   vacuously reported PROVED -- false assurance, the exact movement this
   ticket exists to prove impossible, silently unproven.
2. Two `ty` errors (`_host_isolation.py:496,499`, invalid-return-type):
   `# type: ignore[return-value]` does not suppress `ty`; round 1's Done
   report claimed a clean check that was not actually clean.

Fix for (1), option (a) from the reviewer (wire manifest-sharing into
the closure, not narrow the claim): new `_host_isolation.py::
host_movement_flows` derives the SAME sharing relations HOST001 detects
(shared writable path, shared reachable socket) as synthetic `Flow`
facts; new `_models.py::AddFlow` (a fourth `Rewrite` variant, reusing
the existing `Flow` shape -- no new `strata_core` closure primitive) 
materializes each one into the scenario's rewritten model; 
`build_compromised_user_scenario` now emits one `AddFlow` rewrite per 
derived edge, BEFORE the `SetTrust` downgrades. Verified against the
reviewer's exact adversarial case (`tests/unit/strata/
test_host_isolation.py::
test_blast_radius_refutes_over_shared_writable_path_with_no_declared_flow`):
two users sharing `/var/lib/shared` writably with no declared `Flow` --
the blast-radius claim now REFUTES (previously wrongly PROVED); the
disjoint hardened model (`test_blast_radius`) still discharges
(PROVED). `test_movement_flows` covers `host_movement_flows` directly.

Fix for (2): the two early-return branches in `evaluate_host_isolation_
waived` now `return Err(lateral.danger_err)` / `return
Err(vertical.danger_err)` (constructing the correctly-typed `Result`
value) instead of returning the mistyped `Result[tuple[HostIsolation
Violation, ...], StrataError]` object with an ineffective `# type:
ignore`. `uv run ty check src/frob/strata/` now reports "All checks
passed!" (verified below).

Changed (cumulative, round 1 + round 2):
- src/frob/strata/_host_isolation.py (new) -- `HostIsolationViolation`,
  `evaluate_lateral_isolation` (HOST001), `evaluate_vertical_isolation`
  (HOST002), `evaluate_host_isolation_waived`, `host_movement_flows`
  (round 2), `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`,
  `COMPROMISED_OWNER_CATALOG`, `COMPROMISED_OWNER_OUT_OF_SCOPE`,
  `COMPROMISED_OWNER_VIEWS`.
- src/frob/strata/_models.py -- new `AddFlow` `Rewrite` variant (round 2).
- src/frob/strata/_scenarios.py -- `build_compromised_user_scenario`
  (reuses the existing `SetTrust` rewrite; round 2 additionally emits
  `AddFlow` rewrites for `host_movement_flows`'s edges), `_apply_add_flow`
  + `_apply_rewrite` dispatch for the new variant.
- src/frob/strata/__init__.py -- exports for all of the above (`AddFlow`,
  `host_movement_flows` added round 2).
- docs/strata/host.md -- new "Movement-impossibility proofs" section
  (sub-sections: the honest gap, waiver discipline, compromised-owner
  threat catalog, compromised-user scenario); corrected a pre-existing
  T-0256/T-0257 mislabeling; round 2 added the "Review-round fix
  (vacuity)" paragraph under compromised-user scenario.
- tests/unit/strata/test_host_isolation.py (19 tests total -- 15 round 1
  + `test_movement_flows` and
  `test_blast_radius_refutes_over_shared_writable_path_with_no_declared_flow`
  round 2), tests/unit/strata/test_litmus_host_isolation.py (2 tests),
  tests/unit/strata/litmus/host_isolation_vuln.strata,
  tests/unit/strata/litmus/host_isolation_hardened.strata.
- CHANGELOG.md -- new-public-symbol line under the existing `[0.4.0]`
  section, updated round 2 for `AddFlow`/`host_movement_flows` (REL001;
  version stays 0.4.0 per dispatch instruction).
- .frob-release.json -- re-stamped round 2 (`frob release stamp`) for
  the additional public symbols.
- tickets.md -- this ticket's scope extended to cover CHANGELOG.md and
  .frob-release.json (SCOPE001 fired on both, round 1).

Design notes / honest disclosures:
- HOST001/HOST002 sub-targets are ALL derived from `HostManifest`
  (`_host.py`, T-0255) -- no hand-written per-pair/per-user table.
  `setuid` reads the existing 4-digit octal `owns` mode (no grammar
  change). `shared-group` and `sudoers` structurally CANNOT be derived
  -- `std.host`'s grammar (`strata-core/src/parse.rs`) has no OS-group
  or sudoers vocabulary, and `strata-core/**` is outside this ticket's
  declared scope. Per T-0174's deny-by-default waive discipline, both
  sub-targets UNCONDITIONALLY fire until explicitly waived
  (`waive "HOST001:shared-group" reason="..."` /
  `waive "HOST002:sudoers" reason="..."`) or the grammar lands. Not Filed
  T-draft-7b5b5541 (never refiled) (off-default-branch provisional id; the coordinator's
  ticket-numbering step will assign the permanent id on merge) for that
  grammar addition.
- HOST001 pair findings attribute to the alphabetically-earlier user of
  the pair (deterministic sort order) -- one `waive` clause on that
  user's node discharges the pair finding; a duplicate on the peer's
  node correctly reports STALE (`_waive.py`'s drift-lock). Documented in
  `evaluate_host_isolation_waived`'s `target_of` docstring and in
  `docs/strata/host.md#waiver-discipline`.
- `evaluate_host_isolation_waived` runs two SEPARATE `apply_waivers`
  calls (one per rule family) with `in_scope` narrowed to exactly the
  family being checked -- an earlier draft used the union
  `HOST_MULTI_INSTANCE_WAIVER_FAMILIES` for both calls and
  double-reported a HOST002 waiver as STALE inside the HOST001
  application (caught by the hardened-model unit test before commit).
- `COMPROMISED_OWNER_CATALOG` (CWE-284/269/522) joins a SEPARATE
  `compromised-owner-baseline` view, never `_threat.py::CWE_CATALOG`/
  `VIEWS` -- verified `check_catalog_completeness("owasp-top-10")`
  still passes unaffected (`TestCompromisedOwnerCatalog::
  test_default_owasp_view_unaffected`).
- `host_movement_flows` is computed over EVERY distinct service-user
  pair in the model (not scoped to the one compromised user), so a
  multi-hop movement path through a third user's shared resource stays
  visible to the closure -- sound (more edges only tighten a `NoFlow`
  proof, never loosen it), disclosed as not maximal (a movement vector
  this function does not model, e.g. process-level ptrace/IPC, is still
  invisible; only filesystem-ownership and socket-port sharing are
  covered, matching HOST001's own detection surface exactly -- no wider
  claim is made).
- `AddFlow` is scenario-scoped only (`_apply_add_flow` copies the model,
  never mutates the base `KernelModel`'s declared flows) and fails
  closed (`StrataError.DuplicateId`) on a flow-id collision.
- HOST001/HOST002 are evaluated as standalone strata functions, NOT
  wired into `frob check`/a gate rule -- matching `_threat.py::
  evaluate_threats`'s own documented precedent ("gate wiring is a
  follow-up... this function is the seam that follow-up calls into").
  Gate wiring is a natural T-0258 (conformance checker) or follow-up
  ticket concern, not silently done here beyond declared scope.

Evidence: 19 pytest node ids recorded via `frob ticket evidence T-0256`
(command output confirms `T-0256 recorded 19 id(s)` across the two
`frob ticket evidence` calls -- 17 round 1 + 2 round 2), all
independently verified passing via
`uv run pytest tests/unit/strata/test_host_isolation.py
tests/unit/strata/test_litmus_host_isolation.py -v -o addopts=""`
(`19 passed`). Full repo `uv run pytest -q` also green.

Not Filed: T-draft-7b5b5541 (never refiled) ("std.host: OS-group and sudoers-grant
vocabulary" -- scope `strata-core/src/parse.rs`, `src/frob/strata/**`,
`docs/strata/**`, `tests/**`).

Gates (round 2, REAL state): merged `main` (T-0221 landed, tip
6079e51 pre-recommit) before this round's work. `uv run ty check
src/frob/strata/` -> "All checks passed!" (0 errors; round 1's 2
invalid-return-type errors gone). `uv run frob check --ticket T-0256`
-> 0 errors, 12 warnings, 223 waived. `uv run frob check` (full,
unscoped) -> 0 errors, 0 DRIFT002, 12 warnings, `ty` tool-summary line
reads "pass ty no issues". `git diff main --diff-filter=D --stat`
empty (deletion-filter land rule). `make core`/`make coverage`'s
Cargo.lock churn reverted before every check and before commit.
