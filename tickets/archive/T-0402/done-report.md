## Done report

G1 (HIGH): load_graph now diffs the on-disk tracked-file set vs the cached set
via _first_added_file, returning CacheStale on any added/removed file (not
just changed cached ones) -- a newly-added file no longer passes on an
incomplete snapshot. G2 (HIGH): non-UTF-8/decode errors caught per-file,
surfaced loudly (the file never gets a cache row -> perpetual CacheStale ->
build_graph fallback), never crash-or-silently-drop. G3/G5/G10/G11/G12 also
fixed (bare-describes resolution via resolve(), exact-qualname-wins,
acknowledge facets). G3 correctly SURFACED 48 real dangling doc anchors that
were unresolvable from day one (dotted-import convention instead of the
graph's path::qualname) -- repointed to correct symbols in arch.md (5) +
dup.md (43), literal frob:describes examples in audit/module docs neutralized.
Reviewer APPROVED G1/G2/qualname (round 1) then the doc-drift disposition
(round 2). Verified: 95 graph tests pass, 0 DRIFT002, full frob check 50
errors -> 0. Landed via file-copy (tickets.md merge tangled -- recovered a
mis-copy that briefly reverted T-0377/drainer, restored from HEAD, no loss).
Residuals filed: T-0433 (G6/G7), T-0434 (G4/G9 in frob.lang).
