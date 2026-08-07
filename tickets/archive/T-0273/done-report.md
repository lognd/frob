## Done report

Added a run-size guard to exact_regions' O(k^2) pair emission. In
frob-core/src/lib.rs, exact_regions/emit_run_pairs gained max_run_size
(default 200 via #[pyo3(signature=...)]); a run larger than the cap only
pairs its first max_run_size SA-ordered occurrences, bounding per-run cost
at O(cap^2) (200 -> <=19,900 pairs vs the reviewer's demonstrated
1,999,000-pair/17.5s blowup at run-size 2000). Return type is now
(regions, truncated: bool) -- an HONEST truncation signal, never a silent
drop (T-0193-recall-bug lesson). Threaded through: _core._exact_regions
returns Result[(regions, truncated), DupError]; DupConfig.region_run_cap=200;
_pipeline._region_groups passes cfg.region_run_cap and logs a WARN naming
[dup].region_run_cap when truncated. Documented in docs/modules/dup.md
(guard + toml key, both [dup] example blocks).

Evidence (2 Python ids, pass; 2 Rust tests also added): TestExactRegions
run-size-guard-bounds-emission-and-signals-truncation and
does-not-trip-below-the-cap. 9 Rust + 3 Python existing tests updated only
for the tuple-return signature. Reviewer APPROVED with explicit correctness
sign-off (recall trade-off honestly signaled + documented, sane default).
Landed via 3-way patch (coexisting with T-0268's candidate_pairs change in
the same lib.rs) + make core rebuild onto current main.
