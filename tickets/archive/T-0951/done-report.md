## Done report

Study ticket -- no port implemented, per the ticket's own instruction.
Measured `archgate` (11.08s audit baseline) and `pii_structural` (4.60s
audit baseline) directly instead of accepting T-0930's read-level
assumption at face value.

**`pii_structural`: assumption confirmed, disposed honestly, no
follow-up.** Direct non-profiled run over this repo's 689 tracked
`.py`/`.ts`/`.tsx`/`.rs` files measured 5.15s wall. Every significant
per-file cost is `ast.parse`/tree-sitter-`Node`-shaped walking; the
final matching step (`_field_name_hit`/`_field_type_hit`) is already a
cheap dict lookup. No separable expensive plain-data computation to
lift out -- the walk itself needs the `Node`/`ast` object. Not a rust
candidate at this repo's scale.

**`archgate`: one real, measured, plain-data-shaped sub-boundary found.**
`_check_abstraction_opportunities` -> `_near_duplicate_cluster`
(`src/frob/arch/_python.py`) runs pairwise `difflib.SequenceMatcher(
None, a, b).ratio()` over already-normalized body-fingerprint STRINGS
(plain data, not `Node`s), matching `frob_core.tree_edit_similarity`/
`apted_similarity`'s existing compute-only precedent shape. Isolated by
monkeypatching the function to a no-op and diffing wall-clock
(non-profiled, this repo's own tree, single A/B call since
`analyze_project` is memoized per-call not across calls): baseline
11.57s, near-dup-neutralized 8.47s -- ~3.1s (~27% of the audit's 11.08s
baseline row) attributable to this one detector. A `cProfile` pass
(109.5s under profiler overhead, relative shares only) attributed 40.9s
cumulative to `_check_abstraction_opportunities`'s own subtree, with
107,024 `difflib.find_longest_match` calls as the single largest leaf.
The other ~73% of archgate (SOLID/LSP/OCP/concurrency/async/lock-
ordering/SRP-cohesion detectors, all genuinely `Node`/`NormalizedModule`-
shaped) is NOT a rust candidate, same reason as pii_structural.

Marshaling cost estimated per T-0930's lesson (PyO3 marshal overhead
measured exceeding a comparable string/token-scan kernel's own compute
cost at this repo's real scale, T-0930's dead_symbols finding): the
natural batching boundary here is one marshal PER SAME-SIGNATURE GROUP
(list of body strings in, near-dup index set out), not one per pairwise
comparison -- a coarser batch than T-0930's reverted per-symbol-call
`resolve_call_edges` prototype, so the marshal-once-per-group
amortization is plausibly favorable, but this was NOT measured directly
(would require the kernel to exist first). Filed as a follow-up rather
than assumed.

Filed: T-0953 (port `_near_duplicate_cluster`'s pairwise
body-similarity scoring to a `frob_core` kernel, `list[str]` bodies in /
near-dup index set out, batched once per same-signature group; golden
parity vs `difflib.SequenceMatcher.ratio()` at the existing 0.9
threshold; real marshal-vs-compute measurement required with the kernel
actually built before wiring as default, per T-0930's precedent -- do
not ship if measured net slower). Gets a permanent T-#### id at land,
per T-0930's own T-0950/T-0951 precedent for drafts filed this way.

Changed:
- docs/audits/check-performance.md ("Remediation log (T-0951,
  archgate/pii_structural rust-candidate feasibility)" section
  appended)

Evidence: this ticket is a measurement/decision-document study with no
code changes; the two isolation measurements above (wall-clock A/B via
monkeypatch, and the standalone `pii_structural_gate`/`arch_gate` calls)
are the evidence, run live against this repo's own real tree, not
against a synthetic fixture -- recorded in the audit doc's new section
verbatim. No pytest node ids apply (no test-observable behavior changed;
this ticket produced a decision document plus one filed follow-up
ticket, nothing else).

Gates: `frob check --ticket T-0951` (chunked: gates-fast, gates-native,
gates-security, static, all clean, 0 errors). `lint` group shows 2
pre-existing `ty` errors and 3 pre-existing `ruff-format` warnings, all
in `tests/test_gates.py`/`src/frob/arch/_lock_ordering.py`/
`tests/unit/test_arch.py` -- files this ticket did not touch (`git diff
--stat` shows only `docs/audits/check-performance.md` and `tickets.md`
changed). These are the SAME pre-existing failures T-0929's and
T-0930's own Done reports already documented as pre-existing and out of
scope; not touched, not waived under T-0951.
