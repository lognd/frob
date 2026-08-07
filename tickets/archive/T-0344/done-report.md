## Done report

Changed: `docs/modules/dup.md` -- (1) rewrote the stale R5 paragraph in
the "Deviations" section that still described the co-occurrence proxy as
R5's only graph path; it now describes the real two-path design
(`_real_dataflow_graph` first, `_build_dataflow_graph` fallback) and
explains when each fires. (2) Added a new per-language R5 coverage table
directly under that paragraph, built by reading
`src/frob/dup/_pipeline.py`'s `_BLOCK_LABELS`/`_ASSIGNMENT_LABELS`/
`_DECLARATOR_LABELS` constants and cross-checking against
`src/frob/lang/__init__.py`'s `_EXTENSION_TABLE` and
`tests/test_dup_r5_multilang.py`'s per-grammar test methods -- not
invented. Findings, stated honestly: python, rust, typescript, c, and cpp
all have real block-container and assignment-node matches (real CFG/DFG);
tsx shares typescript's grammar labels (`_EXTENSION_TABLE` maps `.tsx` to
the `tsx` tree-sitter grammar under the same `"typescript"` `frob.lang`
label) but is NOT separately exercised by `test_dup_r5_multilang.py`
(only `.ts` is), so the table flags that gap rather than claiming tested
coverage it doesn't have; strata has no tree-sitter grammar at all
(`frob.lang.symbol_tree` returns `Err(UnsupportedLanguage)` for
`.strata`), so it is proxy-only with no real-CFG path possible. The table
also states plainly that per-grammar capability is not a per-symbol
100% guarantee -- a region with no matching block node still falls back
to the proxy even on a supported grammar.
Evidence: docs-kind ticket, no pytest surface of its own (per the
playbook's docs-evidence precedent). Recorded via `--evidence-cmd`: a
small verification script asserting every `_BLOCK_LABELS`/
`_ASSIGNMENT_LABELS`/`_DECLARATOR_LABELS` string value from
`_pipeline.py` appears in the new `docs/modules/dup.md` table, so the
table cannot silently drift from the real label sets without the check
failing. Ran clean: "OK: all R5 grammar labels present in
docs/modules/dup.md's coverage table" (exit 0).
Filed: none -- no out-of-scope work found; the tsx-not-separately-tested
gap is disclosed in the table itself rather than filed as a new ticket,
since it is a test-coverage note about an existing passing behavior
(tsx shares typescript's labels), not a bug.
Gates: `uv run frob check --ticket T-0344` -- doc-only scope, no
code-gate surface; verified `uv run frob check` full run's doclink/
docanchor stages do not newly flag `docs/modules/dup.md` (checked before
and after: same doc-related warning set).
