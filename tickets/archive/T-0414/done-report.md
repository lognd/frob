## Done report

Content-hash-keyed (path:sha256(content)), thread-safe, process-lifetime memo
around frob.lang._parse (re-reads + re-hashes content every call, so no
stale-read; single grammar per call site; trees read-only so no cross-consumer
corruption). reset once per frob check via check/_run_check_with_skips.
strata/_code_binding._sorted_py_files switched from unfiltered rglob to a
_should_prune_dir-pruned os.walk (H2/M7). New public reset_parse_cache() /
parse_cache_stats(); 5 TestParseCache tests incl the 1-miss-2-hits
cross-entry-point anti-regression. Reviewer APPROVED after independent
verification: cache-key sound, byte-identical frob check output (same-tree
toggle; cross-checkout diffing is invalid due to .frob state), timing
42.3s->24.2s wall (-43%), 65->32s CPU (-51%). Landed via file-copy recovery
(the worktree commit was lost to a fast-forward; the reviewer-verified changes
were uncommitted-but-safe on disk). Non-blocking nested-worktree walk caveat
filed as T-0416. 0.30.0 re-stamped to include the new public symbols.
