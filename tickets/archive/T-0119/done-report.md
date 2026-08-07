## Done report

Already satisfied: commit b46c1c9 (T-0046) split _heat_body (now 22
lines, delegating to _load_snapshot/_ranked_heat_entries/
_print_heat_result) and _annotate (now 26 lines, delegating to
_annotate_gutters) before this ticket was dispatched. Verified on main:
zero long-function diagnostics on src/frob/app/perf_runner.py, perf
suites green. No code change needed.
