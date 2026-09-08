## Done report

Confirmed the three ARCH103 findings on src/frob/graph/cache.py's
lock-holder diagnostic helpers by reading _srp.py's mixed-concern
detector: each of _lock_holder_pids_linux, _lock_holder_pids_darwin,
and _holder_cmdline combined an I/O-capability call, a string-
formatting call (str()/join()/decode()), and >=2 of its own branches
in one body.

Split each into three concerns per the ticket's instruction:
- A reading half doing only I/O (no format calls): _resolve_lock_
  target + _scan_proc_fd_pids for Linux, _run_lsof for darwin,
  _read_proc_cmdline_bytes for cmdline.
- A deciding half doing pure filtering/parsing with no I/O:
  _exclude_pid (shared by both platforms -- both readers duplicated
  the exact same "drop my own pid" filter, now one function),
  _parse_lsof_pids for darwin.
- A formatting half for _holder_cmdline: _parse_cmdline_bytes (also
  does the deciding -- "is this an empty cmdline" -- since that
  decision and the join/decode formatting are the same few lines and
  splitting them further would not add a testable seam).
- Each original public function (_lock_holder_pids_linux/_darwin,
  _holder_cmdline) is now pure composition with no I/O/format/branch
  of its own, so it is a single concern (orchestration) rather than
  the flagged mixed-concern shape.

Checked whether the two platform-specific readers share more than
_exclude_pid: they do not -- Linux walks /proc/*/fd, darwin shells to
lsof; the raw-acquisition mechanisms are platform-native and have no
shared substrate beyond the self-pid filter now extracted.

Did NOT waive. Verified the rule's own reasoning is correct for this
code (these ARE diagnostic helpers that need to be testable without a
real stuck lock) and fixed the actual concern-mixing.

Added tests/unit/test_graph_lock_holder_naming.py::
TestLockHolderDecisionAndFormattingHalves (11 new cases) exercising
_exclude_pid, _parse_lsof_pids, _parse_cmdline_bytes, and the two
darwin/cmdline composing functions against fabricated process state
(no real lock or subprocess involved) -- the coverage gap the ticket
flagged as worth closing now that the logic is separable. All 5
pre-existing tests in that file (which call the public functions
directly and mock the internals) still pass unchanged.

Verified: `frob.gates._arch.arch_gate` no longer reports ARCH103 for
src/frob/graph/cache.py (confirmed by direct call, filtering for
cache.py). The pre-existing LARGE001 (file-size) finding on the same
file is untouched and unrelated to this ticket.

### Changed
```
 src/frob/graph/cache.py                     | 173 +++++++++++++++++++++-------
 tests/unit/test_graph_lock_holder_naming.py |  89 ++++++++++++++
 tickets/T-4317/done-report.md               |  64 ++++++++++
 tickets/T-4317/ticket.md                    |  16 ++-
 4 files changed, 299 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderDecisionAndFormattingHalves::test_exclude_pid_drops_only_the_named_pid` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderDecisionAndFormattingHalves::test_parse_lsof_pids_reads_p_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderDecisionAndFormattingHalves::test_parse_cmdline_bytes_joins_nul_separated_parts` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderDecisionAndFormattingHalves::test_lock_holder_pids_darwin_composes_reading_deciding_excluding` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_lock_holder_naming.py::TestLockHolderDecisionAndFormattingHalves::test_holder_cmdline_composes_reading_and_parsing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4673 warning(s), 952 waived
- error-findings: SCOPE002@tickets.md
