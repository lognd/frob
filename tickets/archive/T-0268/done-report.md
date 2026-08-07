## Done report

Fixed in frob-core/src/lib.rs::candidate_pairs: skip any members[a] ==
members[b] pairing before it is inserted into shared_counts, so a region
that indexes itself twice into one bucket (its own fingerprint set carries
a duplicate value) can never surface a self-pair (i, i) regardless of
caller-side guards. This fixes the kernel, so every caller inherits the
guard for free -- not just the _r4_groups site T-0191 patched.

Evidence: tests/unit/test_dup_core.py::test_candidate_pairs_never_returns_a_self_pair
(Python-boundary regression: _candidate_pairs(((7,7,7),(99,)), 2) returns
() with no self-pair; the fix protects the Python callers of the kernel).
Also covered by the Rust unit test candidate_pairs_never_emits_a_self_pair
in the same file. Native rebuilt (make core); frob_core.candidate_pairs(
[[7,7,7],[99]], 2) -> [] confirmed from Python.

Landing note: taken surgically. The implementer worktree's tickets.md was
stale (branched pre-T-0415) and would have reverted T-0415/T-0345 and
dropped T-0438/T-0439/T-0440; only frob-core/src/lib.rs was lifted from the
worktree and this close was re-spliced onto current main. Reviewer approved
the lib.rs fix + test; the REJECT was solely the stale-ledger damage, which
this surgical land avoids.
