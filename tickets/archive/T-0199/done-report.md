## Done report

Built src/frob/dup/_exhaustiveness.py: the (rung x clone_type x language)
matrix (8 RUNG_SPECS x CLONE_TYPES x 5 LANGUAGES = 40 cells) in the T-0158
capability-matrix mold -- dup_matrix(), unclaimed_cells(),
validate_claim_rungs(). 6 cells are claim-backed by REAL fixtures (all
reused: mod_r6.py, mod_a.py/mod_b.py, dup_region, mod_r4/mod_r5,
probe_equivalence -- no new fixtures authored), 34 are excused with written
reasons, 0 unclaimed. The meta-test (tests/test_dup_exhaustiveness.py, 13
cases) FAILS if any cell is left silently unclaimed, and each claim has a
litmus proof the named fixture actually fires that rung's detector (reviewer
spot-verified non-vacuous via fault injection).

HONEST GAP (not papered over): R3 currently cannot be distinguished from R2
-- _pipeline._r3_fingerprint feeds _r2_normalize output (alpha-rename only,
no literal-abstraction/control-flow-desugar) into r3_canonical_hash, whose
own docstring assumes the caller already did that normalization. The matrix
EXCUSES this cell with the real reason rather than falsely claiming it;
reviewer independently verified the R3-vs-R2 drift against _pipeline.py and
frob-core/src/lib.rs and confirmed it is honestly represented. That gap plus
the missing cross-language fixtures are filed as T-0447.

Coordinator landing note: reviewer APPROVED the matrix code (real, honest,
gate-clean) but REJECTED on undisclosed tickets.md contamination in the
worktree (T-0177 blocked_by silently emptied; T-0330/331/332 drift-lock
paragraphs dropped) -- a stale-worktree ledger artifact. Landed SURGICALLY:
only the code files (_exhaustiveness.py, test_dup_exhaustiveness.py,
dup/__init__.py, docs/modules/dup.md) were lifted; the worktree's
contaminated tickets.md was DISCARDED and this close re-spliced onto clean
main, so none of that contamination reaches the ledger. Evidence: 3 of 13
tests (no-unclaimed-cells, full-matrix-coverage, r1-claim-fires).
