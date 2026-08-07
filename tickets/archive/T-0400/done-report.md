## Done report

Closed the top HIGH findings from docs/audits/vet.md within src/frob/vet/
scope:

1. Source-unavailable fail-open (finding #1): `_scan_located_source` now
   emits a `VET-SOURCE-UNAVAILABLE` ERROR `Violation`
   (`_source_unavailable_violation`) instead of silently returning an
   empty capability set -- a dependency `frob vet` never read can no
   longer be indistinguishable from one read and found clean.
2. First-lockfile-only scanning (finding #2): added
   `_lockfile._find_all_lockfiles`; `scan_tree` now iterates and merges
   results from EVERY supported lockfile under root (`_resolve_lockfiles_and_deps`),
   not just the first fixed-order hit. `_find_lockfile` kept for
   backward compatibility (delegates to the new function's first result).
3. CVE-fingerprint whitespace evasion (finding #3, partial): added a
   whitespace-tolerant regex matcher (`_needle_to_ws_pattern`/
   `_needle_hits_outside_comments_ws`) so `shell = True` /
   `yaml.load (x)`-style reformatting can no longer evade a needle.
   NOT done in this pass: extending the python import/alias/scope
   resolver to fingerprint scanning (a substantially larger change) --
   left as an honest gap, not attempted.
4. C/C++ registry gaps (finding #4): added real fs-write
   (fopen/fwrite/write/rename/unlink/mkdir), raw-fd fs-read
   (open/read/mmap), Windows exec (CreateProcess/ShellExecute/WinExec),
   and net (send/recv/sendto/recvfrom/getaddrinfo) `_DangerousOperation`
   entries -- the strcpy-family entry was a memory-safety bucket, not an
   actual file-write capability, so real fs-write was entirely absent
   before this.
5. Obfuscation language blind spot (finding #5, partial): extended
   `_SCANNABLE_SUFFIXES` to include .c/.h/.cpp/.hpp/.cc/.kt, so the
   deterministic bidi/zero-width Trojan-Source scan (the one sound
   detector in this module per the audit) now runs on C/C++/Kotlin
   dependency files. NOT done: triple-quoted/template-literal and
   split-string entropy blindness -- `_iter_string_literals` still only
   scans single-char `'`/`"` delimiters; closing that needs a real
   string-literal-shape rewrite, documented as an honest gap with a
   negative test (`test_split_string_payload_still_not_detected`).

MED/LOW findings in the audit doc (typosquat distance, VET-C build.rs
path, allow=true blanket, max_files truncation, pnpm v9 shape, etc.) were
NOT addressed -- out of scope for this pass per the ticket's own text
("Then re-audit until empty. MED/LOW in the doc").

Also found and filed (out of scope, not fixed here): the CLI's
`frob ticket evidence <id>` rejects a dot-form `Class.method` evidence id
with a misleading EvidenceNotPassing even when the test passes --
`_apply_evidence` passes raw un-normalized ids into `_verify_ids_passing`,
which only matches pytest's native `::` form. Not Filed as T-draft-2d6b3e5d (never refiled)
(scope src/frob/app/ticket_runner.py). Worked around here by recording
this ticket's own evidence in `::` form.

### Changed
(no changed files detected)

### Evidence
- `tests/test_vet.py::TestCapabilityScan::test_c_source_fs_write_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_c_source_raw_fd_read_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_c_source_windows_exec_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_c_source_net_recv_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_whitespace_reformatted_needle_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_whitespace_tolerant_match_still_respects_comment_spans` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeSourceUnavailableFailClosed::test_missing_source_surfaces_error_violation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeSourceUnavailableFailClosed::test_enforced_missing_source_fails_the_gate` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeMultipleLockfiles::test_scan_tree_scans_every_lockfile` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_polyglot_repo` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_single` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_none` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestLockfileParsers::test_find_all_lockfiles_direct_path` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_c_file` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_detected_in_kotlin_file` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestObfuscationEnsemble::test_split_string_payload_still_not_detected` (pytest node id, verified passing when recorded)
