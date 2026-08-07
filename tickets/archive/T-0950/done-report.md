## Done report

Bar stated before measuring: T-0930 measured PyO3's fixed per-call
marshaling tax at ~0.8ms even for a single batched call over a sizeable
payload (whole `by_name` index). A rust-candidate must therefore cost at
least low-hundreds-of-ms of real Python compute at real-repo scale (2+
orders of magnitude above that ~1ms floor) to plausibly clear it.

Sizing (same isolation technique T-0930 used for dead_symbols --
time.thread_time() bracketing only find_cycles, graph pre-built, median
of 8 runs with 1 warmup dropped):

- This repo's real import graph (frob.check._python._build_import_graph,
  1101 files): 693 nodes, 26 edges.
- find_cycles isolated thread_time at that real scale: 0.0004s (0.4ms).
- Synthetic stress at 1000 nodes/3000 edges (~1.4x node count, ~115x
  edge count vs this repo): 0.0011s (1.1ms) -- and a second run at this
  scale hit RecursionError (native Python recursion depth), so the
  current implementation caps out before reaching a scale where the
  loop cost would matter.

0.4ms is ~2000x below the stated bar and roughly HALF of T-0930's own
measured fixed FFI tax for one batched call -- a native port would lose
the marshaling round-trip alone before the Rust loop runs, a strictly
worse case than T-0930's own dead_symbols finding.

Verdict: DISPOSE, do not port. `frob.cycle.graph.find_cycles` stays
pure Python, unchanged. No frob_core kernel added; no parity tests
needed since nothing shipped a second implementation.

Changed:
- docs/audits/check-performance.md (new "T-0950 remediation log"
  section: bar, methodology, measured numbers, disposition, filed
  out-of-scope discovery)

Evidence: tests/unit/test_cycle.py's 7 existing tests (all passing,
bound as ticket evidence) -- confirms find_cycles' behavior is
unaffected since no code changed; `uv run pytest -q tests/unit/
test_cycle.py` (7 passed).

Filed: T-0952 ("cycle: Tarjan find_cycles recurses natively,
RecursionError on long chains", bug, scope src/frob/cycle/**) -- the
RecursionError surfaced while sizing the synthetic stress graph above
is a real, reproducible correctness gap, out of scope for this ticket
(which is about the port-or-dispose decision, not correctness).

Gates: `uv run frob check --ticket T-0950` run chunked per-stage
(gates-fast, static, gates-security, lint) per agent-playbook section
3b. gates-fast, static, gates-security all pass clean (baseline
warnings/waivers only, no new violations). `lint` shows 2 pre-existing
ty errors and 3 pre-existing ruff-format findings, all in files this
ticket never touched (tests/test_gates.py, src/frob/arch/
_lock_ordering.py, tests/unit/test_arch.py) -- unrelated baseline noise,
not introduced here. `frob ticket done-report T-0950` itself hung
(T-0887-class done-report hang per this dispatch's process rules);
this section was hand-written directly into tickets.md instead, per
that same instruction.
