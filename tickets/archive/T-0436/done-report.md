## Done report

Built src/frob/gates/_docblocks.py (doc004_gate, rule DOC004), wired into
run_gates as gate `docblocks` -- confirmed executing (`docblocks=` in the
per-gate timing line) and present in BOTH _ALL_GATES and
_CANONICAL_GATE_ORDER (set equality holds, so it cannot be silently dropped
from the summary -- the T-0122/T-0415 lesson). Two tiers: STALE (error,
reference resolves to nothing) and UNBOUND (warn, resolves but no nearby
frob:doc/frob:describes/frob:tests anchor). frob:waive DOC004 reason="..."
honored directly from doc text (REFINEMENT 2).

Manifest-derived namespaces (REFINEMENT 3): python pyproject [project.name]
+ importable packages under src/; rust Cargo [package].name AND
[workspace].members subcrates (each its own crate namespace); ts/js
package.json name + workspaces -- so package-name != dir-name
(logandapp_backend) resolves via manifest, and external libs (tokio, etc.)
are skipped/waivable. Generalized beyond frob to any project's own code
surface (REFINEMENT 1).

Dogfooded on frob's own docs: 6 raw findings -> fixed 2 real detector bugs
(_module_reexports package-reexport FP, _collapse_paren_imports multi-line
import misparse) -> remaining findings dispositioned with reasoned
frob:waive DOC004 in 3 doc files. frob check now reports 0 DOC004 on this
repo (hand-verified 0/6 false positives, reviewer-confirmed).

Evidence: 5 of the 9 tests in tests/test_docblocks_gate.py (stale python
symbol, unbound-warn, waiver-suppression, package!=dir namespace, rust
missing-item stale). All 9 pass; reviewer confirmed non-vacuous.

Reviewer REJECT was a single ARCH001 on doc004_gate (42 lines > the OLD
30-line default) measured in a worktree branched before T-0373. T-0373
(landed just before this) wires the calibrated max_function_lines=60 into
the arch gate, so on current main doc004_gate (42) is UNDER threshold and
no ARCH001 fires -- the reject is mooted by the threshold fix, not by
silencing. Verified: the only 3 ARCH001 findings now are pre-existing
(registry_gate 109, _refs.ref_gate 78, _classify 76), none is doc004_gate.

Follow-up filed T-0443 (console/bash `frob <subcommand>` command-drift
tier, pending a frob.toml-configurable command source). Landed via 3-way
patch + hand-merged gate wiring onto current main (worktree stale; gates
__init__.py was also restructured by the landed T-0415).
