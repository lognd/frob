## Done report

Changed:
- src/frob/vet/_obfuscation.py::_iter_string_literals (frob:waive PERF003)
- src/frob/tickets/_land.py::splice_ledger (frob:waive PERF004)
- src/frob/strata/_host_isolation.py::_lateral_pair_violations (frob:waive PERF004)
- src/frob/deploy/_generate.py::sorted_manifest_entries (frob:waive PERF004)

Per-finding disposition (all four are false positives of the lexical
heuristic, not genuine inefficiencies -- verified by reading each flagged
function in full, not just the flagged line):

1. PERF003 src/frob/vet/_obfuscation.py:77 (`_iter_string_literals`):
   FALSE POSITIVE. The outer `while i < n` and inner `while j < n` are one
   two-pointer linear scan, not an O(n*m) join: `j` always starts where
   `i` last stopped, and `i` is advanced past `j`'s stopping point on the
   next outer iteration (`i = (end + 1) if ... else max(end, i + 1)`), so
   every character in `text` is visited by exactly one of the two loops
   across the entire call. Total work is O(len(text)), matching the
   function's own docstring, which already proves this at length (the
   T-0208 note). Waived with a reason naming the two-pointer shape, not a
   blanket waiver.

2. PERF004 src/frob/tickets/_land.py:75 (`splice_ledger`, sorted() at line
   118): FALSE POSITIVE. `sorted(resurrected)` is called once, inside an
   `if resurrected:` block that runs AFTER the `for ticket_id in
   resurrected:` loop above it has already finished -- it is not inside
   any loop at all, just lexically following one in the same function
   (the heuristic's documented "sorted() anywhere in a function containing
   a loop" false-positive class). Waived naming that exact placement.

3. PERF004 src/frob/strata/_host_isolation.py:242
   (`_lateral_pair_violations`, sorted() at lines 258/278): FALSE
   POSITIVE. The caller (`_host_isolation` gate body) loops over user
   PAIRS and calls this function once per pair; each call's `owns_a`/
   `owns_b`/`ports_a`/`ports_b` are pair-specific data (derived from
   `nodes_a`/`nodes_b`, which differ per pair), so each `sorted()` call
   computes fresh, necessary output for that pair -- there is no constant
   input being redundantly re-sorted, nothing to hoist. Waived naming the
   per-pair data dependency.

4. PERF004 src/frob/deploy/_generate.py:104 (`sorted_manifest_entries`):
   FALSE POSITIVE, the exact documented T-0161 class: `sorted(model.nodes,
   key=...)` at line 111/112 is the `for` loop's OWN iterable (`for node
   in sorted(...)`), evaluated once per call, not per iteration. The
   `sorted()` calls inside the loop body (capabilities/syscalls) sort each
   node's own per-node data, which differs per node and cannot be hoisted
   either. Waived naming the loop-iterable shape.

Evidence: `uv run frob test --base main` -> `run_selected: python exit=0
duration=5.50s`; `[PASS] python exit=0 5.50s` (touched=8 files, all
selected tests pass). `uv run ruff check` (both `uv run ruff` and PATH
`ruff`) clean on all four changed files. `uv run frob check --only perf`
shows the four target findings all present in the `[waived: ...]` list
with 0 unwaived PERF violations. `uv run frob check` (full): `gates 0
errors, 1 warning, 31 waived` (the 1 warning is the pre-existing
`load_coverage: no coverage.xml at coverage.xml` note, unrelated to this
ticket's scope), overall `frob check . [WARN] 0 errors 360 warnings`, exit
code 0 -- the 360 warnings are pre-existing repo-wide frob-arch/malformed-
directive notices, none newly introduced by this change.

Not Filed: none -- no out-of-scope issues found; all four findings resolved
by waiver within the ticket's declared scope.

Gates: `uv run frob check --only perf` clean (0 unwaived PERF violations,
4/4 target findings waived with specific per-finding reasons). `uv run
frob check --ticket T-draft-349ca4cb (never refiled)` PRE001 cleared via `frob ticket
sweep T-draft-349ca4cb (never refiled)` after the code edits. Deletion filter (`git diff
main --diff-filter=D --stat`) is empty -- no files deleted.
