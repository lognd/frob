## Done report

Changed: docs/audits/check-performance.md (new, ranked hot-path audit)
Changed: docs/index.md (link the new audit doc)
Changed: docs/audits/README.md (verdict-table row for the new audit)

Evidence: cmd:bash <scratchpad>/verify_audit.sh (structural check of the
required sections/table in check-performance.md), bound to both acceptance
criteria via --accepts 0/1.

Filed: T-0948 (frob.perf collectors blind to thread/process-pool
gate dispatch), T-0946 (shared walk investigation for
sys/secrets/pii_structural), T-0947 (process-pool cold-start
overhead isolation), T-0949 (finish isolated test_gate profile,
root-cause the isolated-vs-in-context discrepancy from Finding 5).

Gates: frob check --ticket T-0928 (gates-fast/static/gates-native/
gates-security, chunked) all clean, 0 errors. One pre-existing FAIL in the
`lint` group (ruff-format on src/frob/arch/_lock_ordering.py and
tests/unit/test_arch.py) predates this ticket's changes and is outside its
scope -- not touched, not waived under this ticket.

Key finding: frob's own profiling stack (cProfile-based `frob perf
profile`, `StackSampler`, `frob perf heat`) cannot see inside `frob
check`'s own thread-pool/process-pool gate dispatch -- `heat` itself
reports "237 symbol(s) attributed, 30.349s unattributed" against a ~60s
artifact. The ranked table is therefore anchored on `gate-summary`'s own
wall-clock brackets (real per-gate elapsed time, unaffected by this blind
spot) rather than on cProfile/heat symbol attribution. Full detail, ranked
table (8 rows clear the 80% bar), top-10 remedies, and PERF00x/.strata
dispositions are in docs/audits/check-performance.md.
