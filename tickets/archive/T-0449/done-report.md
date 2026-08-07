## Done report

LINK, not exempt (per user directive). ref_gate now resolves the sidecar-
stub<->crate pairing STRUCTURALLY from the maturin manifest:
_load_maturin_module_name reads [tool.maturin] module-name from a tracked
pyproject.toml; _native_stub_pairs pairs a .pyi whose stem matches that
module-name with a same-directory manifest; ref_gate adds the paired
manifest into the stub's INBOUND reference set. So a linked stub gets a real
inbound edge (its crate manifest) -- REF002 (single-anchor advisory), not
REF001 (orphan). Confirmed on the real repo: frob-core/frob_core.pyi (newly
created with typed signatures for all 8 pymodule exports) and
strata-core/strata_core.pyi (frob:describes its crate) each now show REF002,
not REF001. A genuinely un-linked .pyi with no adjacent module STILL fires
REF001 (not a blanket exemption) -- reviewer SABOTAGE-VERIFIED this: faking
the pairing as always-true made test_unlinked_pyi... and the name-mismatch
test correctly FAIL, proving the tests are non-vacuous.

Evidence (3 tests): linked-passes, unlinked-still-fires-REF001,
manifest-present-but-name-mismatch-still-fires.

Reviewer verdict: the linking MECHANISM is correct and sabotage-verified; the
REJECT was solely 6 SCOPE001 from the untracked src/frob/render/ pollution in
the worktree (the T-0465 shared-.git/info/exclude bug) and the Done report's
resulting stale SCOPE001=0 claim. That pollution is now MOOT on main --
render/ is properly tracked (fixed this session) so it is no longer a stray
file, and T-0449's own diff (gates/_refs.py, the two .pyi, tests) is clean.
Landed via 3-way + explicit copy of the new frob_core.pyi (the new-file case
T-0463's completeness assertion now guards).
