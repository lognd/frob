# Dup detector registry

<!-- frob:describes src/frob/dup/_rules.py::DUP001 -->

## What it is and where it lives

`frob.dup` is not a declarative registry table the way the capability or
threat catalogs are -- it is an ORDERED RUNG LADDER of detectors, each
stage stricter and more expensive than the last, implemented in
`src/frob/dup/_pipeline/` (T-1086 split package): R1 (exact token hash, `_r1_hash`), R2
(alpha-renamed token hash, `_r2_normalize`/`_r2_hash`), R3 (canonicalized
subtree hash, `_r3_fingerprint`, needs `frob_core`), R4 (winnowed
fingerprints + statement-alignment verification, `_r4_fingerprint`), R5
(Weisfeiler-Lehman dataflow-graph hashing, `_r5_fingerprint`), R6
(`probe_equivalence`, opt-in behavioral probing, never in the default
`find_clones` path), R7 (`probe_smt_equivalence`, bounded-SMT, also
opt-in). `src/frob/dup/_rules.py` holds the two PURE gate-rule functions
(`DUP001`, `DUP002`) that turn a computed `CloneReport` into
`Violation`s -- `docs/modules/dup.md` is the authoritative, heavily
anchored reference (37 `frob:doc` anchors already); this guide is
deliberately thin, pointing there rather than duplicating it.

## Add-an-entry recipe (new rung)

1. Decide where in the ladder the new detector sits (stricter than R5 but
   cheaper than SMT? a language-specific rung?) -- rungs are ORDERED by
   cost and recall/precision tradeoff, not an unordered set; a new rung
   needs a documented position, not just an ad hoc bucket.
2. Implement the fingerprinting function in `_pipeline.py` following the
   `_r<n>_fingerprint(state, ...)` signature convention -- pure, no I/O,
   operating on `frob.lang`'s already-parsed `RawSymbol` token/subtree
   data via `state: _FpState`.
3. Wire it into `_fingerprint_symbol`'s per-symbol pass (the function that
   populates every rung bucket for one symbol) -- an unwired rung
   computes fingerprints nobody ever buckets or compares.
4. Per `docs/modules/dup.md`'s no-silent-fallback rule: if the new rung
   needs `frob_core`, `find_clones` must return
   `Err(DupError.CoreUnavailable)` when the native extension is missing --
   never silently skip the rung and under-report clones.
5. Update `docs/modules/dup.md`'s rung table and this guide's cross-
   reference if the new rung changes DUP001/DUP002's default threshold
   semantics.

## Drift-locks that fire

- No `frob check` gate enforces "every rung in the pipeline module is
  wired into `_fingerprint_symbol`" -- an unwired rung function is dead
  code a plain `TEST00x` unit-test-coverage gate would eventually flag
  (an untested public function), but nothing detects "computes a
  fingerprint no caller ever buckets" specifically.
- `DUP001`/`DUP002` are ordinary `frob.gates` rule functions -- they get
  the SAME waiver boundary (`docs/modules/gates.md#waive-boundary-t-0101-revised-t-0289`) and
  severity-override treatment (`[gates.severity]`) as every other gate
  rule id, opt-in via `[dup].enforce`.
- `CoreUnavailable` is a loud typed error, not a silent skip -- this is
  the module's own drift-lock against under-reporting when `frob_core`
  is missing (same posture as the CVE mirror's vacuous-pass doctrine).

## Worked example

R5 (Weisfeiler-Lehman dataflow-graph hashing) is the newest rung: it reuses
R3's canonicalized subtree (`_dataflow_graph`, `_add_chunk_nodes`,
`_add_clique_edges`) to build a small graph per symbol, then hashes it
with a bounded number of WL refinement rounds -- catching structural
clones that R1-R4's token/subtree hashing miss (e.g. two symbols with the
same dataflow shape but reordered independent statements). It sits after
R4 in `_fingerprint_symbol`'s pass and is gated the same
`frob_core`-required way as R3/R4.

## Common mistakes

- Adding a new rung's fingerprinting logic directly inside `_rules.py`
  (the pure gate-rule layer) instead of `_pipeline.py` -- `_rules.py` is
  deliberately a thin filter-and-format pass over an ALREADY-COMPUTED
  `CloneReport`; fingerprinting belongs in the pipeline, matching-and-
  violation-formatting belongs in rules, and conflating them breaks the
  same-shape convention every other `frob.gates` rule function follows.
- Treating a new rung as strictly additive without checking its false-
  positive rate against the SELF-MATCH exclusion precedent (T-0151/T-0158:
  a file whose own text IS the pattern catalog trivially matches itself) --
  `_is_self_path`-style exclusions are per-module, not automatic; a new
  rung scanning raw text/tokens needs its own self-match audit.

## See also

- `docs/modules/dup.md` -- the full rung ladder design, gate integration,
  and caching internals (37 anchors, the primary reference).
- `docs/modules/dup-sota-survey.md` -- state-of-the-art disposition survey
  behind the rung ladder's design choices.
