---
id: T-2352
title: 'sweep auto-filer must relativize absolute finding paths into scope: (T-2342
  producer-side half, deferred behind T-2313''s lease)'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_under_root_is_relativized
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_already_relative_is_unchanged
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_filed_ticket_scope_is_relative_end_to_end
designated_repro_test: tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_filed_ticket_scope_is_relative_end_to_end
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9b7da2f6184aafd77c120768ce9279bb67ff66e8
---
Producer-side half of T-2342, deferred because src/frob/app/ticket_runner/
_rapid_sweep.py carried a live cross-worktree lease held by T-2313 (fixing
the SAME auto-filer's blank/degenerate-identity defect, same file) for
the entire duration T-2342 was worked. Rather than force a collision on
the same file two tickets are independently repairing, T-2342 landed only
the reader-side half (the defensive fix in _new.py that stops one
corrupted ledger row from crashing `frob ticket new` fleet-wide) and this
ticket carries the remaining producer-side half forward.

Root cause, confirmed by reading the code
(src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket):

    spec = TicketSpec(
        ...
        scope=tuple(sorted({file for _, file in unfiled_pairs})),
        ...
    )

`unfiled_pairs` are `(rule_id, file)` tuples sourced from `new_findings`,
which is threaded through from whatever gate/diagnostic collection
produced the sweep's finding set -- `file` is used AS-IS with no
relativization against `root`. When the upstream diagnostic reports an
absolute path (confirmed happening for at least 3 tickets historically:
T-1753, T-1756, T-2308), that absolute path is written directly into the
new ticket's `scope:` with no normalization.

Fix (same posture as T-2314's `_relativize_perf_violation_file` fix for
the analogous `perf_gate` absolute-path defect -- normalize at the
FILER's OWN RETURN BOUNDARY, leave internal disk-I/O paths elsewhere in
the module untouched, do not teach every consumer of `scope:` to accept
both shapes): add a `_relativize_regression_scope_file(root, file) ->
str` helper (or equivalent) that resolves `file` against `root` and
returns the repo-relative POSIX path whenever `file` is absolute AND
under `root`; used at the `scope=tuple(sorted({...}))` construction
above, not deeper in the pipeline. If `file` is absolute but NOT under
`root` (should not happen, but a defensive fallback matters after this
exact defect class caused a fleet-wide outage once already), keep it
as-is and log a WARNING naming the ticket being filed and the anomalous
path, rather than silently coercing it into something wrong.

Must-still-pass positive controls (per the parent ticket's own
acceptance criteria, still binding here):
1. A ticket filed by the sweep gets relative scope paths (the fix's own
   direct effect -- assert on a filed ticket's `scope:` after feeding
   `_file_regression_ticket` an absolute-path finding).
2. A genuinely malformed scope (e.g. a Windows-style path, or an absolute
   path outside `root`) is still visible/loud, not silently coerced into
   a plausible-but-wrong relative path.
3. `frob ticket new` for an unrelated ticket still succeeds when a sweep-
   filed ticket exists with scope entries from BEFORE this fix (the
   reader-side guard T-2342 already landed covers this independently, but
   a regression test here should exercise the producer's own new-ticket
   path end-to-end, not just the reader).

Sequencing: touches the same file as T-2313 (both `_rapid_sweep.py`).
Land T-2313 first if it is still in progress when this is picked up, then
narrow/rebase this ticket's own scope onto the post-T-2313 state before
starting, to avoid the same collision that deferred this half of T-2342
in the first place.