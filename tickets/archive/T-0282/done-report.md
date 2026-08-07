## Done report

Changed:
- `strata-core/src/lib.rs::Edge` -- 5th bool field `transitive` (default
  meaning: middle-link-eligible); `reachable`'s BFS only enqueues a
  discovered node into `frontier` when the edge that discovered it has
  `transitive == true` -- a `false` edge's `dst` is still added to `paths`
  (single-hop reach always succeeds) but never becomes a chain link.
- `strata-core/strata_core.pyi::reachable` -- stub signature updated to the
  5-tuple `Edge` type (SCOPE001-noted, see above).
- `src/frob/strata/_facts.py::FactBase.reachable` -- edge tuples now carry
  a 5th element, `"krb_no_transit" not in f.attrs`, read off each `Flow`.
- `src/frob/strata/_krb.py::krb_trust_flows` -- a trust with
  `transitive=False` now also stamps `krb_no_transit` on its synthesized
  `Flow`'s `attrs` (both directions of a two-way trust share the flag).
- `docs/strata/kernel.md#strata-core`, `docs/strata/krb.md#domain-trust-
  lattice` -- known-gap language replaced with the fixed behavior and
  pointers to the regression coverage.

Trip-wire flipped: `tests/unit/strata/test_krb.py::
TestTrustChainReachability.test_non_transitive_chain_currently_over_reaches_known_gap`
now asserts `"c" not in paths` (was `"c" in paths`, the disclosed bug) for
a two-hop chain of non-transitive one-way trusts `a->b->c`; kept, not
deleted, per the ticket's instruction -- it is now the permanent
regression guard. The sibling `test_transitive_chain_reaches_across_both_hops`
(all-transitive chain) is UNCHANGED and still asserts `"c" in paths` --
confirms transitive chaining is untouched.

Verification run (this worktree, `.claude/worktrees/agent-aefe00c12bf4af2d5`,
merged to main tip `b932e5b` before finishing):
- `cargo test` (strata-core, via the venv's Python 3.11 lib for pyo3
  linking): 111 passed, 0 failed, including the 2 new terminal-edge unit
  tests above.
- `uv run pytest -q` (full repo suite): all green, no failures (only the
  pre-existing 2 skips unrelated to this change).
- `uv run pytest -q -k "TestRealGateGreen or litmus"`: all green.
- `uv run pytest tests/unit/strata -q`: all green (283 tests).
- `uv run frob check --json`: 0 unwaived errors, "all files formatted",
  "no cycles"; remaining warnings/notes (duplicate groups, missing-from-
  `__init__.py` symbols) are pre-existing repo-wide baseline noise, not
  introduced by this change (confirmed via `git diff main` touching only
  the files listed above).
- `git diff main --diff-filter=D --stat`: empty (deletion-filter land rule,
  agent-playbook.md #9) -- no files/hunks deleted.
- `uv run ruff format --check` and PATH `ruff format --check` on every
  touched Python file: both "already formatted" after one `ruff format`
  auto-fix pass on `_krb.py`.

Cuts/notes: no existing `reach`/`noflow` claim's expected value changed --
every pre-existing edge default-constructs `transitive=true` at the
`_facts.py` boundary (`"krb_no_transit" not in f.attrs` is `true` for any
flow without that attr, which is every non-krb-trust flow and every
transitive krb-trust flow), so the full test suite passing unmodified
except for the two krb-trust tests already discussed is the evidence of
no regression, not an assumption.

Filed: none (no out-of-scope work discovered).
Gates: `uv run frob check` clean (0 unwaived errors); no waivers added by
this change beyond the repo's pre-existing waiver set.

T-0262 round-2 review finding (reviewer-reproduced): std.krb's non-transitive domain trusts (trusts IDENT direction "..."  -- no transitive marker) are recorded as typed metadata (KrbTrust.transitive=False) but the shared strata_core::reachable BFS (strata-core/src/lib.rs) has no concept of a non-transitive/terminal edge -- every synthesized Flow is walked identically regardless of the transitive flag, so a chain of non-transitive one-way trusts a-->b-->c wrongly yields reach(a,c)=True today. This is a genuine kernel-level gap: strata_core::reachable's Edge tuple and BFS loop would need a new terminal-edge concept (discover the direct dst via a terminal edge, but do not enqueue it into the BFS frontier for further expansion), which is a change to the SHARED reachable() primitive every noflow/reach claim in the kernel uses -- out of scope for T-0262 (parse.rs only) and too wide-blast-radius to bundle into that ticket's std.krb vocabulary work. Fix: extend the Edge type in strata-core/src/lib.rs with a 5th bool field (terminal), thread it through _facts.py::FactBase.reachable's edge construction (read a new flow attr, e.g. krb_no_transit, off krb_trust_flows-synthesized Flows), and add the property tests test_kernel_properties.py already has infrastructure for (hypothesis oracle). Until this lands, docs/strata/krb.md and _krb.py honestly disclose that transitive is recorded but not yet enforced by the reach engine.
